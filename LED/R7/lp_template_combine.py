"""Combine the per-series Z7-chain pulse fits (lp_template_led.py) into one template per cell and channel,
fit the analytic pulse, and draw the figures.

Per cell (out/summary/cells.csv) and channel, over all series:
  - measured template: mean of the aligned low-passed traces with fit_ok (as the Z7 chain's aligned mean);
  - Z7 1x1 template: NRMSE-weighted mean of the fitted 2-exp curves (lp_fit_align.nrmse_weighted_fit_mean);
  - per-pulse 2-exp time constants (median, 16-84 %), fit_ok fraction, median NRMSE;
  - signal: at least PULSE_FRAC_SIGNAL of the cell's events have a pulse in that channel by the Part-2 cuts
    (events.npz tag good, glitch or bipolar: SNR >= 8 and a rise found), else "no signal"
    (the LED light does not reach that channel, or the pulses are below SNR 8);
  - analytic pulse: fit_led.fit (one rise, two falls; 2-exp fallback) of the measured template.
Per cell also the detector template (PSum-like): signal channels added with their typical amplitude.

Output in out/lpfit/: LED_cell_templates.csv, LED_cell_templates.pkl, cell_<ID>.png (one per cell),
cells_overview.png, example_pulses_<ID>.png and shape_vs_time_<ID>.png (default ID: Z7 <- Z7 LED0).

Usage: python3 lp_template_combine.py [EXAMPLE_CELL_ID]
"""
import csv, glob, os, pickle, sys
from collections import defaultdict
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.ndimage import median_filter
from scipy.signal import butter, sosfilt, sosfilt_zi
from lp_template_led import lp, WIN_LO, WIN_HI, CHANS, PSUM_MEDFILT, START_TOL
from analyze_led import OUT
import fit_led

LP = os.path.join(OUT, "lpfit")
SR = lp.SAMPLERATE
PULSE_FRAC_SIGNAL = 0.3
EXAMPLE_LP_KHZ = 40.0                     # low-pass of the example-pulse figure (Prof. Liu)
PULSE_TAGS = (0, 1, 6)                     # extract_led_events.TAGS: good, glitch, bipolar
A = fit_led.A                              # fit_led works on a 32768 array aligned at sample 8000
X_MS = (np.arange(WIN_LO, WIN_HI) - lp.RISE_REF_IDX) / SR * 1e3


def to_fitframe(win):
    """Place a stored window (aligned at RISE_REF_IDX) into a 32768 array aligned at fit_led.A."""
    arr = np.zeros(lp.TRACELENGTH)
    arr[A - (lp.RISE_REF_IDX - WIN_LO):A + (WIN_HI - lp.RISE_REF_IDX)] = win
    return arr


def analytic(win):
    r = fit_led.fit(to_fitframe(win))
    if r["p"] is None:
        return r, None
    x = np.arange(lp.TRACELENGTH, dtype=float)
    curve = fit_led.model3(x, *r["p"]) if r["model"] == "3-exp" else \
        fit_led.model2(x, r["p"][0], r["p"][2], r["p"][3], r["p"][5], r["p"][6])
    return r, curve[A - (lp.RISE_REF_IDX - WIN_LO):A + (WIN_HI - lp.RISE_REF_IDX)]


def series_time(s):
    return datetime.strptime(s[2:], "%y%m%d_%H%M%S")


def us(v):
    return "" if v is None or not np.isfinite(v) else round(float(v) * 1e6, 1)


def plot_example(example_id, cells, psum, per_series, store):
    # example pulses (Prof. Liu): one PSum per series, normalised to its peak, 40 kHz low-pass, light -> dark in time.
    # The raw-ADC panels were dropped at his request.
    c = cells[example_id]
    lst = sorted(psum[example_id], key=lambda x: x[0])
    # light -> dark in time, through several hues (yellow-green -> teal -> blue -> purple): with 45 overlapping
    # traces a single hue hides which day a line belongs to
    cmap = plt.get_cmap("viridis_r")
    C0 = 0.08
    cols = [cmap(C0 + (1 - C0) * i / max(len(lst) - 1, 1)) for i in range(len(lst))]
    sos = butter(4, EXAMPLE_LP_KHZ * 1e3 / (0.5 * SR), btype="low", output="sos")
    zi = sosfilt_zi(sos)
    x_full = np.arange(lp.TRACELENGTH) / SR * 1e3
    fig, ax = plt.subplots(figsize=(11.5, 5.0))
    for (t, s, ex), col in zip(lst, cols):
        # wide median filter (removes the LED pickup spike), then the low-pass (steady-state start, as lp.lowpass)
        y = median_filter(ex["psum"].astype(np.float64), size=PSUM_MEDFILT, mode="nearest")
        yl, _ = sosfilt(sos, y, zi=zi * y[0])
        pk = np.max(yl[lp.RISE_REF_IDX - 1000:lp.RISE_REF_IDX + 4000])
        ax.plot(x_full, yl / pk, color=col, lw=0.9)
    t0 = lp.RISE_REF_IDX / SR * 1e3
    ax.set_xlim(t0 - 1, t0 + 8); ax.set_ylim(-0.2, 1.1); ax.grid(alpha=0.25); ax.tick_params(labelsize=12)
    ax.set_xlabel("time in the trace [ms]", fontsize=13); ax.set_ylabel("PSum / its peak", fontsize=13)
    ax.set_title("%s PSum on LED %s of %s: one pulse per series (%d series), %.0f kHz low-pass" %
                 (c["det"], c["led"].split("#")[1], c["led"].split("#")[0], len(lst), EXAMPLE_LP_KHZ), fontsize=12)
    sm = plt.cm.ScalarMappable(cmap=matplotlib.colors.LinearSegmentedColormap.from_list("b", [cmap(v) for v in np.linspace(C0, 1.0, 64)]),
                               norm=plt.Normalize(mdates.date2num(lst[0][0]), mdates.date2num(lst[-1][0])))
    cb = fig.colorbar(sm, ax=ax, pad=0.02)
    cb.ax.yaxis.set_major_formatter(mdates.DateFormatter("%d %b")); cb.ax.tick_params(labelsize=11)
    cb.set_label("series start (light = early, dark = late)", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(LP, "example_pulses_%s.png" % example_id), dpi=160); plt.close(fig)

    # the same pulses with the time axis zoomed on the rising edge (Prof. Liu: does the rise time drift?).
    # Left: exactly the figure above, zoomed. Right: each pulse moved so that it crosses half of its peak at 0,
    # which takes out the trigger-time jitter and leaves only the slope of the edge.
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.2), sharey=True)
    rows = []
    for (t, s, ex), col in zip(lst, cols):
        y = median_filter(ex["psum"].astype(np.float64), size=PSUM_MEDFILT, mode="nearest")
        yl, _ = sosfilt(sos, y, zi=zi * y[0])
        lo = lp.RISE_REF_IDX - 1000
        ip = lo + int(np.argmax(yl[lo:lp.RISE_REF_IDX + 4000])); pk = yl[ip]
        yn = yl / pk
        axes[0].plot(x_full, yn, color=col, lw=0.9)

        def cross(level):                      # last upward crossing of `level` before the peak, in samples
            j = ip
            while j > lo and yn[j - 1] >= level:
                j -= 1
            return j - 1 + (level - yn[j - 1]) / (yn[j] - yn[j - 1])
        x50 = cross(0.5)
        axes[1].plot((np.arange(lp.TRACELENGTH) - x50) / SR * 1e6, yn, color=col, lw=0.9)
        rows.append((t, s, (cross(0.9) - cross(0.2)) / SR * 1e6, x50 / SR * 1e3))
    tp = float(np.median([r[3] for r in rows]))
    axes[0].set_xlim(tp - 0.25, tp + 0.55); axes[0].set_ylim(-0.25, 1.1)
    axes[0].set_xlabel("time in the trace [ms]", fontsize=13); axes[0].set_ylabel("PSum / its peak", fontsize=13)
    axes[0].set_title("as recorded, time axis zoomed", fontsize=12)
    axes[1].set_xlim(-150, 300)
    axes[1].set_xlabel("time from the half-height point of the rising edge [us]", fontsize=13)
    axes[1].set_title("each pulse moved to cross half of its peak at 0", fontsize=12)
    for ax in axes:
        ax.grid(alpha=0.25); ax.tick_params(labelsize=12)
    cb = fig.colorbar(sm, ax=axes, pad=0.015)
    cb.ax.yaxis.set_major_formatter(mdates.DateFormatter("%d %b")); cb.ax.tick_params(labelsize=11)
    cb.set_label("series start (light = early, dark = late)", fontsize=12)
    fig.suptitle("%s PSum on LED %s of %s: rising edge of the %d example pulses (one per series), %.0f kHz low-pass" %
                 (c["det"], c["led"].split("#")[1], c["led"].split("#")[0], len(lst), EXAMPLE_LP_KHZ), fontsize=13)
    fig.savefig(os.path.join(LP, "example_pulses_%s_zoom.png" % example_id), dpi=160, bbox_inches="tight"); plt.close(fig)
    with open(os.path.join(LP, "example_pulses_%s_rise.csv" % example_id), "w") as f:
        f.write("series,rise_20_90_us,half_height_ms\n")
        for t, s, r, x in rows:
            f.write("%s,%.2f,%.4f\n" % (s, r, x))

    # shape vs time of the example cell: per series median per-pulse rise / fall, per channel
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.8), sharex=True)
    for ch in CHANS:
        pts = sorted(per_series.get((example_id, ch), []))
        d = store.get((example_id, ch))
        if not pts or d is None or not d["row"]["signal"]:
            continue
        axes[0].plot([p[0] for p in pts], [p[1] * 1e6 for p in pts], ".-", lw=0.7, ms=3, label=ch)
        axes[1].plot([p[0] for p in pts], [p[2] * 1e6 for p in pts], ".-", lw=0.7, ms=3, label=ch)
    axes[0].set_ylabel("median rise time of the single-pulse fits [us]"); axes[1].set_ylabel("median fall time [us]")
    axes[1].legend(fontsize=7, ncol=2)
    for ax in axes:
        ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.suptitle("%s: pulse shape vs time (one point per series and channel; 2-exp fit of every pulse, Z7 chain)" % example_id)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(os.path.join(LP, "shape_vs_time_%s.png" % example_id), dpi=110); plt.close(fig)
    print("wrote example figures of", example_id)


def main(example_id, example_only=False):
    os.makedirs(LP, exist_ok=True)
    cells = {r["id"]: r for r in csv.DictReader(open(os.path.join(OUT, "summary", "cells.csv")))}
    files = sorted(glob.glob(os.path.join(OUT, "2426*", "lpfit.pkl")))
    acc = defaultdict(lambda: dict(sum=np.zeros(WIN_HI - WIN_LO), n=0, fits=[], overlay=[], example=None))
    psum = defaultdict(list)          # cid -> [(time, series, example dict)]
    per_series = defaultdict(list)    # (cid, ch) -> [(time, median t_rise, median t_fall, n)]
    pulses = defaultdict(lambda: [0, 0, [], [], 0])   # (cid, ch) -> [events with a pulse, events, pulse amplitudes, spike / noise, negative pulses]
    for f in files:
        d = pickle.load(open(f, "rb")); s = d["series"]; t = series_time(s)
        assert "cell_keys" in d, "%s: lpfit.pkl without cell_keys (old run) -- rerun lp_template_led.py" % s
        for cid, k in d["cell_keys"].items():                 # IDs are positional: they must match cells.csv
            assert cid in cells and (cells[cid]["phase"], cells[cid]["led"], cells[cid]["det"]) == tuple(k), \
                "%s: cell %s in lpfit.pkl is %s, cells.csv differs -- rerun lp_template_led.py" % (s, cid, k)
        e = np.load(os.path.join(os.path.dirname(f), "events.npz"))
        evidx = {int(n): i for i, n in enumerate(e["ev_event"])}
        assert len(evidx) == len(e["ev_event"]), "event numbers not unique in %s" % s
        for cid, evs in d["events"].items():
            if example_only and cid != example_id:
                continue
            m = np.isin(e["ch_ev"], np.array([evidx[x] for x in evs]))
            for ch in CHANS:
                mm = m & (e["ch_chan"] == ch)
                ok = mm & np.isin(e["ch_tag"], PULSE_TAGS)
                p = pulses[(cid, ch)]
                p[0] += int(ok.sum()); p[1] += int(mm.sum()); p[2] += list(e["ch_amp"][ok])
                sn = e["ch_spike"][mm] / e["ch_noise_raw"][mm]        # largest excursion removed by the despiking, in raw-noise sigma
                p[3] += list(sn[np.isfinite(sn)])
                p[4] += int((ok & (e["ch_pol"] < 0)).sum())
        for cid, chs in d["cells"].items():
            if example_only and cid != example_id:
                continue
            for ch, o in chs.items():
                a = acc[(cid, ch)]
                a["sum"] += o["sum"]; a["n"] += o["n"]
                allok = [x["fit"] for x in o["fits"] if x["fit"] and x["fit"]["fit_ok"]]
                ok = [fp for fp in allok if abs(fp["pretrigger"] - lp.RISE_REF_IDX) <= START_TOL]     # as used for the sum
                a["n_fit_ok"] = a.get("n_fit_ok", 0) + len(allok)
                a["starts"] = a.get("starts", []) + [fp["pretrigger"] - lp.RISE_REF_IDX for fp in allok]
                a["fits"] += [dict(fp, series=s) for fp in ok]
                a["overlay"] += o["overlay"]
                if a["example"] is None and o["example"] is not None:
                    a["example"] = o["example"]
                if len(ok) >= 5:
                    per_series[(cid, ch)].append((t, np.median([x["t_rise"] for x in ok]),
                                                  np.median([x["t_fall"] for x in ok]), len(ok)))
        for cid, ex in d["psum_example"].items():
            psum[cid].append((t, s, ex))
    print("%d series read, %d (cell, channel)" % (len(files), len(acc)), flush=True)

    rows, store = [], {}
    for cid in ([example_id] if example_only else sorted(cells)):
        c = cells[cid]
        tot, wsum = np.zeros(WIN_HI - WIN_LO), 0.0
        for ch in CHANS:
            a = acc.get((cid, ch))
            if a is None or a["n"] == 0:
                continue
            nall = a["n"]
            mean = a["sum"] / a["n"]
            nr = np.array([fp["nrmse"] for fp in a["fits"]])
            tr = np.array([fp["t_rise"] for fp in a["fits"]]); tf = np.array([fp["t_fall"] for fp in a["fits"]])
            npl, nev, amps, spk, nneg = pulses.get((cid, ch), [0, 0, [], [], 0])
            pulse_frac = npl / nev if nev else 0.0
            # a negative transient in most events, not a phonon pulse (Z18 PFS2, own LED3)
            negative = bool(pulse_frac >= PULSE_FRAC_SIGNAL and nneg > 0.5 * npl)
            signal = bool(pulse_frac >= PULSE_FRAC_SIGNAL) and not negative
            r, curve = analytic(mean) if signal else (dict(model="", p=None, err=None, rms=np.nan,
                                                           flags=["negative_transient" if negative else "no_signal"]), None)
            fitmean = lp.nrmse_weighted_fit_mean(a["fits"], WIN_LO, WIN_HI) if signal else None
            rise_1090, decay_1e = fit_led.shape(to_fitframe(mean), A)
            flags = list(r["flags"])
            if signal and rise_1090 < 10e-6:
                flags.append("spike_not_phonon")
            row = dict(id=cid, phase=c["phase"], led=c["led"], det=c["det"], channel=ch, fraction=c["fraction"],
                       n_pulses_fit_ok=nall, n_fit_ok_all=a.get("n_fit_ok", 0),
                       start_far_fraction=round(1.0 - nall / max(a.get("n_fit_ok", 0), 1), 3),
                       start_us_p05=us(np.percentile(a["starts"], 5) / SR), start_us_p95=us(np.percentile(a["starts"], 95) / SR),
                       median_nrmse=round(float(np.median(nr)), 3),
                       pulse_fraction=round(pulse_frac, 3), amp_median_adc=round(float(np.median(amps)), 1) if amps else "",
                       spike_over_noise_median=round(float(np.median(spk)), 1) if spk else "",
                       spike_gt10sigma_fraction=round(float(np.mean(np.array(spk) > 10)), 3) if spk else "",
                       signal=signal,
                       pulse_t_rise_us_median=us(np.median(tr)), pulse_t_fall_us_median=us(np.median(tf)),
                       pulse_t_fall_us_p16=us(np.percentile(tf, 16)), pulse_t_fall_us_p84=us(np.percentile(tf, 84)),
                       template_rise_1090_us=us(rise_1090), template_decay_1e_us=us(decay_1e), model=r["model"])
            if r["p"] is not None:
                p = r["p"]
                row.update(tau_rise_us=us(p[2]), tau_fall1_us=us(p[3]), tau_fall2_us=us(p[4]), A1=round(p[0], 4),
                           A2=round(p[1], 4), fit_rms=round(r["rms"], 4))
            row["flags"] = "|".join(flags)
            rows.append(row)
            store[(cid, ch)] = dict(mean=mean.astype(np.float32), fit_mean=None if fitmean is None else fitmean.astype(np.float32),
                                    analytic=None if curve is None else curve.astype(np.float32), fit=r, row=row,
                                    overlay=a["overlay"], example=a["example"])
            if signal and "spike_not_phonon" not in flags:
                w = float(np.median(amps)) if amps else 0.0          # typical pulse amplitude of the channel, ADC
                tot += w * mean; wsum += w
        if wsum > 0:
            tot = tot / tot.max()
            r, curve = analytic(tot)
            row = dict(id=cid, phase=c["phase"], led=c["led"], det=c["det"], channel="detector", fraction=c["fraction"],
                       signal=True, model=r["model"], flags="|".join(r["flags"]))
            if r["p"] is not None:
                p = r["p"]
                row.update(tau_rise_us=us(p[2]), tau_fall1_us=us(p[3]), tau_fall2_us=us(p[4]), A1=round(p[0], 4),
                           A2=round(p[1], 4), fit_rms=round(r["rms"], 4))
            rows.append(row)
            store[(cid, "detector")] = dict(mean=tot.astype(np.float32), analytic=None if curve is None else curve.astype(np.float32),
                                            fit=r, row=row)

    if example_only:
        return plot_example(example_id, cells, psum, per_series, store)
    for p in glob.glob(os.path.join(LP, "cell_*.png")):       # cell IDs are positional: no stale figures
        os.remove(p)
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(os.path.join(LP, "LED_cell_templates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval=""); w.writeheader(); w.writerows(rows)
    pickle.dump(dict(note="templates aligned so the fitted pulse start is at sample %d of the trace; window %d..%d; "
                          "analytic = fit_led model3/model2 of the measured template" % (lp.RISE_REF_IDX, WIN_LO, WIN_HI),
                     sample_rate=SR, cells=cells,
                     templates={k: {kk: v for kk, v in d.items() if kk in ("mean", "fit_mean", "analytic", "row")}
                                for k, d in store.items()}),
                open(os.path.join(LP, "LED_cell_templates.pkl"), "wb"), protocol=4)
    print("wrote LED_cell_templates.csv: %d rows, %d channels with signal" % (len(rows), sum(r["signal"] is True for r in rows if r["channel"] != "detector")))

    note = ("Z7 template chain per pulse (after an 11-sample median filter against the LED pickup spikes; trace moved so the LED pulse starts where the Z7 pulses do): 100 kHz low-pass -> baseline (median 2000-12000) -> / peak -> 2-exp fit with free start "
            "-> aligned on the fitted start. Template = mean of the aligned pulses over all series. "
            "Analytic pulse (dashed) = A1(exp(-t/fall1)-exp(-t/rise)) + A2(exp(-t/fall2)-exp(-t/rise)).")

    # one figure per cell: the 12 channels
    for cid, c in cells.items():
        fig, axes = plt.subplots(3, 4, figsize=(16, 9.5), sharex=True); axes = axes.ravel()
        for ax, ch in zip(axes, CHANS):
            d = store.get((cid, ch))
            ax.set_xlim(-0.5, 6); ax.set_ylim(-0.35, 1.15); ax.grid(alpha=0.2); ax.tick_params(labelsize=7)
            if d is None:
                ax.set_title("%s: no pulses" % ch, fontsize=9); continue
            for tr in d["overlay"][:150]:
                ax.plot(X_MS, tr, color="steelblue", lw=0.3, alpha=0.15)
            ax.plot(X_MS, d["mean"], color="crimson", lw=1.3, label="template (mean)")
            r = d["row"]
            if d["analytic"] is not None:
                ax.plot(X_MS, d["analytic"], "k--", lw=1, label="analytic fit")
                ax.plot(X_MS, (d["mean"] - d["analytic"]) - 0.25, color="gray", lw=0.5, label="residual - 0.25")
                ax.set_title("%s  rise %s, fall %s / %s us%s" % (ch, r.get("tau_rise_us", ""), r.get("tau_fall1_us", ""),
                             r.get("tau_fall2_us", ""), "  [spike]" if "spike" in r["flags"] else ""), fontsize=8)
            else:
                ax.set_title(("%s: negative transient, no phonon pulse" % ch) if "negative" in r["flags"] else
                             "%s: no signal (pulse in %.0f %% of the events)" % (ch, 100 * r["pulse_fraction"]), fontsize=8, color="gray")
            ax.text(0.98, 0.95, "%d pulses" % r["n_pulses_fit_ok"], transform=ax.transAxes, ha="right", va="top", fontsize=7)
        axes[0].legend(fontsize=6, loc="center right")
        for ax in axes[8:]:
            ax.set_xlabel("ms from the fitted pulse start", fontsize=8)
        fig.suptitle("%s: detector %s, LED %s of %s (%s), triggers on %.0f %% of the flashes" %
                     (cid, c["det"], c["led"].split("#")[1], c["led"].split("#")[0], c["phase"], 100 * float(c["fraction"])), fontsize=12)
        fig.text(0.01, 0.005, note + "\nBlue: aligned single pulses (up to 150, all series). Red: template. "
                 "Gray: residual of the analytic fit, shifted down by 0.25.", fontsize=7.5, family="monospace", va="bottom")
        fig.tight_layout(rect=(0, 0.05, 1, 0.96))
        fig.savefig(os.path.join(LP, "cell_%s.png" % cid), dpi=110); plt.close(fig)

    # overview: detector template of every cell
    ids = sorted(cells)
    nc = 8; nr = (len(ids) + nc - 1) // nc
    fig, axes = plt.subplots(nr, nc, figsize=(2.6 * nc, 2.2 * nr + 1), squeeze=False); axes = axes.ravel()
    for ax, cid in zip(axes, ids):
        c = cells[cid]; d = store.get((cid, "detector"))
        ax.set_xlim(-0.5, 5); ax.set_ylim(-0.15, 1.1); ax.tick_params(labelsize=5); ax.grid(alpha=0.2)
        ttl = "%s  %s <- %s LED%s" % (cid, c["det"], c["led"].split("#")[0], c["led"].split("#")[1])
        if d is None:
            ax.set_title(ttl + "\nno channel with pulses above SNR 8", fontsize=6.5, color="gray"); continue
        ax.plot(X_MS, d["mean"], color="crimson", lw=1)
        if d["analytic"] is not None:
            ax.plot(X_MS, d["analytic"], "k--", lw=0.8)
        r = d["row"]
        ax.set_title(ttl + "\nrise %s, fall %s / %s us" % (r.get("tau_rise_us", ""), r.get("tau_fall1_us", ""), r.get("tau_fall2_us", "")),
                     fontsize=6.5)
    for ax in axes[len(ids):]:
        ax.axis("off")
    fig.suptitle("Detector template of every non-zero cell (channels with signal, weighted by their typical amplitude); "
                 "red = template, black dashed = analytic fit; x: ms from pulse start", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(LP, "cells_overview.png"), dpi=110); plt.close(fig)

    plot_example(example_id, cells, psum, per_series, store)
    print("wrote", LP)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else "P1-07", example_only="--example-only" in sys.argv)
