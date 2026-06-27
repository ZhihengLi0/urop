#!/usr/bin/env python3
"""
Assemble per-event debug PNGs + summary PNG into a single multi-page PDF.
Page 1: summary overlay plot (all fitted traces).
Page 2+: per-event debug plots, failures first then successes.
"""

import os
import glob
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.image import imread

def main():
    run_dir   = os.environ.get("ZIP19PAS1_RUN_DIR", os.path.abspath("Zip19PAS1/run"))
    debug_dir = os.path.join(run_dir, "debug_plots")
    plot_dir  = os.path.join(run_dir, "plots")
    out_pdf   = os.path.join(run_dir, "debug_all_events.pdf")

    # summary plot
    summary_png = os.path.join(
        plot_dir,
        "zip19_pas1_24260619_230219_first200_all_2exp_fitted_normalized.png",
    )

    # per-event PNGs — failures first, then successes, sorted by event number within each group
    def sort_key(path):
        name = os.path.basename(path)
        evn  = int(re.search(r"ev(\d+)", name).group(1))
        is_ok = 1 if "_ok.png" in name else 0
        return (is_ok, evn)

    per_event = sorted(glob.glob(os.path.join(debug_dir, "ev*.png")), key=sort_key)

    if not per_event:
        raise RuntimeError(f"No per-event PNGs found in {debug_dir}")

    n_fail = sum(1 for p in per_event if "_fail.png" in p)
    n_ok   = sum(1 for p in per_event if "_ok.png" in p)
    print(f"Found {len(per_event)} debug plots ({n_fail} fail, {n_ok} ok)")

    pages = []
    if os.path.exists(summary_png):
        pages.append(("Summary: all fitted traces", summary_png))
    else:
        print(f"Warning: summary PNG not found at {summary_png}")

    for path in per_event:
        label = os.path.basename(path).replace(".png", "")
        pages.append((label, path))

    print(f"Building PDF with {len(pages)} pages ...")
    with PdfPages(out_pdf) as pdf:
        for label, path in pages:
            img = imread(path)
            h, w = img.shape[:2]
            fig_w = 14.0
            fig_h = fig_w * h / w
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            ax.imshow(img)
            ax.axis("off")
            fig.tight_layout(pad=0)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    print(f"Saved: {out_pdf}  ({len(pages)} pages)")


if __name__ == "__main__":
    main()
