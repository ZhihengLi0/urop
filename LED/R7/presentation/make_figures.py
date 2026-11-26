"""Figures and numbers for the R7 LED talk (run in the V07-02 container from LED/R7/talk).

Copies the analysis figures from ../out into figures/ and makes the talk-only ones:
  fig_week_timeline.png     all LED runs of the week on a time axis, and one sequencer cycle (--week: only this)
  fig_run_timeline.png      one run: trigger time vs detector, LED phases
  fig_flash_groups.png      TriggerTime mod 1 s in phase 1 of one run: one peak per LED
  fig_amp_map.png           relative amplitude, cell x series (median over the cell's channels)
  fig_trig_map.png          trigger fraction, cell x series
  fig_stab_cases.png        the amplitude cases worth a second look, readable size
  fig_same_led.png          same LED on two detectors vs same detector with its two LEDs: whose change is it
and writes stats.json with every number quoted on the slides. Needs out/summary/trigger_epochs.csv
(trigger_settings.py) for the trigger-threshold epochs.
"""
import csv, glob, json, os, shutil, sys
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R7 = os.path.dirname(HERE)
sys.path.insert(0, R7)
from analyze_led import led_ids  # noqa: E402

OUT = os.path.join(R7, "out")
FIG = os.path.join(HERE, "figures")
RUN = "24260915_063921"
EXAMPLE = "P1-07"
DROPPED = ["24260916_232802", "24260918_084531"]     # in the series list, not analysed (74 events; no LED flashes)
MSL = os.path.join(os.path.dirname(R7), "SR1a_post-activation_LEDStability_0V_23Det_20260918.msl")


def rd(p):
    return list(csv.DictReader(open(os.path.join(OUT, p))))


def series_time(s):
    return datetime.strptime(s[2:], "%y%m%d_%H%M%S")


def copy(src, dst=None, crop=0.0, crop_top=0.0):
    """Copy an analysis figure into figures/; crop = fraction of the height cut at the bottom (the long
    monospace note that documents the figure in out/ is left out of the talk copy)."""
    p = os.path.join(OUT, src)
    if not os.path.exists(p):
        print("missing", src); return
    d = os.path.join(FIG, dst or os.path.basename(src))
    if crop or crop_top:
        from PIL import Image
        im = Image.open(p)
        im.crop((0, int(round(im.height * crop_top)), im.width, int(round(im.height * (1 - crop))))).save(d)
    else:
        shutil.copy(p, d)


def script_times():
    """Sequencer script: seconds of WAIT between TRANSITION START and STOP per subroutine, and the main loop count."""
    sub, on, out, loop = None, False, defaultdict(float), None
    for l in open(MSL):
        w = l.split("#")[0].strip(); u = w.upper()
        if u.startswith("SUBROUTINE"):
            sub = w.split()[1]
        elif u.startswith("ENDSUBROUTINE"):
            sub = None
        elif u.startswith("TRANSITION START"):
            on = True
        elif u.startswith("TRANSITION STOP"):
            on = False
        elif u.startswith("WAIT SECONDS") and on and sub:
            out[sub] += float(w.split(",")[1])
        elif u.startswith("LOOP") and sub is None and len(w.split()) == 2:
            loop = int(w.split()[1])
    return dict(out), loop


def week_timeline():
    """All LED runs of the week on a time axis (one line per run), and one sequencer cycle drawn from the script's
    wait times. Returns the numbers quoted on the background slide."""
    import matplotlib.dates as mdates
    from stability_led import SCRIPT_SWITCH
    ser = sorted(os.path.basename(os.path.dirname(f)) for f in glob.glob(os.path.join(OUT, "2426*", "timing.json")))
    tms = {s: json.load(open(os.path.join(OUT, s, "timing.json"))) for s in ser}
    run_s = float(np.median([tms[s]["led_off_s"] for s in ser]))
    allser = sorted(ser + DROPPED)
    tt = {s: series_time(s) for s in allser}
    blocks = [[allser[0]]]
    for a, b in zip(allser, allser[1:]):
        if (tt[b] - tt[a]).total_seconds() > 3 * 3600:
            blocks.append([])
        blocks[-1].append(b)
    gaps = [(tt[b] - tt[a]).total_seconds() / 60 for bl in blocks for a, b in zip(bl, bl[1:])]
    cycle = float(np.median(gaps))
    waits, loop = script_times()
    lowbkg = waits["LOW_BACKGROUND"] / 60.0

    fig, (ax, bx) = plt.subplots(2, 1, figsize=(12, 3.85), gridspec_kw=dict(height_ratios=[1.3, 1]))
    pad = timedelta(minutes=25)
    for bl in blocks:
        a, b = tt[bl[0]] - pad, tt[bl[-1]] + timedelta(seconds=run_s) + pad
        ax.axvspan(a, b, color="C0", alpha=0.10, lw=0)
        ax.text(a + (b - a) / 2, 0.84, "%d" % sum(s in tms for s in bl), ha="center", fontsize=12, color="C0")
    ax.vlines([tt[s] for s in ser], 0.12, 0.72, color="C0", lw=1.7, label="LED run, analysed (%d)" % len(ser))
    ax.vlines([tt[s] for s in DROPPED], 0.12, 0.72, color="0.45", lw=1.7, linestyles=":", label="LED run, not used (%d)" % len(DROPPED))
    ax.plot([tt[s] for s in DROPPED], [0.72] * len(DROPPED), "x", color="0.3", ms=7)
    ax.axvline(SCRIPT_SWITCH, color="C3", ls="--", lw=1.1)
    ax.text(SCRIPT_SWITCH + timedelta(minutes=40), 0.02, "script 0913 -> 0918", color="C3", fontsize=10.5, va="bottom")
    d0 = tt[allser[0]].replace(hour=0, minute=0, second=0)
    d1 = tt[allser[-1]].replace(hour=0, minute=0, second=0) + timedelta(days=1)
    ax.set_xlim(d0, d1); ax.set_ylim(0, 1); ax.set_yticks([])
    ax.xaxis.set_major_locator(mdates.DayLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
    ax.grid(axis="x", which="major", color="0.6", lw=0.8); ax.grid(axis="x", which="minor", color="0.88", lw=0.6)
    for lab in ax.get_xticklabels():
        lab.set_ha("left"); lab.set_fontsize(11)
    bx.tick_params(labelsize=11); bx.xaxis.label.set_size(11)
    ax.set_title("LED runs from %s to %s: blue line = one run used (%d), grey dotted = not used (%d)\n"
                 "bands = blocks of consecutive runs, with the number of analysed runs"
                 % (tt[allser[0]].strftime("%d %b %H:%M"), tt[allser[-1]].strftime("%d %b %H:%M"), len(ser), len(DROPPED)), fontsize=11.5)

    tm = tms[RUN]
    x0 = lowbkg + waits.get("LOW_BACKGROUND_after", 300.0) / 60.0            # the script waits 300 s after the stop
    on, sp, off, pz = tm["led_on_s"] / 60, tm["split_s"] / 60, tm["led_off_s"] / 60, tm["pause_s"] / 120
    bx.barh(0, lowbkg, left=0, color="0.75", edgecolor="k", lw=0.6)
    bx.text(lowbkg / 2, 0, "low-background run: %.0f min" % lowbkg, ha="center", va="center", fontsize=12)
    bx.barh(0, on, left=x0, color="C0", alpha=0.25, edgecolor="k", lw=0.6)
    bx.barh(0, sp - pz - on, left=x0 + on, color="C1", alpha=0.75, edgecolor="k", lw=0.6)
    bx.barh(0, off - sp - pz, left=x0 + sp + pz, color="C2", alpha=0.75, edgecolor="k", lw=0.6)
    bx.text(x0 + on / 2, 0, "wait", ha="center", va="center", fontsize=11)
    bx.text(x0 + off / 2, 0.62, "LED run: about %.0f min" % (run_s / 60), ha="center", va="bottom", fontsize=12, color="C0")
    bx.annotate("phase 1: %d flashes" % tm["n_flashes"]["phase1"], (x0 + (on + sp) / 2, -0.4), (x0 + on - 17, -1.3),
                fontsize=11, ha="center", arrowprops=dict(arrowstyle="-", lw=0.7))
    bx.annotate("phase 2: %d flashes" % tm["n_flashes"]["phase2"], (x0 + (sp + off) / 2, -0.4), (x0 + off + 12, -1.3),
                fontsize=11, ha="center", arrowprops=dict(arrowstyle="-", lw=0.7))
    bx.barh(0, cycle - (x0 + off), left=x0 + off, color="w", edgecolor="k", lw=0.6, hatch="///")
    bx.text(cycle + 1.5, 0, "stop, relock,\nthen again", ha="left", va="center", fontsize=11)
    bx.set_xlim(-2, cycle + 22); bx.set_ylim(-1.75, 1.45); bx.set_yticks([])
    bx.set_xlabel("minutes within one sequencer cycle (from the script's wait times; measured: one LED run every %.0f min)" % cycle)
    for sp_ in ("top", "right", "left"):
        bx.spines[sp_].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_week_timeline.png"), dpi=130); plt.close(fig)
    return dict(n_all=len(allser), n_ok=len(ser), dropped=DROPPED, first_all=allser[0], last_all=allser[-1],
                n_blocks=len(blocks), block_sizes=[sum(s in tms for s in bl) for bl in blocks], run_min=round(run_s / 60, 1),
                cycle_min=round(cycle), lowbkg_min=round(lowbkg), script_loop=loop,
                led_wait_script_s=None if "LED_MONITORING" not in waits else waits["LED_MONITORING"])


def main():
    os.makedirs(FIG, exist_ok=True)
    for f in ("stability/amplitude_vs_time.png", "stability/trigger_fraction.png", "lpfit/cells_overview.png",
              "lpfit/shape_vs_time_%s.png" % EXAMPLE):
        copy(f)
    for f in ("summary/visibility_phase1.png", "summary/visibility_phase2.png"):
        copy(f, crop=0.09)
    copy("lpfit/example_pulses_%s.png" % EXAMPLE, crop=0.06, crop_top=0.075)   # the slide carries the title
    cells = rd("summary/cells.csv")
    for c in cells:
        copy("lpfit/cell_%s.png" % c["id"], crop=0.045)
    st = {}
    st["campaign"] = week_timeline()

    # ---- one run: timeline and flash groups
    tm = json.load(open(os.path.join(OUT, RUN, "timing.json")))
    e = np.load(os.path.join(OUT, RUN, "events.npz"))
    t, det = e["ev_time"], e["ev_det"]
    fig, ax = plt.subplots(figsize=(12, 4.2))
    led = np.isin(e["ev_phase"], ["phase1", "phase2"]) & (e["ev_source"] != "bg")
    ax.plot(t[~led], det[~led], "|", color="0.6", ms=5, label="other triggers")
    ax.plot(t[led], det[led], "|", color="C0", ms=5, label="triggers on an LED flash")
    ax.axvspan(tm["led_on_s"], tm["split_s"] - tm["pause_s"] / 2, color="C1", alpha=0.12)
    ax.axvspan(tm["split_s"] + tm["pause_s"] / 2, tm["led_off_s"], color="C2", alpha=0.12)
    ax.text((tm["led_on_s"] + tm["split_s"]) / 2, 25, "phase 1 (15 LEDs)", ha="center", fontsize=11)
    ax.text((tm["split_s"] + tm["led_off_s"]) / 2, 25, "phase 2 (12 LEDs)", ha="center", fontsize=11)
    ax.set_xlim(t.min() - 5, t.max() + 5); ax.set_ylim(0, 27)
    ax.set_xlabel("time since start of run [s]"); ax.set_ylabel("detector that triggers")
    ax.set_yticks(range(1, 25, 2)); ax.legend(loc="lower left", fontsize=9)
    ax.set_title("One run (%s): LEDs on at %.0f s; phase 1: %d flashes, %.0f s pause, phase 2: %d flashes" %
                 (RUN, tm["led_on_s"], tm["n_flashes"]["phase1"], tm["pause_s"], tm["n_flashes"]["phase2"]))
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_run_timeline.png"), dpi=130); plt.close(fig)

    m = e["ev_phase"] == "phase1"
    ids = led_ids(tm["groups"])
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.hist(np.mod(t[m], 1.0) * 1e3, bins=2000, range=(0, 1000), color="C0")
    ax.set_yscale("log"); ax.set_xlabel("trigger time within its second [ms]"); ax.set_ylabel("triggers per 0.5 ms")
    # LED names: horizontal, on staggered heights where peaks are close, each joined to its peak by a thin line
    levels = [300, 800, 2100, 5500, 14000]
    last_x, lev = -1e9, -1
    for g in sorted((g for g in tm["groups"] if g["phase"] == "phase1"), key=lambda g: g["pos"]):
        lid = ids.get(("phase1", g["name"]))
        if not lid:
            continue
        x = g["pos"] * 1e3
        lev = lev + 1 if x - last_x < 70 else 0
        last_x = x
        y = levels[lev % len(levels)]
        ax.plot([x, x], [sum(g["n_triggers"].values()) * 1.1, y * 0.9], color="0.6", lw=0.6)
        ax.text(x, y, "%s LED%d" % lid, fontsize=8, ha="center", va="bottom")
    ax.set_ylim(0.8, 50000)
    ax.set_title("Phase 1 of the same run: each LED flashes at its own time within the second, so each LED is one peak")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_flash_groups.png"), dpi=130); plt.close(fig)

    # ---- stability maps: cell x series
    ser = sorted({r["series"] for r in rd("stability/trigger_fraction.csv")})
    st["n_series"] = len(ser); st["first"] = ser[0]; st["last"] = ser[-1]
    sp = rd("stability/stability_per_series.csv")
    med = defaultdict(list)
    for r in sp:
        med[(r["det"], r["channel"], r["led"])].append(float(r["amp_median"]))
    med = {k: np.median(v) for k, v in med.items()}
    rel = defaultdict(list)
    for r in sp:
        rel[(r["series"], r["det"], r["led"])].append(float(r["amp_median"]) / med[(r["det"], r["channel"], r["led"])])
    tf = {(r["series"], r["det"], r["led"]): int(r["n_triggers"]) / int(r["n_flashes"]) for r in rd("stability/trigger_fraction.csv")}
    amb = {(r["series"], r["led"]) for r in rd("summary/ambiguous_leds.csv")}     # LED not separable in that series
    lab = ["%s  %s<-%s LED%s" % (c["id"], c["det"], c["led"].split("#")[0], c["led"].split("#")[1]) for c in cells]
    Amap = np.full((len(cells), len(ser)), np.nan); Tmap = np.full((len(cells), len(ser)), np.nan)
    for i, c in enumerate(cells):
        for j, s in enumerate(ser):
            if (s, c["led"]) in amb:
                continue                              # grey: two LEDs in one flash group in this series
            v = rel.get((s, c["det"], c["led"]))
            if v:
                Amap[i, j] = np.median(v)
            Tmap[i, j] = tf.get((s, c["det"], c["led"]), 0.0)     # no trigger on that LED in this series = 0
    xt = [j for j in range(len(ser)) if j == 0 or series_time(ser[j]).date() != series_time(ser[j - 1]).date()]
    # runs of series with identical L1 trigger thresholds (trigger_settings.py)
    epochs = rd("summary/trigger_epochs.csv") if os.path.exists(os.path.join(OUT, "summary", "trigger_epochs.csv")) else []
    if not epochs:
        print("WARNING: out/summary/trigger_epochs.csv missing -- run trigger_settings.py; no epoch lines drawn")
    ep_x = [ser.index(e["first"]) - 0.5 for e in epochs[1:] if e["first"] in ser]
    sw_x = next((j for j, s in enumerate(ser) if series_time(s) >= datetime(2026, 9, 18, 22)), None)
    st["epochs"] = [dict(epoch=int(e["epoch"]), first=e["first"], last=e["last"], n_series=int(e["n_series"]), changed=e["changed"])
                    for e in epochs]
    for name, M, cmap, vmin, vmax, cl in (("fig_amp_map.png", Amap, "RdBu_r", 0.7, 1.3, "amplitude / its median over the series"),
                                          ("fig_trig_map.png", Tmap, "viridis", 0, 1, "fraction of the flashes it triggers on")):
        fig, ax = plt.subplots(figsize=(13, 9.5))
        cm = plt.get_cmap(cmap).copy(); cm.set_bad("0.85")
        im = ax.imshow(M, aspect="auto", cmap=cm, vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_yticks(range(len(cells))); ax.set_yticklabels(lab, fontsize=7)
        ax.set_xticks(xt); ax.set_xticklabels([series_time(ser[j]).strftime("%m-%d") for j in xt], fontsize=9)
        ax.set_xlabel("series, in time order (tick = first series of the day)")
        for x in ep_x:                                         # trigger thresholds changed here
            ax.axvline(x, color="k", lw=1.2)
        if sw_x is not None:                                   # 0913 -> 0918 sequencer script
            ax.axvline(sw_x - 0.5, color="r", lw=1.0, ls=":")
        ax.text(0.0, -0.085, "black lines: trigger thresholds changed;  red dotted: sequencer script changed",
                transform=ax.transAxes, fontsize=8, va="top")
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01, label=cl)
        ax.set_title(("Amplitude / its median" if "amp" in name else "Trigger fraction") +
                     ": one row per cell, one column per series (grey = no data)")
        fig.tight_layout(); fig.savefig(os.path.join(FIG, name), dpi=130); plt.close(fig)
    def pearson(x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        return float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 and x.std() > 0 and y.std() > 0 else float("nan")

    days = np.array([(series_time(s) - datetime(2026, 9, 15)).total_seconds() / 86400 for s in ser])
    st["cell_amp"] = {}
    for i, c in enumerate(cells):
        ok = np.isfinite(Amap[i])
        if ok.sum() >= 10:
            v = Amap[i][ok]
            st["cell_amp"][c["id"]] = dict(n=int(ok.sum()), min=round(float(v.min()), 2), max=round(float(v.max()), 2),
                                           std_pct=round(100 * float(v.std()), 1),
                                           slope_pct_per_day=round(100 * float(np.polyfit(days[ok], v, 1)[0]), 1),
                                           first_day=round(float(np.median(v[days[ok] < 1])), 2) if (days[ok] < 1).any() else None)
    sl = [v["slope_pct_per_day"] for v in st["cell_amp"].values() if v["n"] >= 30]
    st["slope_pct_per_day"] = dict(median=round(float(np.median(sl)), 1), min=min(sl), max=max(sl), n_cells=len(sl),
                                   n_negative=int(sum(x < 0 for x in sl)))
    # do two detectors that look at the same LED vary together? does one detector vary the same way with its two LEDs?
    row = {c["id"]: i for i, c in enumerate(cells)}
    same_led, same_det = [], []
    for a_ in cells:
        for b_ in cells:
            if a_["id"] >= b_["id"]:
                continue
            both = np.isfinite(Amap[row[a_["id"]]]) & np.isfinite(Amap[row[b_["id"]]])
            if both.sum() < 15:
                continue
            r = pearson(Amap[row[a_["id"]]][both], Amap[row[b_["id"]]][both])
            if (a_["phase"], a_["led"]) == (b_["phase"], b_["led"]):
                same_led.append(dict(led=a_["led"], a=a_["det"], b=b_["det"], ids=[a_["id"], b_["id"]], n=int(both.sum()), r=round(r, 2)))
            elif a_["det"] == b_["det"] and a_["own_led"] == "True" and b_["own_led"] == "True":
                same_det.append(dict(det=a_["det"], a=a_["led"], b=b_["led"], ids=[a_["id"], b_["id"]], n=int(both.sum()), r=round(r, 2)))
    st["same_led_corr"], st["same_det_corr"] = same_led, same_det
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw=dict(width_ratios=[1.25, 1.25, 1]))
    def series_plot(ax, pair, labels, title):
        for cid, lab_, col in zip(pair, labels, ("C0", "C3")):
            ok = np.isfinite(Amap[row[cid]])
            ax.plot([series_time(s) for s, k in zip(ser, ok) if k], Amap[row[cid]][ok], "o-", ms=3, lw=0.9, color=col, label=lab_)
        ax.axhline(1, color="k", lw=0.5); ax.set_ylim(0.8, 1.35); ax.grid(alpha=0.3); ax.legend(fontsize=8)
        ax.set_title(title, fontsize=10); ax.set_ylabel("amplitude / its median"); ax.tick_params(axis="x", labelrotation=30, labelsize=7)
    ex_led = next((p for p in same_led if p["led"] == "Z2#3"), same_led[0])
    ex_det = next((p for p in same_det if p["det"] == "Z1"), same_det[0])
    series_plot(axes[0], ex_led["ids"], ["detector %s" % ex_led["a"], "detector %s" % ex_led["b"]],
                "same LED (%s LED%s), two detectors: r = %.2f" % (tuple(ex_led["led"].split("#")) + (ex_led["r"],)))
    series_plot(axes[1], ex_det["ids"], ["LED%s" % ex_det["a"].split("#")[1], "LED%s" % ex_det["b"].split("#")[1]],
                "same detector (%s), its two LEDs: r = %.2f" % (ex_det["det"], ex_det["r"]))
    labs = ["%s LED%s: %s, %s" % (tuple(p["led"].split("#")) + (p["a"], p["b"])) for p in same_led] + \
           ["%s: LED%s, LED%s" % (p["det"], p["a"].split("#")[1], p["b"].split("#")[1]) for p in same_det]
    vals = [p["r"] for p in same_led] + [p["r"] for p in same_det]
    cols = ["C0"] * len(same_led) + ["C1"] * len(same_det)
    y = np.arange(len(vals))[::-1]
    axes[2].barh(y, vals, color=cols); axes[2].set_yticks(y); axes[2].set_yticklabels(labs, fontsize=6.5)
    axes[2].axvline(0, color="k", lw=0.5); axes[2].set_xlim(-0.7, 1.05); axes[2].set_xlabel("correlation over the series")
    axes[2].set_title("blue: one LED seen by two detectors\norange: one detector, its two LEDs", fontsize=9)
    fig.suptitle("Is it the LED or the detector? Same LED on two detectors, and one detector with its two LEDs", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(os.path.join(FIG, "fig_same_led.png"), dpi=130); plt.close(fig)

    # trigger fraction per threshold epoch
    ep_of = {}
    for e in epochs:
        for s in ser[ser.index(e["first"]):ser.index(e["last"]) + 1]:
            ep_of[s] = int(e["epoch"])
    st["trig_epoch"] = {}
    for i, c in enumerate(cells):
        per = []
        for e in epochs:
            v = [Tmap[i, j] for j, s in enumerate(ser) if ep_of.get(s) == int(e["epoch"]) and np.isfinite(Tmap[i, j])]
            per.append(dict(mean=round(float(np.mean(v)), 2), min=round(float(np.min(v)), 2), max=round(float(np.max(v)), 2)) if v else None)
        st["trig_epoch"][c["id"]] = per

    a = Amap[np.isfinite(Amap)]
    st["amp_cells_series"] = int(a.size)
    st["amp_within_5pct"] = round(100 * float(np.mean(np.abs(a - 1) < 0.05)), 1)
    st["amp_within_10pct"] = round(100 * float(np.mean(np.abs(a - 1) < 0.10)), 1)
    ss = [r for r in rd("stability/stability_summary.csv") if int(r["n_series"]) >= 30]
    st["chan_units"] = len(ss)
    st["chan_scatter_median_pct"] = round(100 * float(np.median([float(r["amp_rel_std"]) for r in ss])), 1)
    st["chan_scatter_below5_pct"] = round(100 * float(np.mean([float(r["amp_rel_std"]) < 0.05 for r in ss])), 1)
    st["trig_own_mean"] = {c["id"]: c["fraction"] for c in cells}
    dbl = [r for r in rd("stability/trigger_fraction.csv") if int(r["n_triggers"]) > int(r["n_flashes"])]
    st["double_trigger"] = [(r["series"], r["det"], r["led"], int(r["n_triggers"]), int(r["n_flashes"])) for r in dbl]
    fg = rd("summary/flash_groups.csv")
    st["n_groups"] = len(fg)
    st["retrigger"] = [(r["series"], r["group"], sum(json.loads(r["triggers"]).values())) for r in fg if r["kind"] == "re-trigger"]
    st["ambiguous"] = [(r["series"], r["phase"], r["group"]) for r in fg if r["kind"] == "ambiguous"]
    st["unidentified"] = [(r["series"], r["phase"], r["group"]) for r in fg if r["kind"] == "unidentified"]
    st["ambiguous_led_series"] = len(amb)
    vis = rd("summary/visibility.csv")
    offs = [(float(r["offset_us_min"]), float(r["offset_us_max"])) for r in vis if r["offset_us_min"] != "" and
            any(c["phase"] == r["phase"] and "%s LED%s" % tuple(c["led"].split("#")) == r["group"] and c["det"] == r["det"] for c in cells)]
    st["offset_us_range"] = [round(min(o[0] for o in offs)), round(max(o[1] for o in offs))]

    # ---- the cases worth a second look (detector median over channels)
    cases = [("Z20", "Z20#0"), ("Z19", "Z20#0"), ("Z1", "Z1#0"), ("Z13", "Z13#5"), ("Z16", "Z15#4"), ("Z19", "Z19#0")]
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.2), sharex=True); axes = axes.ravel()
    for ax, (d_, l_) in zip(axes, cases):
        pts = sorted((series_time(s), np.median(v)) for (s, dd, ll), v in rel.items() if (dd, ll) == (d_, l_))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", ms=3, lw=0.8)
        ax.axhline(1, color="k", lw=0.5); ax.axvline(datetime(2026, 9, 18, 22), color="r", ls=":", lw=0.8)
        for e in epochs[1:]:
            ax.axvline(series_time(e["first"]), color="k", lw=0.8, alpha=0.6)
        ax.set_ylim(0.2, 1.4); ax.grid(alpha=0.3)
        ax.set_title("detector %s <- %s LED %s" % (d_, l_.split("#")[0], l_.split("#")[1]), fontsize=10)
    fig.autofmt_xdate()
    fig.suptitle("Amplitude / its median for a few detectors (black lines: thresholds changed, red dotted: script changed)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(os.path.join(FIG, "fig_stab_cases.png"), dpi=130); plt.close(fig)
    z20 = sorted((s, round(float(np.median(v)), 2)) for (s, dd, ll), v in rel.items() if (dd, ll) == ("Z20", "Z20#0") and np.median(v) < 0.6)
    st["z20_low"] = z20
    st["z20_led3_low"] = sorted((s, round(float(np.median(v)), 2)) for (s, dd, ll), v in rel.items()
                                if (dd, ll) == ("Z20", "Z20#3") and s in {x[0] for x in z20})
    # before / after the 0913 -> 0918 switch: change of the cell median (cells with > 20 series on both sides)
    ba = []
    for c in cells:
        b4 = [np.median(v) for (s, dd, ll), v in rel.items() if (dd, ll) == (c["det"], c["led"]) and series_time(s) < datetime(2026, 9, 18, 22)]
        af = [np.median(v) for (s, dd, ll), v in rel.items() if (dd, ll) == (c["det"], c["led"]) and series_time(s) >= datetime(2026, 9, 18, 22)]
        if len(b4) > 20 and len(af) > 20:
            ba.append(float(np.median(af) - np.median(b4)))
    st["switch_change_pct"] = [round(100 * min(ba)), round(100 * max(ba)), len(ba)]
    z19 = sorted((s, round(float(np.median(v)), 2)) for (s, dd, ll), v in rel.items() if (dd, ll) == ("Z19", "Z20#0") and np.median(v) < 0.8)
    st["z19_low"] = z19

    # ---- which way does each LED shine: own detector, previous (number - 1), next (number + 1)
    from extract_led_events import SCRIPT_LEDS
    frac = {(c["phase"], c["led"], c["det"]): float(c["fraction"]) for c in cells}
    tab = []
    for ph in ("phase1", "phase2"):
        for z, n in sorted(SCRIPT_LEDS[ph].items(), key=lambda kv: int(kv[0][1:])):
            k = int(z[1:]); led = "%s#%d" % (z, n)
            tab.append(dict(phase=ph, led=led, number=n, own=frac.get((ph, led, z), 0.0),
                            prev=frac.get((ph, led, "Z%d" % (k - 1)), 0.0), next=frac.get((ph, led, "Z%d" % (k + 1)), 0.0),
                            first_in_tower=(k % 6 == 1), last_in_tower=(k % 6 == 0)))
    st["led_table"] = tab
    st["cells_not_adjacent"] = [c["id"] for c in cells if abs(int(c["det"][1:]) - int(c["led_owner"][1:])) > 1]
    st["cells_across_towers"] = [c["id"] for c in cells if (int(c["det"][1:]) - 1) // 6 != (int(c["led_owner"][1:]) - 1) // 6]
    tfr = rd("stability/trigger_fraction.csv")
    st["series_z9_z10"] = sorted({r["series"] for r in tfr if r["det"] in ("Z9", "Z10") and int(r["n_triggers"]) >= 20})

    # ---- templates
    tp = rd("lpfit/LED_cell_templates.csv")
    ch = [r for r in tp if r["channel"] != "detector"]
    st["n_cells"] = len(cells)
    st["n_cells_phase"] = {p: sum(c["phase"] == p for c in cells) for p in ("phase1", "phase2")}
    st["chan_templates"] = len(ch)
    st["chan_signal"] = sum(r["signal"] == "True" for r in ch)
    st["chan_spike"] = sum("spike" in r["flags"] for r in ch)
    st["det_templates"] = sum(r["channel"] == "detector" for r in tp)
    st["n_pulses_fit_ok"] = int(sum(int(r["n_pulses_fit_ok"]) for r in ch if r["n_pulses_fit_ok"]))
    det = [r for r in tp if r["channel"] == "detector"]
    st["det_table"] = [dict(id=r["id"], det=r["det"], led=r["led"], rise=r.get("tau_rise_us", ""), f1=r.get("tau_fall1_us", ""),
                            f2=r.get("tau_fall2_us", ""), rms=r.get("fit_rms", ""), model=r["model"]) for r in det]
    # LED drive pickup in the detector template: deviation before the start, or a large residual at the start
    import pickle
    d = pickle.load(open(os.path.join(OUT, "lpfit", "LED_cell_templates.pkl"), "rb"))
    x = (np.arange(12050, 32050) - 16050) / 625.0
    pick = []
    for (cid, chn), v in sorted(d["templates"].items()):
        if chn != "detector" or v.get("analytic") is None:
            continue
        m = v["mean"]
        pre = max(np.max(np.abs(m[(x > -0.3) & (x < -0.02)])), max(0.0, -np.min(m[(x > -0.02) & (x < 0.15)])))
        res = np.max(np.abs((m - v["analytic"])[(x > -0.3) & (x < 0.5)]))
        if pre > 0.08 or res > 0.25:
            c = d["cells"][cid]
            pick.append(dict(id=cid, det=c["det"], led=c["led"], own=c["own_led"], pre=round(float(pre), 3), res=round(float(res), 3)))
    st["pickup_cells"] = pick
    json.dump(st, open(os.path.join(HERE, "stats.json"), "w"), indent=1, default=str)
    print("figures in", FIG); print(json.dumps({k: v for k, v in st.items() if k not in ("det_table", "trig_own_mean")}, default=str)[:1500])


if __name__ == "__main__":
    if "--week" in sys.argv:          # only the week timeline and its numbers; the other figures stay as they are
        os.makedirs(FIG, exist_ok=True)
        f = os.path.join(HERE, "stats.json")
        st_ = json.load(open(f))
        st_["campaign"] = week_timeline()
        json.dump(st_, open(f, "w"), indent=1, default=str)
        print(st_["campaign"])
    else:
        main()
