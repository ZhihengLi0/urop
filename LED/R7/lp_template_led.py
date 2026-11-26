"""Per-pulse fits of the LED pulses with the Z7 template chain, for one series.

For every non-zero cell of the visibility plots (out/summary/cells.csv: a detector triggering on an LED in a
phase) and every phonon channel, each pulse of that cell goes through the unchanged Z7 chain
(snolab_phonon_pulse_analysis/phonon_pulse_template_generation/R4/lp_fit_align/scripts/lp_fit_align.py):
  raw trace -> [LED data only: MEDFILT-sample (17.6 us) running median, removes the few-us pickup spikes of the
  LED drive; the same filter as in extract_led_events.features] -> 100 kHz 4th-order Butterworth low-pass -> baseline (median of samples 2000-12000) subtracted
  -> divided by the global peak -> 2-exp fit with free pretrigger (16050 +- 3000)
  -> fit_ok := amp > 0 and 0 < t_rise < t_fall; NRMSE recorded
  -> the measured low-passed trace is shifted so its fitted start lands on sample 16050.
Before the chain every trace is moved by SHIFT samples so that the LED pulse starts where the Z7 pulses do (see SHIFT);
a pulse whose fitted start is more than START_TOL samples from the expected one is not used for the template.
Event selection (the Z7 analogue): the cell's detector triggered and the event lies in that LED's flash group.

Stored in out/<series>/lpfit.pkl, per cell and channel: all per-pulse fit parameters, the sum and count of the
aligned traces with fit_ok (samples WIN_LO..WIN_HI, full resolution), a few aligned traces for overlays and one
fit example. Per cell also the PSum example: the sum of the 12 raw channels (each minus its own baseline) of the
event whose (despiked, low-passed) PSum amplitude is closest to the series median; stored unfiltered, full trace, ADC.

Usage: python3 lp_template_led.py SERIES [NPROC]
"""
import csv, json, os, pickle, sys, time
from collections import defaultdict
from multiprocessing import Pool
import numpy as np
from scipy.ndimage import median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
Z7_CHAIN = ("/users/9/li004628/urop/snolab_phonon_pulse_analysis/phonon_pulse_template_generation/"
            "R4/lp_fit_align/scripts")
sys.path.insert(0, Z7_CHAIN)
import lp_fit_align as lp                                   # noqa: E402  (unchanged Z7 chain)
from extract_led_events import triggered_files, events_of, MEDFILT   # noqa: E402
from analyze_led import OUT, led_ids                       # noqa: E402

WIN_LO, WIN_HI = lp.RISE_REF_IDX - 4000, lp.RISE_REF_IDX + 16000   # stored window of aligned traces
OVERLAY_PER_SERIES = 3
# The Z7 chain starts its fit at sample RISE_REF_IDX (16050), where the low-background Z7 pulses start. The LED
# pulses start ~550 samples (0.9 ms) later (20 % crossing at 16554 / 16606 / 16667 for 1 / 50 / 99 % of the good
# pulses), and for low-SNR pulses the fit then stayed near its start value, 0.9 ms before the pulse: the "aligned"
# pulse landed at +0.9 ms and the template got a second bump there. So every trace is first moved by SHIFT samples,
# which puts the LED pulse where the Z7 chain expects it; the chain itself is unchanged.
LED_START = 16600
SHIFT = LED_START - lp.RISE_REF_IDX
START_TOL = 300           # samples (0.48 ms): a fitted start further from the expected one is a misfit, not used
PSUM_MEDFILT = 31         # samples (50 us): the pickup in the sum of 12 channels is wider than in one channel
CHANS = lp.ALL_CHANS


def load_cells():
    return {(r["phase"], r["led"], r["det"]): r["id"]
            for r in csv.DictReader(open(os.path.join(OUT, "summary", "cells.csv")))}


def to_z7_frame(tr):
    """Despiked trace moved by SHIFT samples so that the LED pulse starts near RISE_REF_IDX (the tail is padded
    with the last value; it lies outside the fit window and the stored window)."""
    a = median_filter(np.asarray(tr, dtype=np.float64), size=MEDFILT, mode="nearest")
    return np.concatenate([a[SHIFT:], np.full(SHIFT, a[-1])])


def fit_channel(task):
    """Z7 chain on all pulses of one (cell, channel); mirrors lp_fit_align.process_channel."""
    cid, ch, traces, events = task
    out = dict(fits=[], sum=np.zeros(WIN_HI - WIN_LO), n=0, overlay=[], example=None)
    for tr, ev in zip(traces, events):
        y = lp.normalize_trace(to_z7_frame(tr))
        if y is None:
            out["fits"].append(dict(event=int(ev), fit=None))
            continue
        fp = lp.fit_trace(y)
        out["fits"].append(dict(event=int(ev), fit=fp))
        if fp is None or not fp["fit_ok"] or abs(fp["pretrigger"] - lp.RISE_REF_IDX) > START_TOL:
            continue
        sh = lp.shift_align(y, fp["pretrigger"])[WIN_LO:WIN_HI]
        out["sum"] += sh; out["n"] += 1
        if len(out["overlay"]) < OVERLAY_PER_SERIES:
            out["overlay"].append(sh.astype(np.float32))
        if out["example"] is None:
            out["example"] = (y[lp.FIT_LO:lp.FIT_HI].astype(np.float32), dict(fp), int(ev))
    out["sum"] = out["sum"].astype(np.float32)
    return cid, ch, out


def main(series, nproc):
    t0 = time.time()
    d = os.path.join(OUT, series)
    tm = json.load(open(os.path.join(d, "timing.json")))
    e = np.load(os.path.join(d, "events.npz"))
    ids = led_ids(tm["groups"])
    cells = load_cells()
    # cell of every event (None when not in a non-zero cell)
    ev_cell = []
    for ph, src, det in zip(e["ev_phase"], e["ev_source"], e["ev_det"]):
        lid = ids.get((str(ph), str(src)))
        ev_cell.append(cells.get((str(ph), "%s#%d" % lid, "Z%d" % det)) if lid else None)
    print("series %s: %d events in %d cells" % (series, sum(c is not None for c in ev_cell),
                                                len({c for c in ev_cell if c})), flush=True)

    traces = defaultdict(lambda: defaultdict(list))   # cid -> ch -> [trace]
    evnum = defaultdict(list)                          # cid -> [event number]
    psum = defaultdict(list)                           # cid -> [(event, PSum raw float32)]
    i = 0
    for f in triggered_files(series):
        for ev, det in events_of(f):
            assert int(ev["event"].get("EventNumber", -1)) == int(e["ev_event"][i]), "event order differs from events.npz"
            cid = ev_cell[i]
            if cid is not None:
                evnum[cid].append(int(e["ev_event"][i]))
                ps = np.zeros(lp.TRACELENGTH)
                for ch in CHANS:
                    a = np.asarray(ev[det].get(ch, []))
                    if a.size != lp.TRACELENGTH:
                        traces[cid][ch].append(None)
                        continue
                    traces[cid][ch].append(a)
                    af = a.astype(np.float64)
                    ps += af - np.median(af[lp.BASELINE_LO:lp.BASELINE_HI])
                psum[cid].append((int(e["ev_event"][i]), ps.astype(np.float32)))
            i += 1
        print("  read %s: %.0f s" % (os.path.basename(f), time.time() - t0), flush=True)
    assert i == len(e["ev_event"]), "read %d events, events.npz has %d" % (i, len(e["ev_event"]))

    tasks = []
    for cid, chs in traces.items():
        for ch, trs in chs.items():
            ok = [(t, ev) for t, ev in zip(trs, evnum[cid]) if t is not None]
            tasks.append((cid, ch, [t for t, _ in ok], [ev for _, ev in ok]))
    tasks.sort(key=lambda t: -len(t[2]))
    res = {}
    with Pool(nproc) as pool:
        for cid, ch, out in pool.imap_unordered(fit_channel, tasks):
            res.setdefault(cid, {})[ch] = out
    print("  fitted %d (cell, channel): %.0f s" % (len(tasks), time.time() - t0), flush=True)

    # PSum example per cell: the event whose PSum amplitude is closest to the series median. Amplitude = peak of
    # the despiked (PSUM_MEDFILT-sample median, removes the LED-drive pickup) and low-passed PSum around the trigger
    examples = {}
    for cid, lst in psum.items():
        amps = []
        for _, ps in lst:
            yl = lp.lowpass(median_filter(ps.astype(np.float64), size=PSUM_MEDFILT, mode="nearest"))
            amps.append(float(np.max(yl[lp.RISE_REF_IDX - 1000:lp.RISE_REF_IDX + 4000])))
        amps = np.array(amps)
        k = int(np.argmin(np.abs(amps - np.median(amps))))
        examples[cid] = dict(event=lst[k][0], psum=lst[k][1], amp=amps[k], amp_median=float(np.median(amps)),
                             n=len(lst))
    pickle.dump(dict(series=series, medfilt=MEDFILT, shift=SHIFT, start_tol=START_TOL, cell_keys={cid: k for k, cid in cells.items()}, win=(WIN_LO, WIN_HI), rise_ref=lp.RISE_REF_IDX, sample_rate=lp.SAMPLERATE,
                     events=dict(evnum), cells=res, psum_example=examples),
                open(os.path.join(d, "lpfit.pkl"), "wb"), protocol=4)
    print("done %s: %.0f s" % (series, time.time() - t0), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else os.cpu_count())
