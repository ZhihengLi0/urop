"""L1 trigger settings of every analysed series, from the begin-of-run ODB dump.

The trigger fraction of a detector on an LED changes in steps between series; the steps follow the L1
trigger thresholds, which were changed between groups of runs. This script reads, per series, the
/Detectors ODB tree once (first MIDAS file) and writes

  out/summary/trigger_settings.csv   series, det, dcrc, activation_threshold (ActivationThreshold[0] of
                                     Settings/L1Trigger), enabled (TriggerLogic Enable[0])
  out/summary/trigger_epochs.csv     consecutive series with identical thresholds on all detectors:
                                     epoch, first series, last series, number of series, what changed

Usage: python3 trigger_settings.py
"""
import csv, glob, os, re
from collections import defaultdict
from rawio.IO import RawDataReader
from analyze_led import OUT
from extract_led_events import RAW


def read_series(s):
    f = sorted(glob.glob("%s/%s/*.mid.lz4" % (RAW, s)))[0]
    o = RawDataReader(filepath=f, verbose=False).get_full_odb(odb_dir="/Detectors")
    rows = {}
    for k, v in o.items():
        m = re.match(r"/Detectors/Det(\d+)/Settings/L1Trigger/(DCRC\d)/(ActivationThreshold|TriggerLogic Enable)$", k)
        if m:
            d = rows.setdefault(("Z%d" % int(m.group(1)), m.group(2)), {})
            d["activation_threshold" if m.group(3).startswith("Act") else "enabled"] = v[0]
    return rows


def main():
    series = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(OUT, "2426*", "timing.json")))
    out, sett = [], {}
    for s in series:
        r = read_series(s)
        sett[s] = {k: (v.get("activation_threshold"), v.get("enabled")) for k, v in r.items()}
        for (det, dcrc), v in sorted(r.items(), key=lambda kv: (int(kv[0][0][1:]), kv[0][1])):
            out.append(dict(series=s, det=det, dcrc=dcrc, activation_threshold=v.get("activation_threshold"),
                            enabled=v.get("enabled")))
        print(s, len(r), "detector/DCRC", flush=True)
    sdir = os.path.join(OUT, "summary")
    with open(os.path.join(sdir, "trigger_settings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    # epochs: runs of consecutive series with identical settings
    epochs, prev = [], None
    for s in series:
        if prev is None or sett[s] != sett[prev]:
            changed = defaultdict(list)
            if prev is not None:
                for k in sorted(set(sett[s]) | set(sett[prev]), key=lambda k: (int(k[0][1:]), k[1])):
                    if sett[s].get(k) != sett[prev].get(k):
                        a, b = sett[prev].get(k, (None, None)), sett[s].get(k, (None, None))
                        changed[k[0]].append("%s %s->%s%s" % (k[1], a[0], b[0], "" if a[1] == b[1] else " enable %s->%s" % (a[1], b[1])))
            epochs.append(dict(epoch=len(epochs) + 1, first=s, last=s, n_series=0,
                               changed="; ".join("%s %s" % (z, ", ".join(v)) for z, v in changed.items())))
        epochs[-1]["last"] = s; epochs[-1]["n_series"] += 1
        prev = s
    with open(os.path.join(sdir, "trigger_epochs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(epochs[0])); w.writeheader(); w.writerows(epochs)
    for e in epochs:
        print("epoch %d: %s .. %s (%d series)  %s" % (e["epoch"], e["first"], e["last"], e["n_series"], e["changed"][:200]))


if __name__ == "__main__":
    main()
