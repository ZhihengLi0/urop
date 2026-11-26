"""Summary of extract_led_events.py outputs: LED timing, who sees which LED, template shapes.

Reads out/<series>/{timing.json, events.npz, templates.pkl} for every series given (default:
all in out/) and writes into out/summary/:
  flash_groups.csv     per (series, phase, flash group): the LED(s) the script switches on that
                       trigger on it, every detector that triggers on it and how often, its
                       position in TriggerTime mod 1 s and its width
  visibility.csv       per (phase, flash group, detector): in how many series the detector
                       triggers on that group, and the mean fraction of the flashes it triggers on
  visibility_<phase>.png   detector x flash group matrix of that fraction
  shapes.csv           per (series, detector, phase, channel, source): pulses, 10-90 % rise,
                       1/e decay of the template, and its correlation with the same channel's
                       template from the other phase / other source in the same series
  templates_<series>.png   templates per detector, own LED vs neighbour's LED vs background
Limitation: one detector is read out per trigger, so a detector that sees a flash below its
own trigger threshold does not appear here.

Usage: python3 analyze_led.py [SERIES ...]
"""
import csv, glob, json, os, pickle, sys
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from extract_led_events import SCRIPT_LEDS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SR = 625000.0
DETS = ["Z%d" % d for d in range(1, 25) if d != 12]


def shape(tm, align):
    """10-90 % rise and peak -> 1/e decay (seconds) of a normalised template."""
    pk = int(np.argmax(tm))
    s = tm[max(pk - 2000, 0):pk + 1] / tm[pk]
    i10, i90 = np.where(s >= 0.1)[0], np.where(s >= 0.9)[0]
    rise = (i90[0] - i10[0]) / SR if len(i10) and len(i90) else np.nan
    after = np.where(tm[pk:] / tm[pk] <= np.exp(-1))[0]
    return rise, (after[0] / SR if len(after) else np.nan)


def corr(a, b, align):
    w = slice(align - 500, align + 8000)
    return float(np.corrcoef(a[w], b[w])[0, 1])


def canonical(g, lid):
    """Series-independent column name of a flash group: its LED ('Z1 LED4'), or, when no member detector
    points to any LED, '? seen only by <detectors>'."""
    if lid is not None:
        return "%s LED%d" % lid
    return "? seen only by " + "+".join(sorted(g["dets"], key=lambda z: int(z[1:])))


def name_order(n):
    """Sort LED names by the detector number; unidentified ('? seen only by ...') last."""
    import re
    m = re.search(r"Z(\d+)", n)
    return (n.startswith("?"), int(m.group(1)) if m else 99, n)


# A detector WITHOUT a switched-on LED that stands in for a neighbour's LED: when its 1 Hz peak is in a flash
# group, that LED is a candidate for the group. Needed for the LEDs whose own detector does not (always) trigger.
# True = the owner triggers in the same group in other series (same flash confirmed); False = the owner never
# triggers, inferred from the neighbour pattern.
LED_ALIAS = {("phase2", "Z2"): ("Z1", 4, True), ("phase2", "Z6"): ("Z5", 3, True),
             ("phase2", "Z14"): ("Z13", 5, True), ("phase2", "Z17"): ("Z18", 1, True),
             ("phase1", "Z16"): ("Z17", 0, True), ("phase2", "Z10"): ("Z9", 4, True),
             ("phase2", "Z21"): ("Z22", 0, False), ("phase1", "Z10"): ("Z11", 0, False)}


def _circ(x):
    return ((x + 0.5) % 1.0) - 0.5


def identify(groups):
    """Which LED each flash group of one series is. Returns
         ids   {(phase, group name): (owner detector, LED number) or None}
         kind  {(phase, group name): 'led' | 'ambiguous' | 're-trigger' | 'unidentified'}
         amb   {(phase, 'Z20 LED3'), ...}  LEDs that share a group with another LED: not separable in this series
    Candidates of a group: the LED of every member detector whose LED is on in this phase, and the LED a member
    stands in for (LED_ALIAS). An LED is REQUIRED in a group when this is its only candidate group, or when its
    own detector triggers in this group and in no other. One required LED -> the group is that LED (the other
    candidates only see its light and are dropped here); two or more -> two LEDs flash within the link tolerance,
    'ambiguous'. An LED left with several groups in which it is the only candidate: the one where its supporters
    trigger most, plus the others within 1 ms of it (same flash seen with a delay: Z16 up to 0.5 ms before Z17);
    groups further away are 're-trigger' peaks (Z1, 13 ms after its flash). No candidate -> 'unidentified'."""
    ids, kind, amb = {}, {}, set()
    for ph in ("phase1", "phase2"):
        G = [g for g in groups if g["phase"] == ph]
        cand = []
        for g in G:
            c = {}
            for z in g["dets"]:
                if z in g["leds"]:
                    c.setdefault((z, g["leds"][z]), []).append(z)
                elif (ph, z) in LED_ALIAS:
                    c.setdefault(LED_ALIAS[(ph, z)][:2], []).append(z)
            cand.append(c)
        where = defaultdict(list)
        for i, c in enumerate(cand):
            for led in c:
                where[led].append(i)
        member = defaultdict(list)                   # detector -> groups it has a peak in
        for i, g in enumerate(G):
            for z in g["dets"]:
                member[z].append(i)

        def score(i, led):
            return (G[i]["n_triggers"].get(led[0], 0), sum(G[i]["n_triggers"].get(z, 0) for z in cand[i].get(led, [])))

        dec, knd = {}, {}
        changed = True
        while changed:
            changed = False
            for i in range(len(G)):
                if i in dec:
                    continue
                if not cand[i]:
                    dec[i], knd[i] = None, "unidentified"; changed = True
                    continue
                req = [led for led in cand[i] if where[led] == [i] or member[led[0]] == [i]]
                if len(req) == 1:
                    dec[i], knd[i] = req[0], "led"
                elif len(req) > 1:
                    dec[i], knd[i] = None, "ambiguous"
                    amb.update((ph, "%s LED%d" % led) for led in req)
                elif len(cand[i]) == 1 and all(len(cand[k]) == 1 for k in where[next(iter(cand[i]))]):
                    led = next(iter(cand[i])); gi = list(where[led])
                    best = max(gi, key=lambda k: score(k, led))
                    for k in gi:
                        if k == best or abs(_circ(G[k]["pos"] - G[best]["pos"])) < 1e-3:
                            dec[k], knd[k] = led, "led"
                        else:
                            dec[k], knd[k] = None, "re-trigger"
                    changed = True
                    continue
                else:
                    continue
                for led in list(cand[i]):            # the non-required candidates are not this group
                    if led not in req:
                        del cand[i][led]; where[led].remove(i)
                changed = True
        for i, g in enumerate(G):
            if i not in dec:                         # candidates left, none required: cannot be decided
                dec[i], knd[i] = None, "ambiguous"
                amb.update((ph, "%s LED%d" % led) for led in cand[i])
            ids[(ph, g["name"])] = dec[i]; kind[(ph, g["name"])] = knd[i]
    return ids, kind, amb


def led_ids(groups):
    return identify(groups)[0]


def ambiguous_leds(groups, ids=None):
    return identify(groups)[2]


def n_flashes(g):
    return g.get("n_flashes", int(round(g["t_last"] - g["t_first"])) + 1)


def write_csv(path, rows):
    if rows:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main(series_list):
    sdir = os.path.join(OUT, "summary"); os.makedirs(sdir, exist_ok=True)
    grows, srows = [], []
    vis = defaultdict(list)            # (phase, group name) -> list of {det: fraction}
    used = []                          # series with LED flashes
    amb = {}                           # series -> LEDs not separable from another LED in that series
    offs = defaultdict(list)           # (phase, LED, detector) -> offset of its peak from the owner's peak, us
    for s in series_list:
        d = os.path.join(OUT, s)
        tm = json.load(open(os.path.join(d, "timing.json")))
        if not tm["groups"]:
            print("%s: %s -- skipped" % (s, tm.get("note", "no flash groups")))
            continue
        used.append(s)
        tp = pickle.load(open(os.path.join(d, "templates.pkl"), "rb"))
        A, T, N = tp["align_sample"], tp["templates"], tp["n_pulses"]
        print("%s: LEDs %.1f-%.1f s, split %.2f s (pause %.2f s), %d groups, no trigger on own LED: %s"
              % (s, tm["led_on_s"], tm["led_off_s"], tm["split_s"], tm["pause_s"], len(tm["groups"]), tm["missing_leds"]))
        ids, kind, amb[s] = identify(tm["groups"])
        for g in tm["groups"]:
            key = (g["phase"], g["name"]); lid = ids[key]
            label = {"led": canonical(g, lid) if lid else "", "unidentified": canonical(g, None),
                     "ambiguous": "ambiguous: " + "+".join(sorted(g["dets"], key=lambda z: int(z[1:]))),
                     "re-trigger": "re-trigger: " + "+".join(g["dets"])}[kind[key]]
            grows.append(dict(series=s, phase=g["phase"], group=label, kind=kind[key], leds=json.dumps(g["leds"]),
                              position_s="%.5f" % g["pos"], half_width_us=round(g["half_s"] * 1e6),
                              peaks=json.dumps([[z, round(p, 6), round(w * 1e6)] for z, p, w in g["peaks"]]),
                              triggers=json.dumps(g["n_triggers"]), n_flashes=n_flashes(g),
                              t_first=round(g["t_first"], 1), t_last=round(g["t_last"], 1)))
            if kind[key] in ("ambiguous", "re-trigger"):     # two LEDs not separable / not a flash: not counted
                continue
            vis[(g["phase"], label)].append(dict({z: n / max(n_flashes(g), 1) for z, n in g["n_triggers"].items()}, _series=s))
            if lid and any(z == lid[0] for z, _, _ in g["peaks"]):      # trigger-time offsets from the owner's peak
                po = [p for z, p, _ in g["peaks"] if z == lid[0]][0]
                for z, p, w in g["peaks"]:
                    if z != lid[0]:
                        offs[(g["phase"], label, z)].append(float(_circ(p - po)) * 1e6)

        # template shapes and comparisons
        by = defaultdict(dict)          # (det, ch) -> {(phase, source): template}
        for (det, ph, ch, src), t in T.items():
            by[(det, ch)][(ph, src)] = t
        for (det, ch), dd in sorted(by.items(), key=lambda x: (int(x[0][0][1:]), x[0][1])):
            for (ph, src), t in sorted(dd.items()):
                r, dec = shape(t, A)
                other = [(k, v) for k, v in dd.items() if k != (ph, src) and k[1] != "bg"]
                srows.append(dict(series=s, det=det, phase=ph, channel=ch,
                                  source=("own" if src.split("+").count(det) else src), n_pulses=N[(det, ph, ch, src)],
                                  rise_1090_us=round(r * 1e6, 1), decay_1e_us=round(dec * 1e6, 1),
                                  corr_with_others=";".join("%s/%s=%.3f" % (k[0], k[1], corr(t, v, A)) for k, v in other)))

        # one figure per series: per detector, the template of each LED source on one channel set
        dets = sorted({k[0] for k in T}, key=lambda z: int(z[1:]))
        fig, axes = plt.subplots(4, 6, figsize=(22, 13)); axes = axes.ravel()
        x = (np.arange(len(next(iter(T.values())))) - A) / SR * 1e3
        for ax, det in zip(axes, dets):
            for (dd_, ph, ch, src), t in T.items():
                if dd_ != det or src == "bg" or N[(dd_, ph, ch, src)] < 20:
                    continue
                own = det in src.split("+")
                ax.plot(x, t, lw=0.6, color=("C0" if ph == "phase1" else "C1"), ls=("-" if own else "--"), alpha=0.6)
            ax.set_xlim(-0.5, 4); ax.set_title(det, fontsize=9); ax.tick_params(labelsize=6)
        for ax in axes[len(dets):]:
            ax.axis("off")
        fig.suptitle("%s: templates per channel (blue phase 1, orange phase 2; solid own LED, dashed another LED); x in ms" % s)
        fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(sdir, "templates_%s.png" % s), dpi=90); plt.close(fig)

    write_csv(os.path.join(sdir, "flash_groups.csv"), grows)
    # LEDs that share a flash group with another LED (not separable), per series; header only when there is none
    with open(os.path.join(sdir, "ambiguous_leds.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["series", "phase", "led"])
        for s in used:
            for ph, n in sorted(amb[s]):
                w.writerow([s, ph, n.replace(" LED", "#")])
    write_csv(os.path.join(sdir, "shapes.csv"), srows)
    vrows, crows = [], []
    for ph in ("phase1", "phase2"):
        script = ["%s LED%d" % (z, n) for z, n in sorted(SCRIPT_LEDS[ph].items(), key=lambda kv: int(kv[0][1:]))]
        names = script + sorted({n for (p, n) in vis if p == ph} - set(script), key=name_order)
        M = np.zeros((len(DETS), len(names)))
        for j, n in enumerate(names):
            for i, z in enumerate(DETS):
                # every series counts (absent group = 0), except the series where this LED shares its group with
                # another LED (not separable)
                fr = [max([v.get(z, 0.0) for v in vis[(ph, n)] if v["_series"] == sr] or [0.0])
                      for sr in used if (ph, n) not in amb[sr]]
                M[i, j] = np.mean(fr) if fr else 0.0
                if any(fr):
                    o = offs.get((ph, n, z), [])
                    vrows.append(dict(phase=ph, group=n, det=z, series_seen=sum(1 for f in fr if f > 0),
                                      series=len(fr), mean_fraction=round(float(np.mean(fr)), 3),
                                      offset_us_median=round(float(np.median(o))) if o else "",
                                      offset_us_min=round(min(o)) if o else "", offset_us_max=round(max(o)) if o else ""))
        # every non-zero cell of a script LED gets an ID (P1-01 ...), column by column, used by the templates
        cell_id, k = {}, 0
        for j, n in enumerate(names):
            if n not in script:
                continue
            for i, z in enumerate(DETS):
                if M[i, j] >= 0.05:
                    k += 1
                    cell_id[(j, i)] = "P%s-%02d" % (ph[-1], k)
                    own, num = n.split()
                    nser = sum(1 for sr in used if any(v.get(z, 0.0) > 0 for v in vis[(ph, n)] if v["_series"] == sr))
                    nsep = sum(1 for sr in used if (ph, n) not in amb[sr])
                    crows.append(dict(id=cell_id[(j, i)], phase=ph, led_owner=own, led_number=int(num[3:]),
                                      led="%s#%s" % (own, num[3:]), det=z, fraction=round(float(M[i, j]), 3),
                                      series_seen=nser, series_separable=nsep, own_led=(own == z)))
        fig, ax = plt.subplots(figsize=(4 + 0.7 * len(names), 12.5))
        im = ax.imshow(M, cmap="viridis", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=90, fontsize=8)
        ax.set_yticks(range(len(DETS))); ax.set_yticklabels(DETS, fontsize=8)
        for i in range(len(DETS)):
            for j in range(len(names)):
                if M[i, j] >= 0.05:
                    cid = cell_id.get((j, i), "")
                    ax.text(j, i, "%.2f\n%s" % (M[i, j], cid), ha="center", va="center", fontsize=6.5,
                            color=("k" if M[i, j] > 0.6 else "w"), linespacing=1.1)
        for j, n in enumerate(names):                  # red box: the detector the LED belongs to
            if not n.startswith("?") and n.split()[0] in DETS:
                i = DETS.index(n.split()[0])
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="r", lw=1.5))
        ax.set_xlabel("LED switched on in %s by the sequencer script (detector + LED number)" % ph, fontsize=9)
        ax.set_ylabel("detector that triggers", fontsize=9)
        fig.colorbar(im, label="fraction of the flashes on which the detector triggers")
        ax.set_title("%s (%s): who triggers on which LED, mean of %d series"
                     % (ph, "first 151 s of LED flashing" if ph == "phase1" else "151 s after the 3 s pause", len(used)))
        namb = sum(1 for sr in used for (p, _) in amb[sr] if p == ph)
        fig.text(0.01, 0.005,
                 "How to read: each column is one LED that flashes at 1 Hz (151 flashes per series); each row is a detector.\n"
                 "Number = fraction of that LED's flashes on which this detector triggered, averaged over the series "
                 "(1.00 = every flash, 0.50 = half; no number = < 0.05).\n"
                 "P%s-01 ... = ID of a non-zero cell; each has its own pulse template (out/lpfit/cell_<ID>.png).\n"
                 "Red box = the LED's own detector. A number in another row = a neighbouring detector also triggers on that LED.\n"
                 "Empty red box = that LED never makes its own detector trigger. A series in which two LEDs flash within 0.2 ms of each\n"
                 "other is left out for those two LEDs (%d LED-series in this phase).\n"
                 "Only one detector is read out per trigger, so a detector that sees the light below its own trigger threshold does not appear."
                 % (ph[-1], namb), fontsize=8, va="bottom", family="monospace")
        fig.tight_layout(rect=(0, 0.1, 1, 1)); fig.savefig(os.path.join(sdir, "visibility_%s.png" % ph), dpi=110); plt.close(fig)
    write_csv(os.path.join(sdir, "visibility.csv"), vrows)
    write_csv(os.path.join(sdir, "cells.csv"), crows)
    print("wrote %s" % sdir)


if __name__ == "__main__":
    args = sys.argv[1:] or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(OUT, "*", "timing.json")))
    main(args)
