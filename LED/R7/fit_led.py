"""Analytical fit of the R7 LED pulse templates (Yan, Slack 2026-09-23).

Model (as in Kevin's R37 notebook and analytic_fit.py of 2026-09-28): one rise time shared by
two decay components,
    f(t) = A1 (exp(-t/tau_f1) - exp(-t/tau_r)) + A2 (exp(-t/tau_f2) - exp(-t/tau_r)),  t = (sample - t0)/fs >= 0
with a 2-exponential fallback (A2 = 0) when the 3-exponential fit fails or is degenerate.

Unit of a template: (detector, channel, LED), with the LED named by the detector it belongs to
and its number (analyze_led.led_id), e.g. Z14 PAS1 from LED Z13#5. The LED is a different
physical source in phase 1 and phase 2, so templates are never mixed across phases. For every
unit the pulse-count weighted template of all series is fitted ("pooled"), and every series
with >= MIN_SERIES_PULSES pulses is fitted on its own to give the series-to-series spread.

Output in out/fit/:
  LED_fit_parameters.csv   one row per unit (pooled fit, its errors, series spread, flags)
  LED_fit_per_series.csv   one row per (unit, series)
  LED_analytic_templates.pkl   parameters + pooled templates, keyed (det, channel, LED)
  fit_examples.png, fit_parameters.png

Usage (in the V07-02 container, many CPUs): python3 fit_led.py [NPROC]
"""
import csv, glob, json, os, pickle, sys, warnings
from collections import defaultdict
from multiprocessing import Pool
import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyze_led import OUT, SR, led_ids, shape, corr

np.seterr(all="ignore"); warnings.simplefilter("ignore")
FIT = os.path.join(OUT, "fit")
MIN_SERIES_PULSES = 20
A = 8000                                    # align sample of extract_led_events.py
WIN0, WIN1, STEP = A - 1800, A + 15000, 2   # -2.9 .. +24 ms around the rise


def model3(x, a1, a2, tr, tf1, tf2, base, t0):
    t = (x - t0) / SR
    return np.where(x <= t0, base, base + a1 * (np.exp(-t / tf1) - np.exp(-t / tr)) + a2 * (np.exp(-t / tf2) - np.exp(-t / tr)))


def model2(x, a1, tr, tf1, base, t0):
    t = (x - t0) / SR
    return np.where(x <= t0, base, base + a1 * (np.exp(-t / tf1) - np.exp(-t / tr)))


def guess(tm):
    """Start of the pulse (last sample below 5 % of the peak, walking back from the peak) and its 1/e decay."""
    pk = WIN0 + int(np.argmax(tm[WIN0:WIN1]))
    below = np.where(tm[WIN0:pk] < 0.05 * tm[pk])[0]
    t0 = float(WIN0 + below[-1]) if len(below) else float(pk) - 150
    inv = np.where(tm[pk:WIN1] <= tm[pk] / np.e)[0]
    return max(float(WIN0), t0), (inv[0] / SR if len(inv) else 1e-3)


def fit(tm):
    """Returns dict(model, p, err, rms, flags) with the decay components ordered fast -> slow."""
    x = np.arange(WIN0, WIN1, STEP, dtype=float); y = tm[WIN0:WIN1:STEP].astype(float)
    t0, tf = guess(tm)
    out = None
    lo3, hi3 = [0, 0, 1e-6, 2e-6, 2e-5, -0.2, WIN0], [50, 50, 5e-3, 2e-2, 1.0, 0.2, WIN1]
    starts3 = [[1.2, 0.3, tf * 0.08, tf, tf * 6, 0.0, t0], [1.0, 0.5, tf * 0.05, tf * 0.5, tf * 3, 0.0, t0],
               [1.5, 0.1, tf * 0.1, tf, tf * 15, 0.0, t0]]
    for tag, fn, p0s, lo, hi in (
            ("3-exp", model3, starts3, lo3, hi3),
            ("2-exp", model2, [[1.2, tf * 0.08, tf, 0.0, t0]], [0, 1e-6, 2e-6, -0.2, WIN0], [50, 5e-3, 5e-2, 0.2, WIN1])):
        best = None
        for p0 in p0s:                          # several starts; keep the lowest rms
            p0 = np.clip(p0, np.array(lo) + 1e-12, np.array(hi) - 1e-12)
            try:
                p, cov = curve_fit(fn, x, y, p0=p0, bounds=(lo, hi), maxfev=8000)
            except Exception:
                continue
            rms = float(np.sqrt(np.mean((fn(x, *p) - y) ** 2)))
            if best is None or rms < best[2]:
                best = (p, cov, rms)
        if best is None:
            continue
        p, cov, rms = best
        err = np.sqrt(np.abs(np.diag(cov)))
        lo_, hi_ = np.array(lo), np.array(hi)
        at_bound = np.any(np.isclose(p, lo_, rtol=1e-3, atol=0) | np.isclose(p, hi_, rtol=1e-3, atol=0))
        if tag == "3-exp":
            a1, a2, tr, tf1, tf2, base, t0f = p
            if tf1 > tf2:
                p = np.array([a2, a1, tr, tf2, tf1, base, t0f]); err = err[[1, 0, 2, 4, 3, 5, 6]]
            a1, a2, tr, tf1, tf2 = p[:5]
            flags = []
            if at_bound: flags.append("at_bound")
            if tf2 < 1.3 * tf1: flags.append("tf1~tf2")
            if min(a1, a2) < 0.01 * (a1 + a2): flags.append("one_component")
            if tr > 0.8 * tf1: flags.append("rise~fall")
            if flags and out is None:           # degenerate: keep it, but try the 2-exp model too
                out = dict(model=tag, p=p, err=err, rms=rms, flags=flags)
                continue
            return dict(model=tag, p=p, err=err, rms=rms, flags=flags)
        r = dict(model=tag, p=np.array([p[0], 0.0, p[1], p[2], np.nan, p[3], p[4]]),
                 err=np.array([err[0], 0.0, err[1], err[2], np.nan, err[3], err[4]]), rms=rms,
                 flags=(["at_bound"] if at_bound else []))
        # prefer the degenerate 3-exp only if it is clearly better
        if out is not None and out["rms"] < 0.8 * rms:
            return out
        return r
    return out or dict(model="fail", p=None, err=None, rms=np.nan, flags=["fail"])


def collect():
    """{(det, ch, led): {series: (template, n)}}; also which units mix an overlapping group."""
    units = defaultdict(dict)
    for d in sorted(glob.glob(os.path.join(OUT, "2426*"))):
        s = os.path.basename(d)
        if not os.path.exists(os.path.join(d, "timing.json")):
            continue
        tm = json.load(open(os.path.join(d, "timing.json")))
        tp = pickle.load(open(os.path.join(d, "templates.pkl"), "rb"))
        assert tp["align_sample"] == A
        gid = led_ids(tm["groups"])
        for (det, ph, ch, src), t in tp["templates"].items():
            lid = gid.get((str(ph), str(src)))
            if lid is None:
                continue
            key = (str(det), str(ch), "%s#%d" % lid)
            n = tp["n_pulses"][(det, ph, ch, src)]
            old = units[key].get(s)
            if old is not None:                  # same LED split in two groups: merge
                t = (old[0] * old[1] + t * n) / (old[1] + n); n += old[1]
            units[key][s] = (np.asarray(t, dtype=np.float64), n)
    return units


def job(args):
    key, s, t = args
    return key, s, fit(t)


def us(v):
    return "" if v is None or not np.isfinite(v) else round(float(v) * 1e6, 1)


def channel_amplitudes():
    """{(det, ch, led): median over series of the median pulse amplitude (ADC)} from stability_led.py."""
    p = os.path.join(OUT, "stability", "stability_per_series.csv")
    amps = defaultdict(list)
    for r in csv.DictReader(open(p)):
        amps[(r["det"], r["channel"], r["led"])].append(float(r["amp_median"]))
    return {k: float(np.median(v)) for k, v in amps.items()}


def pool(d):
    """Pulse-count weighted mean of the per-series templates, leaving out series whose shape is off
    (correlation with the first-pass mean below min(0.98, median - 0.05); only series with
    >= MIN_SERIES_PULSES pulses can be dropped). Returns template, pulses, used, dropped series."""
    n0 = sum(n for _, n in d.values())
    first = sum(t * n for t, n in d.values()) / n0
    c = {s: corr(t, first, A) for s, (t, n) in d.items()}
    cut = min(0.98, float(np.median(list(c.values()))) - 0.05)
    drop = sorted(s for s, (t, n) in d.items() if n >= MIN_SERIES_PULSES and c[s] < cut)
    keep = {s: v for s, v in d.items() if s not in drop}
    ntot = sum(n for _, n in keep.values())
    return sum(t * n for t, n in keep.values()) / ntot, ntot, sorted(keep), drop


def fitted_curve(x, q):
    return model3(x, *q["p"]) if q["model"] == "3-exp" else model2(x, q["p"][0], q["p"][2], q["p"][3], q["p"][5], q["p"][6])


def main(nproc, per_series=False):
    os.makedirs(FIT, exist_ok=True)
    units = collect()
    amp = channel_amplitudes()
    pooled, info = {}, {}
    for key, d in units.items():
        t, n, used, drop = pool(d)
        pooled[key] = (t, n); info[key] = (used, drop)
    # detector total per (det, LED): channel templates weighted by the channel's typical amplitude
    by_dl = defaultdict(list)
    for (det, ch, led) in pooled:
        by_dl[(det, led)].append(ch)
    for (det, led), chans in by_dl.items():
        w = {ch: amp.get((det, ch, led), 0.0) for ch in chans}
        if sum(w.values()) <= 0:
            continue
        tot = sum(w[ch] * pooled[(det, ch, led)][0] for ch in chans)
        tot = tot / tot.max()
        n = max(pooled[(det, ch, led)][1] for ch in chans)
        used = sorted({s for ch in chans for s in info[(det, ch, led)][0]})
        pooled[(det, "total", led)] = (tot, n); info[(det, "total", led)] = (used, [])
    tasks = [(key, "pooled", t) for key, (t, n) in pooled.items()]
    if per_series:
        tasks += [(key, s, t) for key, d in units.items() for s, (t, n) in d.items() if n >= MIN_SERIES_PULSES]
    print("%d templates (%d detector totals), %d fits" % (len(pooled), sum(k[1] == "total" for k in pooled), len(tasks)), flush=True)
    with Pool(nproc) as p_:
        res = p_.map(job, tasks, chunksize=4)
    R = defaultdict(dict)
    for key, s, r in res:
        R[key][s] = r

    rows, prow, analytic = [], [], {}
    order = sorted(pooled, key=lambda k: (int(k[0][1:]), k[2], k[1] != "total", k[1]))
    for key in order:
        det, ch, led = key
        tmpl, ntot = pooled[key]
        rise_1090, decay_1e = shape(tmpl, A)
        noise = float(np.std(tmpl[WIN0:A - 200]))      # pre-pulse rms of the template: fit_rms cannot go below it
        r = R[key]["pooled"]
        flags = list(r["flags"])
        if rise_1090 < 10e-6:
            flags.append("spike_not_phonon")
        used, drop = info[key]
        row = dict(det=det, channel=ch, led=led, own_led=(led.split("#")[0] == det), n_series=len(used),
                   series_dropped=";".join(drop), n_pulses=ntot,
                   rise_1090_us=us(rise_1090), decay_1e_us=us(decay_1e), model=r["model"])
        if r["p"] is not None:
            p, e = r["p"], r["err"]
            row.update(tau_rise_us=us(p[2]), tau_rise_err_us=us(e[2]), tau_fall1_us=us(p[3]), tau_fall1_err_us=us(e[3]),
                       tau_fall2_us=us(p[4]), tau_fall2_err_us=us(e[4]),
                       A1=round(p[0], 4), A2=round(p[1], 4), frac_fast=round(p[0] / (p[0] + p[1]), 3),
                       t0_sample=round(p[6], 1), fit_rms=round(r["rms"], 4), template_noise_rms=round(noise, 4))
            analytic[key] = dict(model=r["model"], A1=p[0], A2=p[1], tau_rise=p[2], tau_fall1=p[3], tau_fall2=p[4],
                                 t0_sample=p[6], rms=r["rms"], flags=flags, n_pulses=ntot, series=used,
                                 template=tmpl.astype(np.float32))
        row["flags"] = "|".join(flags)
        rows.append(row)
        if per_series:
            for s, q in sorted(R[key].items()):
                if s != "pooled" and q["model"] != "fail":
                    prow.append(dict(det=det, channel=ch, led=led, series=s, n_pulses=units[key][s][1], model=q["model"],
                                     tau_rise_us=us(q["p"][2]), tau_fall1_us=us(q["p"][3]), tau_fall2_us=us(q["p"][4]),
                                     fit_rms=round(q["rms"], 4), flags="|".join(q["flags"])))

    fields = list(max(rows, key=len))
    with open(os.path.join(FIT, "LED_fit_parameters.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval=""); w.writeheader(); w.writerows(rows)
    if prow:
        with open(os.path.join(FIT, "LED_fit_per_series.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(prow[0])); w.writeheader(); w.writerows(prow)
    pickle.dump(dict(function="f(t)=A1*(exp(-t/tau_fall1)-exp(-t/tau_rise))+A2*(exp(-t/tau_fall2)-exp(-t/tau_rise)), "
                                "t=(sample-t0_sample)/sample_rate >= 0; A2=0 for the 2-exp model; templates peak-normalised; "
                                "key (detector, channel or 'total', LED 'owner#number')",
                     sample_rate=SR, align_sample=A, units=analytic),
                open(os.path.join(FIT, "LED_analytic_templates.pkl"), "wb"))
    ok = [r for r in rows if r["model"] != "fail"]
    print("templates %d, fitted %d (3-exp %d, 2-exp %d), no flags %d, rms median %.4f, series dropped in %d"
          % (len(rows), len(ok), sum(r["model"] == "3-exp" for r in ok), sum(r["model"] == "2-exp" for r in ok),
             sum(not r["flags"] for r in ok), np.median([r["fit_rms"] for r in ok]), sum(bool(r["series_dropped"]) for r in rows)))

    # one panel per (detector, LED): channel templates, detector total and its analytic fit
    x = np.arange(WIN0, WIN1, STEP, dtype=float); ms = (x - A) / SR * 1e3
    dls = sorted({(k[0], k[2]) for k in pooled}, key=lambda k: (int(k[0][1:]), k[1]))
    nc = 6; nr = (len(dls) + nc - 1) // nc
    fig, axes = plt.subplots(nr, nc, figsize=(3.6 * nc, 3.0 * nr + 1.2), squeeze=False); axes = axes.ravel()
    for ax, (det, led) in zip(axes, dls):
        for k in pooled:
            if (k[0], k[2]) == (det, led) and k[1] != "total":
                ax.plot(ms, pooled[k][0][WIN0:WIN1:STEP], lw=0.4, alpha=0.6)
        tk = (det, "total", led)
        if tk in pooled:
            ax.plot(ms, pooled[tk][0][WIN0:WIN1:STEP], "k", lw=1.4)
            q = R[tk]["pooled"]
            rr = next(r for r in rows if (r["det"], r["channel"], r["led"]) == tk)
            if q["p"] is not None:
                ax.plot(ms, fitted_curve(x, q), "r--", lw=1)
            ax.set_title("%s <- %s LED %s (%d series)\nrise %s, fall %s / %s us %s"
                         % (det, led.split("#")[0], led.split("#")[1], rr["n_series"], rr.get("tau_rise_us", ""),
                            rr.get("tau_fall1_us", ""), rr.get("tau_fall2_us", ""),
                            "[spike]" if "spike" in rr["flags"] else ""), fontsize=7)
        ax.set_xlim(-0.5, 5); ax.set_ylim(-0.3, 1.1); ax.tick_params(labelsize=6); ax.grid(alpha=0.3)
    for ax in axes[len(dls):]:
        ax.axis("off")
    fig.suptitle("LED pulse templates, all series combined, and analytic fit (x: ms from the pulse rise; y: normalised to peak 1)")
    fig.text(0.01, 0.003,
             "How to read: one panel per detector and LED ('Z14 <- Z13 LED 5' = detector Z14's response to LED 5 of Z13). "
             "Thin coloured lines = the 12 channel templates (each the mean of its good pulses over all series).\n"
             "Black = detector total (channels added with their typical amplitudes). Red dashed = analytic fit "
             "f(t) = A1(exp(-t/fall1) - exp(-t/rise)) + A2(exp(-t/fall2) - exp(-t/rise)); its time constants are in the title.\n"
             "[spike] = a few-us spike, not a phonon pulse. Per-channel fit parameters: out/fit/LED_fit_parameters.csv.",
             fontsize=9, va="bottom", family="monospace")
    fig.tight_layout(rect=(0, 1.0 / (3.0 * nr + 1.2), 1, 0.98))
    fig.savefig(os.path.join(FIT, "LED_templates_fits.png"), dpi=90); plt.close(fig)

    # time constants per (detector, LED): all channels as points, detector total as a star
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    labs = [k for k in dls if (k[0], "total", k[1]) in pooled]
    for ax, k, lab in zip(axes, ("tau_rise_us", "tau_fall1_us", "tau_fall2_us"), ("rise [us]", "fast fall [us]", "slow fall [us]")):
        for j, (det, led) in enumerate(labs):
            rr = [r for r in ok if (r["det"], r["led"]) == (det, led) and r.get(k, "") != ""]
            spike = any("spike" in r["flags"] for r in rr if r["channel"] == "total")
            c = "C3" if spike else ("C0" if led.split("#")[0] == det else "C1")
            ax.plot([j] * sum(r["channel"] != "total" for r in rr), [float(r[k]) for r in rr if r["channel"] != "total"],
                    "o", ms=3, color=c, alpha=0.5)
            ax.plot([j] * sum(r["channel"] == "total" for r in rr), [float(r[k]) for r in rr if r["channel"] == "total"],
                    "*", ms=10, color="k")
        ax.set_yscale("log"); ax.set_ylabel(lab); ax.grid(alpha=0.3)
    axes[-1].set_xticks(range(len(labs)))
    axes[-1].set_xticklabels(["%s <- %s LED%s" % (d, l.split("#")[0], l.split("#")[1]) for d, l in labs], rotation=90, fontsize=7)
    axes[0].set_title("fitted time constants: dots = single channels (blue own LED, orange a neighbour's LED, red us spikes), "
                      "black star = detector total")
    fig.tight_layout(); fig.savefig(os.path.join(FIT, "fit_parameters.png"), dpi=100); plt.close(fig)
    print("wrote", FIT)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(int(args[0]) if args else os.cpu_count(), per_series="--per-series" in sys.argv)
