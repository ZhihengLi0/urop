"""R7 LED monitoring runs: per-event table, LED timing and per-source templates for one series.

The LED monitoring sequence (SR1a_post-activation_LEDStability_0V_23Det_*.msl) waits 800 s
for the begin-of-run randoms, then flashes one set of LEDs for 150 s (phase 1), switches all
LEDs off for 3 s, flashes a second set for 150 s (phase 2) and stops. Every LED flashes at
1 Hz, so its triggers sit at one fixed position of TriggerTime modulo 1 s.

Pass 1 reads every triggered event and stores one row per (event, phonon channel) with the
pulse features of the CUTE R37 / R7 v3 pipeline (baseline, polarity, rise edge, SNR, glitch,
bipolar), measured on the despiked trace (see features). From the event times it finds the boundary between the two phases and, for every
(detector, phase), the 1 Hz LED peaks in TriggerTime mod 1 s.

Peaks of different detectors at (nearly) the same position form one flash group. Every event is
then given a source: the flash group whose peak of its own detector contains it (each detector's
peak has its own centre and width), else a group in whose window it falls, else background.
Pass 2 averages the good pulses per (detector, phase, channel, source).

Usage: python3 extract_led_events.py SERIES [OUTDIR]
"""
import glob, json, os, pickle, sys, time
from collections import defaultdict
import numpy as np
from scipy.ndimage import median_filter
from rawio.IO import RawDataReader

SR, NS, ALIGN, NBASE = 625000.0, 32768, 8000, 5000
SNR_MIN, GLITCH_SIGMA = 8.0, 10.0
MEDFILT = 11              # samples (17.6 us): running median against the LED-drive pickup spikes (1-5 samples wide)
RAW = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R7/Raw"
HERE = os.path.dirname(os.path.abspath(__file__))
WIN_S = 1e-3              # search window around a 1 Hz peak (the final window is per peak, see half_width)
FOLD_BIN_S = 0.5e-3       # bin width of the TriggerTime mod 1 s histogram
# Two detectors that trigger on the same LED flash do so within 0.2 ms of each other (measured over the 45 series
# with the LED's own detector as reference: -115 ... +179 us), so peaks whose centres are closer than LINK_S are one
# flash group. For the Z20 LEDs, whose flash time itself jitters by +-0.7 ms (Z20 and its neighbours all show the
# same wide peak), the centres are less precise: 0.3 x the peak half-width (~0.28 ms). LEDs are switched on one
# after the other, so several LEDs of a phase often flash within a few ms: unrelated flashes do come this close.
LINK_S = 2e-4
# The nominal times of the script (800 / 950 / 953 / 1103 s) are NOT used: in
# 24260915_063921 the LEDs came on at ~888 s and the run ended at ~1192 s (the ODB commands of
# the sequencer take time). Both phases are found from the data.
TAGS = ["good", "glitch", "nopulse", "baseline", "norise", "edge", "bipolar"]
# LED selected per detector in each phase (LED_MONITORING of the .msl scripts; identical in
# the 20260913, 20260918 and 20261004 versions). Detectors not listed have no LED on.
SCRIPT_LEDS = {
    "phase1": {"Z1": 0, "Z2": 3, "Z4": 4, "Z6": 3, "Z7": 0, "Z8": 3, "Z11": 0, "Z13": 1, "Z15": 1,
               "Z17": 0, "Z18": 3, "Z19": 0, "Z20": 3, "Z23": 0, "Z24": 3},
    "phase2": {"Z1": 4, "Z3": 3, "Z5": 3, "Z8": 1, "Z9": 4, "Z11": 3, "Z13": 5, "Z15": 4, "Z18": 1,
               "Z20": 0, "Z22": 0, "Z23": 3},
}


def features(y_raw):
    """Pulse features of one trace: the cuts of make_led_templates_v3.process (R37 algorithm ported to R7), applied
    to the DESPIKED trace (MEDFILT-sample running median). When an LED is driven, the readout of its own detector
    picks up a spike a few samples wide; on the raw trace that spike was taken as the pulse peak (amplitude = spike
    height, 'bipolar' / 'glitch' tags) and the 10-90 % rise of noisy pulses stuck at the 3.2 ms search window.
    A phonon pulse (rise >= 10 us) passes the filter unchanged (peak 0.998, same 10-90 % rise).
    Peak and noise are both taken from the despiked trace (SNR = despiked peak / despiked noise; with the raw
    noise the cut would be much stricter than on the raw trace, whose maximum includes a positive noise
    excursion); noise_raw is the raw noise of the same quiet region. Baseline drift is tested on the raw trace.
    Returns (tag, feature dict, rolled normalised despiked trace or None)."""
    y = y_raw.astype(np.float64)
    yd = median_filter(y, size=MEDFILT, mode="nearest")
    f = dict(base=float(yd[:NBASE].mean()), amp=np.nan, noise=np.nan, rise=-1, t1090=np.nan, tdecay=np.nan, spike=np.nan, pol=1,
             noise_raw=np.nan)
    h1, h2 = y[:NBASE // 2], y[NBASE // 2:NBASE]
    if f["base"] < 1000 or f["base"] > 64500 or abs(h1.mean() - h2.mean()) > 3 * h1.std() + 1:
        return "baseline", f, None
    y = y - f["base"]; yd = yd - f["base"]
    f["spike"] = float(np.max(np.abs(y - yd)))      # largest excursion removed by the filter, ADC
    pk = int(np.argmax(np.abs(yd)))
    if yd[pk] < 0:
        y = -y; yd = -yd; f["pol"] = -1
    peak = yd[pk]
    f["amp"] = float(peak)
    if peak <= 0:
        return "nopulse", f, None
    yn = yd / peak
    seg = yn[max(pk - 2000, 0):pk + 1]
    below = np.where(seg < 0.2)[0]
    if len(below) == 0 or below[-1] == len(seg) - 1:
        return "norise", f, None
    rise = max(pk - 2000, 0) + int(below[-1]) + 1
    if pk - rise > 1900:
        return "norise", f, None
    f["rise"] = rise
    glitch_safe, post_pulse = int(rise - 0.9e-3 * SR), int(rise + 10e-3 * SR)
    if rise > NBASE + 100:
        q = slice(0, max(NBASE, min(glitch_safe, NS)))
    else:
        q = slice(post_pulse, NS) if post_pulse < NS - 100 else slice(NS - NBASE, NS)
    if len(yd[q]) < 100:
        return "nopulse", f, None
    noise = yd[q].std()                              # noise of the trace the cuts work on
    f["noise"] = float(noise); f["noise_raw"] = float(y[q].std())
    if noise <= 0 or peak / noise < SNR_MIN:
        return "nopulse", f, None
    # shape numbers on the normalised despiked trace, walking back from the peak: last sample below 90 % and
    # last sample below 10 % (10-90 % rise); peak -> first sample below 1/e (decay)
    b90, b10 = np.where(seg < 0.9)[0], np.where(seg < 0.1)[0]
    if len(b90) and len(b10):
        f["t1090"] = float(b90[-1] - b10[-1]) / SR
    after = np.where(yn[pk:] <= np.exp(-1))[0]
    if len(after):
        f["tdecay"] = float(after[0]) / SR
    lo, hi = max(rise - 250, 0), max(rise - 31, 1)
    if yn[lo:hi].min() < -GLITCH_SIGMA * noise / peak:
        return "glitch", f, None
    if -yd[pk:pk + 1500].min() > 0.5 * peak:
        return "bipolar", f, None
    if not (ALIGN < rise < NS - 8000):
        return "edge", f, None
    return "good", f, np.roll(yn, ALIGN - rise)


def scalar(v):
    return v[0] if isinstance(v, (list, tuple, np.ndarray)) else v


def triggered_files(series):
    out = []
    for f in sorted(glob.glob("%s/%s/*.mid.lz4" % (RAW, series))):
        n = RawDataReader(filepath=f, verbose=False).get_nb_events()
        if n.get("NbEventsBORR", 0) >= n.get("NbEventsNotEmpty", 1):
            print("  skip %s (begin-of-run randoms only)" % os.path.basename(f), flush=True)
        else:
            out.append(f)
    return out


def events_of(f, stats=None):
    """Triggered events (trigger type 1) with ReadoutType 8 and exactly one detector read out.
    stats (a dict) counts what is read and what is skipped."""
    evs = RawDataReader(filepath=f, verbose=False).read_events(trigger_types=[1], output_format=2)
    evs = evs[0] if isinstance(evs, tuple) else evs
    for e in evs:
        if stats is not None:
            stats["type1"] = stats.get("type1", 0) + 1
        if e["event"].get("ReadoutType") != 8:
            if stats is not None:
                stats["skip_readout_not_8"] = stats.get("skip_readout_not_8", 0) + 1
            continue
        dets = [k for k in e if str(k).startswith("Z")]
        if len(dets) != 1:
            if stats is not None:
                stats["skip_%d_detectors" % len(dets)] = stats.get("skip_%d_detectors" % len(dets), 0) + 1
            continue
        yield e, dets[0]


def run_info(series):
    """Begin-of-run settings worth keeping: start comment, LED and L1 trigger settings."""
    info = {}
    f = sorted(glob.glob("%s/%s/*.mid.lz4" % (RAW, series)))[0]
    r = RawDataReader(filepath=f, verbose=False)
    for key, path in [("edit_on_start", "/Experiment/Edit on start"), ("runinfo", "/Runinfo")]:
        try:
            info[key] = r.get_full_odb(odb_dir=path)
        except Exception as ex:
            info[key] = "unavailable: %r" % (ex,)
    led = {}
    for d in range(1, 25):
        try:
            led["Z%d" % d] = r.get_full_odb(odb_dir="/Detectors/Det%02d/Settings/LED" % d)
        except Exception:
            pass
    info["led_settings"] = led
    return info


def fold(t):
    return np.mod(t, 1.0)


def circ(x):
    """Difference of two positions in the second, wrapped to [-0.5, 0.5)."""
    return np.mod(np.asarray(x) + 0.5, 1.0) - 0.5


def led_peaks(times, min_count=20):
    """Positions (s, in [0,1)) of the 1 Hz peaks in TriggerTime mod 1 s."""
    if len(times) < min_count:
        return []
    nb = int(round(1.0 / FOLD_BIN_S))
    h, _ = np.histogram(fold(times), bins=nb, range=(0, 1))
    # merge a peak split across two bins: smooth with a 3-bin circular sum
    hs = h + np.roll(h, 1) + np.roll(h, -1)
    bg = max(np.median(hs), 1.0)
    peaks = []
    for _ in range(4):                       # at most a few LEDs per detector and phase
        i = int(np.argmax(hs))
        if hs[i] < max(min_count, 10 * bg):
            break
        c = (i + 0.5) * FOLD_BIN_S
        off = circ(fold(times) - c)                  # circular: a peak may straddle 0 / 1
        peaks.append(float(np.mod(c + np.median(off[np.abs(off) < WIN_S]), 1.0)))
        for k in range(-int(WIN_S / FOLD_BIN_S) - 1, int(WIN_S / FOLD_BIN_S) + 2):
            hs[(i + k) % nb] = 0
    return peaks


def link_tol(w1, w2):
    """Largest distance between the peak centres of two detectors that trigger on the same flash."""
    return max(LINK_S, 0.3 * max(w1, w2))


def near(t, phase):
    return np.abs(circ(fold(t) - phase)) < WIN_S


def half_width(times, p):
    """Half-width of a 1 Hz peak: 1.3 x the 95th percentile offset of the triggers within 1 ms,
    at least 0.1 ms (most LEDs: +-13 us = one tick of TriggerTime; Z20: +-0.7 ms)."""
    x = np.abs(circ(fold(times) - p))
    x = x[x < 1e-3]
    return float(max(1e-4, 1.3 * np.percentile(x, 95))) if len(x) else 1e-4


def led_timing(series, t, det):
    """Phases and flash groups from the trigger times alone (re-runnable from events.npz).

    A flash group = one 1 Hz peak position in TriggerTime mod 1 s within a phase, with every
    detector that triggers on it. Its name is the detector(s) whose LED the script switches on
    in that phase and that trigger on it ('Z2' -> Z2's own LED, seen also by the others listed),
    or 'unknown@0.9680' when none of the triggering detectors has an LED on."""
    det = np.asarray(det)
    # 1) the LED period and the 3 s pause, from every detector's 1 Hz peaks (1 ms windows)
    cand = np.zeros(len(t), bool)
    for d in np.unique(det):
        m = det == d
        for p in led_peaks(t[m]):
            cand |= m & near(t, p)
    tc = np.sort(t[cand])
    mid = np.array([], int)
    if len(tc) >= 10:
        lo, hi = tc[0] + 0.25 * (tc[-1] - tc[0]), tc[0] + 0.75 * (tc[-1] - tc[0])
        mid = np.where((tc[:-1] > lo) & (tc[1:] < hi))[0]
    if not len(mid):                                 # no LED flashes found (24260918_084531)
        timing = dict(series=series, split_s=None, pause_s=None, led_on_s=None, led_off_s=None, groups=[],
                      peaks_all={}, missing_leds={ph: sorted(SCRIPT_LEDS[ph], key=lambda z: int(z[1:])) for ph in SCRIPT_LEDS},
                      counts={}, note="no 1 Hz LED peaks found in TriggerTime")
        return timing, np.array(["none"] * len(t)), np.array(["bg"] * len(t))
    g = tc[mid + 1] - tc[mid]; j = mid[int(np.argmax(g))]
    split, pause = float((tc[j] + tc[j + 1]) / 2), float(tc[j + 1] - tc[j])
    phase_of = np.where(t < split, "phase1", "phase2").astype(object)

    # 2) flash groups per phase: every detector's 1 Hz peaks (own centre and width), linked when the centres
    #    are within link_tol of each other
    groups, peaks_all = [], {}
    for ph in ("phase1", "phase2"):
        found = []                                   # (position, half-width, det)
        for d in np.unique(det):
            m = (phase_of == ph) & (det == d)
            for p in led_peaks(t[m]):
                found.append((p, half_width(t[m], p), "Z%d" % d))
                peaks_all.setdefault("Z%d|%s" % (d, ph), []).append(round(p, 6))
        found.sort()
        G = []
        for p, w, zd in found:                       # single linkage on the peak centres
            if G and abs(circ(p - G[-1]["peaks"][-1][1])) < link_tol(w, G[-1]["peaks"][-1][2]):
                gr = G[-1]
            else:
                gr = dict(phase=ph, dets=[], peaks=[])
                G.append(gr)
            if zd not in gr["dets"]:
                gr["dets"].append(zd)
            gr["peaks"].append([zd, p, w])
        if len(G) > 1 and abs(circ(G[0]["peaks"][0][1] - G[-1]["peaks"][-1][1])) < link_tol(G[0]["peaks"][0][2], G[-1]["peaks"][-1][2]):
            last = G.pop()                           # same flash on both sides of the 0 / 1 wrap
            G[0]["peaks"] = last["peaks"] + G[0]["peaks"]
            G[0]["dets"] = last["dets"] + [z for z in G[0]["dets"] if z not in last["dets"]]
        for gr in G:                                 # group position = median peak centre; width = widest peak
            p0 = gr["peaks"][0][1]
            gr["pos"] = float(np.mod(p0 + np.median([circ(q[1] - p0) for q in gr["peaks"]]), 1.0))
            gr["half_s"] = float(max(q[2] for q in gr["peaks"]))
        groups += G
    used = set()
    for gr in groups:
        owners = [z for z in gr["dets"] if z in SCRIPT_LEDS[gr["phase"]]]
        name = "+".join(owners) if owners else "unknown@%.4f" % gr["pos"]
        if (gr["phase"], name) in used:              # e.g. a Z1 re-trigger peak 13 ms after the Z1 flash
            name = "%s@%.4f" % (name, gr["pos"])
        used.add((gr["phase"], name))
        gr["name"] = name
        gr["leds"] = {z: SCRIPT_LEDS[gr["phase"]][z] for z in owners}

    # 3) source of every event. Each peak keeps its own centre and width (Z20's peak is +-0.9 ms wide and
    #    its centre differs from a neighbour's narrow peak in the same group). An event goes to the nearest
    #    peak OF ITS OWN DETECTOR that contains it; if there is none, to the nearest peak of any detector
    #    that contains it (a detector too rare on that flash to have a peak); else it is background.
    source = np.array(["bg"] * len(t), dtype=object)
    for ph in ("phase1", "phase2"):
        P = [(gr["name"], int(z[1:]), p, w) for gr in groups if gr["phase"] == ph for z, p, w in gr["peaks"]]
        m = np.where(phase_of == ph)[0]
        if not P or not len(m):
            continue
        pname = np.array([q[0] for q in P], dtype=object); pdet = np.array([q[1] for q in P])
        ppos = np.array([q[2] for q in P]); pwid = np.array([q[3] for q in P])
        dist = np.abs(circ(fold(t[m])[None, :] - ppos[:, None]))             # peaks x events
        inside = dist < pwid[:, None]
        d_own = np.where(inside & (pdet[:, None] == det[m][None, :]), dist, np.inf)
        d_any = np.where(inside, dist, np.inf)
        dd = np.where(np.isfinite(d_own).any(axis=0)[None, :], d_own, d_any)
        best = np.argmin(dd, axis=0)
        ok = np.isfinite(dd[best, np.arange(len(m))])
        source[m[ok]] = pname[best[ok]]

    # LED period = sustained 1 Hz flashing: per group, the first trigger followed by two more within 3.5 s
    # and the last one preceded by two within 3.5 s; a single background trigger on a group's position
    # (24260915_063921: one Z1 trigger at 813 s, LEDs on at 889 s) cannot start or end it.
    starts, ends = [], []
    for gr in groups:
        tt = np.sort(t[(phase_of == gr["phase"]) & (source == gr["name"])])
        k = np.where(tt[2:] - tt[:-2] <= 3.5)[0] if len(tt) >= 3 else []
        if len(k):
            starts.append(tt[k[0]]); ends.append(tt[k[-1] + 2])
    on0, on1 = float(min(starts)) - 0.5, float(max(ends)) + 0.5
    in_phase = phase_of.copy()
    phase_of[t < on0] = "before"; phase_of[t > on1] = "after"
    source[(t < on0) | (t > on1)] = "outside"
    keep = []
    for gr in groups:
        m = (source == gr["name"]) & (in_phase == gr["phase"])
        if not m.any():                              # no trigger of this group inside the LED period
            continue
        gr["n_triggers"] = {z: int((m & (det == int(z[1:]))).sum()) for z in gr["dets"]}
        gr["t_first"], gr["t_last"] = float(t[m].min()), float(t[m].max())
        gr["n_span"] = int(round(gr["t_last"] - gr["t_first"])) + 1        # 1 Hz: its own first to last trigger
        keep.append(gr)
    groups = keep
    # flashes per phase: all LEDs of a phase start and stop within the same second (checked on the 45 series:
    # groups that start 1-3 s later have that many triggers less), so every LED of the phase flashes as often
    # as the longest group spans
    n_fl = {ph: max([gr["n_span"] for gr in groups if gr["phase"] == ph] or [0]) for ph in ("phase1", "phase2")}
    for gr in groups:
        gr["n_flashes"] = n_fl[gr["phase"]]
    own = {(z, gr["phase"]) for gr in groups for z in gr["leds"]}
    timing = dict(series=series, split_s=split, pause_s=pause, led_on_s=on0, led_off_s=on1, n_flashes=n_fl,
                  groups=groups, peaks_all=peaks_all,
                  missing_leds={ph: sorted(set(SCRIPT_LEDS[ph]) - {z for (z, p) in own if p == ph}, key=lambda z: int(z[1:]))
                                for ph in SCRIPT_LEDS},
                  counts={"%s|%s" % (p, s): int(((phase_of == p) & (source == s)).sum())
                          for p in np.unique(phase_of) for s in np.unique(source)})
    return timing, phase_of.astype(str), source.astype(str)


def main(series, outdir):
    os.makedirs(outdir, exist_ok=True)
    t0 = time.time()
    files = triggered_files(series)
    print("series %s: %d triggered file(s)" % (series, len(files)), flush=True)

    # ---------------- pass 1: event table ----------------
    ev = defaultdict(list)            # one row per event
    ch = defaultdict(list)            # one row per (event, channel)
    nread = {}
    for f in files:
        for e, det in events_of(f, nread):
            tr = e["trigger"]
            i = len(ev["time"])
            ev["time"].append(float(scalar(tr.get("TriggerTime", np.nan))))
            ev["det"].append(int(det[1:]))
            ev["trig_det"].append(int(scalar(tr.get("TriggerDetNum", -1))))
            ev["trig_amp"].append(float(scalar(tr.get("TriggerAmplitude", np.nan))))
            ev["trig_word"].append(int(scalar(tr.get("TriggerWord", -1))))
            ev["event"].append(int(e["event"].get("EventNumber", -1)))
            ev["dump"].append(int(e["event"].get("DumpNumber", -1)))
            for c, v in e[det].items():
                a = np.asarray(v)
                if not c.startswith("P") or a.size != NS:
                    continue
                tag, ft, _ = features(a)
                ch["ev"].append(i); ch["chan"].append(c); ch["tag"].append(TAGS.index(tag))
                for k in ("base", "amp", "noise", "noise_raw", "rise", "t1090", "tdecay", "spike", "pol"):
                    ch[k].append(ft[k])
        print("  pass 1 %s: %d events, %.0f s" % (os.path.basename(f), len(ev["time"]), time.time() - t0), flush=True)
    ev = {k: np.asarray(v) for k, v in ev.items()}
    ch = {k: np.asarray(v) for k, v in ch.items()}
    print("events read: %s; kept %d" % (nread, len(ev["time"])), flush=True)

    # ---------------- LED timing ----------------
    timing, phase_of, source = led_timing(series, ev["time"], ev["det"])
    ev["phase"], ev["source"] = phase_of, source
    t = ev["time"]
    if timing["groups"]:
        print("LEDs %.1f-%.1f s, phase split at %.2f s (pause %.2f s); %d flash groups, own LED missing for %s"
              % (timing["led_on_s"], timing["led_off_s"], timing["split_s"], timing["pause_s"],
                 len(timing["groups"]), timing["missing_leds"]), flush=True)
    else:
        print("NO LED FLASHES FOUND: %d events, TriggerTime %.1f-%.1f s, per detector %s"
              % (len(t), np.nanmin(t), np.nanmax(t), dict(zip(*np.unique(ev["det"], return_counts=True)))), flush=True)

    # ---------------- pass 2: templates per (det, phase, channel, source) ----------------
    acc = defaultdict(lambda: np.zeros(NS)); cnt = defaultdict(int)
    i = 0
    for f in files:
        for e, d in events_of(f):
            key0 = (d, ev["phase"][i], ev["source"][i])
            if key0[1] in ("phase1", "phase2"):
                for c, v in e[d].items():
                    a = np.asarray(v)
                    if not c.startswith("P") or a.size != NS:
                        continue
                    tag, _, rolled = features(a)
                    if rolled is not None:
                        k = key0[:2] + (c, key0[2])
                        acc[k] += rolled; cnt[k] += 1
            i += 1
        print("  pass 2 %s: %.0f s" % (os.path.basename(f), time.time() - t0), flush=True)
    assert i == len(t), "pass 2 saw %d events, pass 1 %d" % (i, len(t))
    templates = {k: (acc[k] / cnt[k]).astype(np.float32) for k in cnt if cnt[k] >= 5}

    np.savez_compressed(os.path.join(outdir, "events.npz"),
                        **{"ev_" + k: v for k, v in ev.items()}, **{"ch_" + k: v for k, v in ch.items()})
    pickle.dump(dict(series=series, align_sample=ALIGN, sample_rate=SR, templates=templates,
                     n_pulses={k: cnt[k] for k in templates}), open(os.path.join(outdir, "templates.pkl"), "wb"))
    timing["events_read"] = nread
    json.dump(timing, open(os.path.join(outdir, "timing.json"), "w"), indent=1)
    try:
        pickle.dump(run_info(series), open(os.path.join(outdir, "run_info.pkl"), "wb"))
    except Exception as ex:
        print("run info not read: %r" % (ex,), flush=True)
    print("done: %d events, %d templates, %.0f s" % (len(t), len(templates), time.time() - t0), flush=True)


if __name__ == "__main__":
    s = sys.argv[1]
    main(s, sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out", s))
