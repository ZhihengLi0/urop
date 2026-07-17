#!/usr/bin/env python3
"""How many events does the t_rise <= 0.3 ms ceiling remove, relative to the
previous step (fit_ok + NRMSE <= 0.4)?

Reads the per-series fit checkpoints (run/checkpoints/zip{N}/{series}_fit.pkl)
and prints, per zip (all channels pooled) and per channel for one zip, the
event counts after the NRMSE cut, after the additional rise-time ceiling, and
the removed fraction.

Result (2026-07-17, all 13 zips): quiet detectors lose almost nothing
(Z7 1.6% — mostly the bad channel PDS2 at 21%, every other channel <= 0.4%;
Z9 4.7%; Z16 5.9%), weak detectors lose 55-74% (Z24 74%, Z4/Z22/Z18 ~71%,
Z19 68%, Z6 56%); pooled over all zips 54%. What the ceiling removes is
residual slow baseline drift that survived the NRMSE cut.

Needs Python >= 3.8 (checkpoints are pickle protocol 5).
"""
import argparse
import os
import pickle

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CKPT_DIR_DEFAULT = os.path.join(BASE_DIR, "run", "checkpoints")
ZIPS = [1, 4, 6, 7, 9, 10, 13, 15, 16, 18, 19, 22, 24]
ALL_CHANS = ["PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
             "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2"]

parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("--ckpt-dir", default=CKPT_DIR_DEFAULT)
parser.add_argument("--nrmse-max", type=float, default=0.4)
parser.add_argument("--trise-max-ms", type=float, default=0.3)
parser.add_argument("--per-channel-det", type=int, default=7,
                    help="zip whose per-channel breakdown is printed")
args = parser.parse_args()
trise_max = args.trise_max_ms * 1e-3

print(f"{'zip':>4} {'after NRMSE':>12} {'after t_rise':>13} "
      f"{'removed':>8} {'removed %':>9}")
tot1 = tot2 = 0
detail_chan = {}
for det in ZIPS:
    d = os.path.join(args.ckpt_dir, f"zip{det}")
    if not os.path.isdir(d):
        print(f"{det:>4}  (no checkpoints at {d})")
        continue
    n1 = n2 = 0
    chan_counts = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith("_fit.pkl"):
            continue
        with open(os.path.join(d, f), "rb") as fh:
            fits = pickle.load(fh)["fits"]
        for c, lst in fits.items():
            for fp in (lst or []):
                if fp is None or not fp["fit_ok"] or fp["nrmse"] > args.nrmse_max:
                    continue
                a, b = chan_counts.get(c, (0, 0))
                passed = fp["t_rise"] <= trise_max
                chan_counts[c] = (a + 1, b + (1 if passed else 0))
                n1 += 1
                n2 += 1 if passed else 0
    rm = n1 - n2
    print(f"{det:>4} {n1:>12} {n2:>13} {rm:>8} {100 * rm / max(n1, 1):>8.1f}%")
    tot1 += n1
    tot2 += n2
    if det == args.per_channel_det:
        detail_chan = chan_counts

rm = tot1 - tot2
print(f"{'ALL':>4} {tot1:>12} {tot2:>13} {rm:>8} {100 * rm / max(tot1, 1):>8.1f}%")

if detail_chan:
    print(f"\nZ{args.per_channel_det} per channel:")
    print(f"{'chan':>6} {'after NRMSE':>12} {'after t_rise':>13} {'removed %':>9}")
    for c in ALL_CHANS:
        if c not in detail_chan:
            continue
        a, b = detail_chan[c]
        print(f"{c:>6} {a:>12} {b:>13} {100 * (a - b) / max(a, 1):>8.1f}%")
