"""Consistency checks of the R7 LED products (run in the V07-02 container after the pipeline).

Prints one line per check, PASS / FAIL / INFO, and exits with status 1 if any check fails.
  timing     every series: 3 s pause, 151 flashes in both phases, no group with more triggers than flashes,
             unique group names, labels in events.npz identical to a fresh led_timing() of the stored times
  reading    events skipped at reading (ReadoutType != 8, not exactly one detector)
  groups     kinds of flash groups; ambiguous / re-trigger / unidentified listed
  cells      trigger-time offset of every neighbour cell from the LED owner's peak (same flash: within +-0.3 ms)
  polarity   channels whose pulses are negative (the Z7 template chain assumes positive pulses)
  lpfit      cell IDs of every lpfit.pkl match cells.csv; events per cell equal to events.npz; all cells have figures

Usage: python3 qa_led.py
"""
import csv, glob, json, os, pickle, sys
from collections import Counter, defaultdict
import numpy as np
from analyze_led import OUT, identify
from extract_led_events import led_timing, TAGS

FAIL = []


def check(ok, name, detail=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + str(detail)) if detail else ""), flush=True)
    if not ok:
        FAIL.append(name)


def info(name, detail):
    print("INFO  %s  -- %s" % (name, detail), flush=True)


def main():
    series = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(OUT, "2426*", "timing.json")))
    info("series", len(series))
    cells = list(csv.DictReader(open(os.path.join(OUT, "summary", "cells.csv"))))
    cellkey = {(c["phase"], c["led"], c["det"]): c["id"] for c in cells}

    pauses, nfl, over, dup, relabel, skipped, kinds, lists = [], Counter(), [], [], [], Counter(), Counter(), defaultdict(list)
    neg = Counter(); npulse = Counter(); per_cell = {}
    for s in series:
        d = os.path.join(OUT, s)
        tm = json.load(open(os.path.join(d, "timing.json")))
        e = np.load(os.path.join(d, "events.npz"))
        pauses.append(tm["pause_s"])
        for ph in ("phase1", "phase2"):
            nfl[tm["n_flashes"][ph]] += 1
        names = [(g["phase"], g["name"]) for g in tm["groups"]]
        if len(names) != len(set(names)):
            dup.append(s)
        for g in tm["groups"]:
            if max(g["n_triggers"].values()) > g["n_flashes"]:
                over.append((s, g["phase"], g["name"], g["n_triggers"]))
        tm2, ph2, src2 = led_timing(s, e["ev_time"], e["ev_det"])
        if not (np.array_equal(ph2, e["ev_phase"]) and np.array_equal(src2, e["ev_source"])
                and [g["name"] for g in tm2["groups"]] == [g["name"] for g in tm["groups"]]):
            relabel.append(s)
        for k, v in tm.get("events_read", {}).items():
            skipped[k] += v
        ids, kind, amb = identify(tm["groups"])
        for g in tm["groups"]:
            k = kind[(g["phase"], g["name"])]
            kinds[k] += 1
            if k != "led":
                lists[k].append("%s %s %s" % (s[-11:], g["phase"], g["n_triggers"]))
        # events per cell, polarity of the pulses
        cnt = Counter()
        for ph, src, det in zip(e["ev_phase"], e["ev_source"], e["ev_det"]):
            lid = ids.get((str(ph), str(src)))
            if lid:
                c = cellkey.get((str(ph), "%s#%d" % lid, "Z%d" % det))
                if c:
                    cnt[c] += 1
        per_cell[s] = cnt
        pulse = np.isin(e["ch_tag"], [TAGS.index(t) for t in ("good", "glitch", "bipolar")])
        dch = np.char.add(np.char.add(np.char.mod("Z%d ", e["ev_det"][e["ch_ev"]]), ""), e["ch_chan"])
        for k, n in zip(*np.unique(dch[pulse], return_counts=True)):
            npulse[k] += n
        for k, n in zip(*np.unique(dch[pulse & (e["ch_pol"] < 0)], return_counts=True)):
            neg[k] += n

    check(min(pauses) > 2.9 and max(pauses) < 3.4, "pause between the phases 2.9-3.4 s", "%.2f-%.2f s" % (min(pauses), max(pauses)))
    check(set(nfl) == {151}, "151 flashes in every phase of every series", dict(nfl))
    check(not over, "no detector triggers more often than the LED flashes", over[:5])
    check(not dup, "group names unique per phase", dup)
    check(not relabel, "events.npz labels = led_timing() of the stored trigger times", relabel)
    info("events read (sum over series)", dict(skipped))
    info("flash groups", dict(kinds))
    for k, v in lists.items():
        info("%s groups (%d)" % (k, len(v)), "; ".join(v[:30]))
    check(kinds["unidentified"] == 0, "every flash group points to an LED")

    vis = list(csv.DictReader(open(os.path.join(OUT, "summary", "visibility.csv"))))
    bad = []
    for r in vis:
        led = r["group"].replace(" LED", "#")
        if (r["phase"], led, r["det"]) in cellkey and r["offset_us_min"] != "":
            if float(r["offset_us_min"]) < -300 or float(r["offset_us_max"]) > 300:
                bad.append((cellkey[(r["phase"], led, r["det"])], r["offset_us_min"], r["offset_us_max"]))
    check(not bad, "neighbour cells trigger within +-0.3 ms of the LED owner's detector", bad)
    nonadj = [c["id"] for c in cells if abs(int(c["det"][1:]) - int(c["led_owner"][1:])) > 1]
    info("cells", "%d (%d own LED, %d neighbour); not adjacent: %s" % (len(cells), sum(c["own_led"] == "True" for c in cells),
                                                                      sum(c["own_led"] == "False" for c in cells), nonadj or "none"))

    negch = {k: "%d/%d" % (neg[k], npulse[k]) for k in neg if neg[k] > 0.2 * npulse[k] and npulse[k] > 100}
    info("channels with mostly negative pulses (pickup transients; excluded from amplitudes and templates)", negch or "none")

    files = sorted(glob.glob(os.path.join(OUT, "2426*", "lpfit.pkl")))
    if not files:
        info("lpfit", "no lpfit.pkl yet")
    else:
        bad_id, bad_n, miss = [], [], [s for s in series if not os.path.exists(os.path.join(OUT, s, "lpfit.pkl"))]
        for f in files:
            d = pickle.load(open(f, "rb")); s = d["series"]
            for cid, k in d.get("cell_keys", {}).items():
                if cellkey.get(tuple(k)) != cid:
                    bad_id.append((s, cid)); break
            got = {c: len(v) for c, v in d["events"].items()}
            if got != dict(per_cell[s]):
                bad_n.append(s)
        check(not miss, "lpfit.pkl for every series", miss)
        check(not bad_id, "cell IDs of lpfit.pkl = cells.csv", bad_id[:5])
        check(not bad_n, "events per cell in lpfit.pkl = events.npz", bad_n)
        figs = [c["id"] for c in cells if not os.path.exists(os.path.join(OUT, "lpfit", "cell_%s.png" % c["id"]))]
        check(not figs, "a template figure for every cell", figs)
        tp = list(csv.DictReader(open(os.path.join(OUT, "lpfit", "LED_cell_templates.csv"))))
        far = ["%s %s %s" % (r["id"], r["channel"], r["start_far_fraction"]) for r in tp
               if r["channel"] != "detector" and r["signal"] == "True" and float(r["start_far_fraction"]) > 0.2]
        check(not far, "signal channels: fitted pulse start within 0.48 ms of the expected start for > 80 % of the pulses", far[:20])
        stale = [os.path.basename(p) for p in glob.glob(os.path.join(OUT, "lpfit", "cell_*.png"))
                 if os.path.basename(p)[5:-4] not in {c["id"] for c in cells}]
        check(not stale, "no template figure of a cell that no longer exists", stale)
    print("\n%s" % ("ALL CHECKS PASSED" if not FAIL else "FAILED: " + "; ".join(FAIL)))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
