"""Stability of the LED response over the LEDStability series (amplitude, shape, trigger rate).

For every series in out/ and every (detector, channel, LED) -- the LED named by
analyze_led.led_id -- it takes the 'good' pulses of the events in that LED's flash group and
records the median amplitude (ADC above baseline), its 16-84 % spread, the fraction of
low-amplitude pulses (< half the median: a second population, e.g. Z19 PAS1 in 24260915_165436),
the median 10-90 % rise and 1/e decay of the single pulses, the amplitude drift inside the
150 s phase (last third / first third), and per (detector, LED) the fraction of the flashes the
detector triggers on.

Output in out/stability/:
  stability_per_series.csv   one row per (series, det, channel, LED)
  stability_summary.csv      one row per (det, channel, LED): series-to-series scatter, slope per
                             day, largest jump between consecutive series
  trigger_fraction.csv       one row per (series, det, LED)
  amplitude_vs_time.png      amplitude / its median over the series, per (det, LED), channels as lines
  trigger_fraction.png

Usage: python3 stability_led.py
"""
import csv, glob, json, os, pickle
from collections import defaultdict
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyze_led import OUT, led_ids, n_flashes

ST = os.path.join(OUT, "stability")
MIN_PULSES = 20


def series_time(s):
    return datetime.strptime(s[2:], "%y%m%d_%H%M%S")


# Sequencer script in use (as actually run; the ODB start comment kept the 0913 text throughout and is wrong)
SCRIPT_SWITCH = datetime(2026, 9, 18, 22, 0)


def script_of(s):
    return "20260913" if series_time(s) < SCRIPT_SWITCH else "20260918"


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    os.makedirs(ST, exist_ok=True)
    rows, trows, irows = [], [], []
    for d in sorted(glob.glob(os.path.join(OUT, "2426*"))):
        s = os.path.basename(d)
        if not os.path.exists(os.path.join(d, "timing.json")):
            continue
        tm = json.load(open(os.path.join(d, "timing.json")))
        e = np.load(os.path.join(d, "events.npz"))
        ev_led = np.full(len(e["ev_time"]), "", dtype=object)
        nflash = {}
        ids = led_ids(tm["groups"])
        for g in tm["groups"]:
            lid = ids[(g["phase"], g["name"])]
            if lid is None:
                continue
            m = (e["ev_source"] == g["name"]) & (e["ev_phase"] == g["phase"])
            ev_led[m] = "%s#%d" % lid
            k = "%s#%d" % lid
            nflash[k] = (max(n_flashes(g), nflash.get(k, (0, ""))[0]), g["phase"])
        for led in nflash:
            irows.append(dict(series=s, led=led, phase=nflash[led][1], n_flashes=nflash[led][0]))
        # trigger fraction per (det, LED)
        for led, (nf, ph) in nflash.items():
            for det in np.unique(e["ev_det"][ev_led == led]):
                trows.append(dict(series=s, time=series_time(s).isoformat(), det="Z%d" % det, led=led, phase=ph,
                                  n_triggers=int(np.sum((ev_led == led) & (e["ev_det"] == det))), n_flashes=nf))
        # pulses
        ci = e["ch_ev"]
        good = (e["ch_tag"] == 0) & (e["ch_pol"] > 0)      # positive good pulses (a negative one is pickup, not light)
        led_c, det_c, t_c = ev_led[ci], e["ev_det"][ci], e["ev_time"][ci]
        for led in nflash:
            for det in np.unique(det_c[good & (led_c == led)]):
                for ch in np.unique(e["ch_chan"][good & (led_c == led) & (det_c == det)]):
                    m = good & (led_c == led) & (det_c == det) & (e["ch_chan"] == ch)
                    if m.sum() < MIN_PULSES:
                        continue
                    a, t = e["ch_amp"][m], t_c[m]
                    med = np.median(a)
                    third = (t.max() - t.min()) / 3
                    first, last = a[t < t.min() + third], a[t > t.max() - third]
                    rows.append(dict(series=s, time=series_time(s).isoformat(), script=script_of(s), det="Z%d" % det,
                                     channel=ch, led=led, phase=nflash[led][1], n_pulses=int(m.sum()),
                                     amp_median=round(float(med), 1), amp_p16=round(float(np.percentile(a, 16)), 1),
                                     amp_p84=round(float(np.percentile(a, 84)), 1),
                                     frac_low=round(float(np.mean(a < 0.5 * med)), 3),
                                     drift_last_over_first=round(float(np.median(last) / np.median(first)), 4) if len(first) > 5 and len(last) > 5 else "",
                                     rise_1090_us=round(float(np.nanmedian(e["ch_t1090"][m])) * 1e6, 1),
                                     decay_1e_us=round(float(np.nanmedian(e["ch_tdecay"][m])) * 1e6, 1)))
        print(s, len(nflash), "LEDs", flush=True)
    write_csv(os.path.join(ST, "stability_per_series.csv"), rows)
    write_csv(os.path.join(ST, "trigger_fraction.csv"), trows)
    write_csv(os.path.join(ST, "leds_identified.csv"), irows)     # LEDs assigned to a flash group, per series

    # summary per (det, channel, LED)
    by = defaultdict(list)
    for r in rows:
        by[(r["det"], r["channel"], r["led"])].append(r)
    srows = []
    for (det, ch, led), rr in sorted(by.items(), key=lambda kv: (int(kv[0][0][1:]), kv[0][2], kv[0][1])):
        rr.sort(key=lambda r: r["time"])
        a = np.array([r["amp_median"] for r in rr])
        days = np.array([(datetime.fromisoformat(r["time"]) - datetime(2026, 9, 15)).total_seconds() / 86400 for r in rr])
        rel = a / np.median(a)
        jumps = np.abs(np.diff(rel)) if len(rel) > 1 else np.array([0.0])
        j = int(np.argmax(jumps)) if len(rel) > 1 else 0
        srows.append(dict(det=det, channel=ch, led=led, own_led=(led.split("#")[0] == det), n_series=len(rr),
                          amp_median=round(float(np.median(a)), 1), amp_rel_std=round(float(np.std(rel)), 4),
                          amp_min_rel=round(float(rel.min()), 3), amp_max_rel=round(float(rel.max()), 3),
                          slope_per_day=round(float(np.polyfit(days, rel, 1)[0]), 4) if len(rr) > 2 else "",
                          max_jump=round(float(jumps.max()), 3),
                          max_jump_between=("%s -> %s" % (rr[j]["series"], rr[j + 1]["series"]) if len(rr) > 1 else ""),
                          max_frac_low=max(r["frac_low"] for r in rr),
                          series_max_frac_low=max(rr, key=lambda r: r["frac_low"])["series"],
                          rise_rel_std=round(float(np.std([r["rise_1090_us"] for r in rr]) / np.median([r["rise_1090_us"] for r in rr])), 3),
                          decay_rel_std=round(float(np.std([r["decay_1e_us"] for r in rr]) / np.median([r["decay_1e_us"] for r in rr])), 3)))
    write_csv(os.path.join(ST, "stability_summary.csv"), srows)

    # amplitude vs time, one panel per (det, LED)
    units = sorted({(r["det"], r["led"]) for r in rows}, key=lambda k: (int(k[0][1:]), k[1]))
    nc = 6; nr = (len(units) + nc - 1) // nc
    fig, axes = plt.subplots(nr, nc, figsize=(3.4 * nc, 2.5 * nr), sharex=True, squeeze=False); axes = axes.ravel()
    for ax, (det, led) in zip(axes, units):
        for (d_, ch, l_), rr in by.items():
            if (d_, l_) != (det, led):
                continue
            t = [datetime.fromisoformat(r["time"]) for r in rr]; a = np.array([r["amp_median"] for r in rr])
            ax.plot(t, a / np.median(a), ".-", lw=0.6, ms=3)
        ax.axvline(SCRIPT_SWITCH, color="r", lw=0.6, ls=":")
        ax.set_title("detector %s  <-  %s LED %s" % ((det,) + tuple(led.split("#"))), fontsize=8); ax.set_ylim(0.7, 1.3); ax.axhline(1, color="k", lw=0.4)
        ax.tick_params(labelsize=6); ax.grid(alpha=0.3)
    for ax in axes[len(units):]:
        ax.axis("off")
    fig.autofmt_xdate()
    fig.suptitle("median LED pulse amplitude per series / its median over the series \n(one line per channel; red dotted line: 0913 -> 0918 script, 2026-09-18 22:00)")
    fig.text(0.01, 0.003,
             "How to read: each panel = one detector seeing one LED ('detector Z2 <- Z1 LED 4': Z2's response to LED 4 of Z1). "
             "Each line = one readout channel of that detector.\n"
             "y = median pulse amplitude of that channel in one series / its median over all series (1.0 = typical, 0.8 = 20 % lower). "
             "x = date and time the series started. Red dotted line = switch from the 0913 to the 0918 sequencer script.\n"
             "All lines of a panel moving together = the light or the detector changed; one line alone = that channel changed.",
             fontsize=9, va="bottom", family="monospace")
    fig.tight_layout(rect=(0, 0.035, 1, 0.975)); fig.savefig(os.path.join(ST, "amplitude_vs_time.png"), dpi=90); plt.close(fig)

    # trigger fraction vs time
    tu = sorted({(r["det"], r["led"]) for r in trows}, key=lambda k: (int(k[0][1:]), k[1]))
    fig, ax = plt.subplots(figsize=(14, 6))
    for k in tu:
        rr = sorted((r for r in trows if (r["det"], r["led"]) == k), key=lambda r: r["time"])
        if len(rr) < 3:
            continue
        ax.plot([datetime.fromisoformat(r["time"]) for r in rr], [r["n_triggers"] / r["n_flashes"] for r in rr], ".-", lw=0.7, label="%s / %s" % k)
    ax.axvline(SCRIPT_SWITCH, color="r", lw=0.8, ls=":")
    ax.set_ylabel("fraction of the 151 flashes the detector triggers on"); ax.legend(fontsize=6, ncol=4, title="detector / LED (owner#number)", title_fontsize=7); ax.grid(alpha=0.3)
    ax.set_title("trigger fraction per series: 1.0 = the detector triggers on every one of the 151 flashes of that LED")
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(os.path.join(ST, "trigger_fraction.png"), dpi=90); plt.close(fig)
    print("wrote", ST)


if __name__ == "__main__":
    main()
