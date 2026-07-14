#!/usr/bin/env python3
"""Crop slide-friendly panels out of the tall multi-channel diagnostic figures.

Panels are located automatically: rows/columns whose pixels are all near-white
separate the panels, so every crop carries its complete title and axes and no
fragments of neighbouring panels.
"""
from PIL import Image
import numpy as np
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PLOTS = os.path.join(HERE, "..", "lp_fit_align", "results", "plots")
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)


def blocks(mask, min_gap):
    """Split boolean 'content' mask (1-D) into blocks separated by >=min_gap blanks."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    out, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev >= min_gap:
            out.append((start, prev))
            start = i
        prev = i
    out.append((start, prev))
    return out


def row_blocks(img, min_gap=12, thresh=248):
    a = np.asarray(img.convert("L"))
    return blocks((a < thresh).any(axis=1), min_gap)


def col_blocks(img, min_gap=12, thresh=248):
    a = np.asarray(img.convert("L"))
    return blocks((a < thresh).any(axis=0), min_gap)


def vpanel(src, out, index, span=1, pad=6, skip_header=True):
    """Crop the index-th vertical panel (0-based, after dropping the header
    text block + figure title block) of a stacked figure; span>1 merges
    consecutive panels."""
    im = Image.open(os.path.join(PLOTS, src))
    rb = row_blocks(im)
    # the first blocks are the processing-chain stamp lines + centered title;
    # real panels are the tall blocks (> 120 px)
    panels = [b for b in rb if b[1] - b[0] > 120] if skip_header else rb
    t = max(panels[index][0] - pad, 0)
    b = min(panels[index + span - 1][1] + pad, im.height)
    im.crop((0, t, im.width, b)).save(os.path.join(OUT, out))
    print(f"{out}: rows {t}-{b} of {im.height}  ({len(panels)} panels found)")


def grid(src, out, row0, nrows, ncols, pad=6, min_row=140):
    """Crop rows [row0, row0+nrows) x first ncols columns of an event grid.
    Row/column boundaries come from blank-gap detection; columns are detected
    inside the selected rows only, so full-width header text cannot mask the
    inter-column gaps."""
    im = Image.open(os.path.join(PLOTS, src))
    rb = row_blocks(im, min_gap=10)
    # event rows are tall blocks; the header stamp always touches the top edge
    panels = [b for b in rb if b[1] - b[0] > min_row and b[0] > 40]
    t = max(panels[row0][0] - pad, 0)
    if row0 == 0:  # keep the thin channel-title line right above row 0
        titles = [b for b in rb if b[1] - b[0] <= 100 and b[1] < panels[0][0]]
        if titles:
            t = max(titles[-1][0] - pad, 0)
    b = min(panels[row0 + nrows - 1][1] + pad, im.height)
    strip = im.crop((0, panels[row0][0], im.width, panels[row0 + nrows - 1][1]))
    cols = [c for c in col_blocks(strip, min_gap=6) if c[1] - c[0] > 80]
    r = min(cols[ncols - 1][1] + pad, im.width)
    im.crop((0, t, r, b)).save(os.path.join(OUT, out))
    print(f"{out}: rows {t}-{b}, x 0-{r}  ({len(panels)} rows x {len(cols)} cols)")


# ---- stacked per-channel figures: panel 0 = PAS1, 1 = PBS1, 2 = PCS1, ...
vpanel("aligned_overlay/zip7_lp_aligned_overlay.png", "aligned_overlay_zip7_PBS1.png", 1)
vpanel("aligned_overlay/zip7_lp_aligned_overlay.png", "aligned_overlay_zip7_PCS1.png", 2)
vpanel("nrmse/zip7_nrmse.png", "nrmse_zip7_PBS1.png", 1)
vpanel("nrmse/zip22_nrmse.png", "nrmse_zip22_PAS1.png", 0)
vpanel("overlay_fan_cut/zip22_overlay_fan_cut_nrmse0.4.png", "fan_cut_zip22_PCS1.png", 2)
vpanel("time_constants/zip7_time_constants.png", "time_constants_zip7_PAS1.png", 0)
vpanel("time_constants/zip7_time_constants.png", "time_constants_zip7_PDS2.png", 9)  # zip7 has no PFS2: 11 panels, PDS2 = 9
vpanel("pca_templates/zip7_pca_templates.png", "pca_zip7_PAS1.png", 0)
vpanel("pca_templates/zip7_pca_templates.png", "pca_zip7_PBS1.png", 1)
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay.png", "fan_zip7_PBS1_before.png", 1)
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay_nrmse0.4.png",
       "fan_zip7_PBS1_nrmse.png", 1)
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay_nrmse0.4_trise0.30ms.png",
       "fan_zip7_PBS1_after.png", 1)
vpanel("pretrigger/zip7_pretrigger.png", "pretrigger_zip7_crop.png", 0)

# ---- event x channel grids: few panels per crop so each panel stays legible
# fit_examples: first 3 channels; noise-trigger rows and K-line rows separately
grid("fit_examples/zip7_fit_examples.png", "fit_examples_zip7_noise.png", row0=0, nrows=2, ncols=3)
grid("fit_examples/zip7_fit_examples.png", "fit_examples_zip7_good.png", row0=2, nrows=2, ncols=3)
grid("slow_rise_events/zip22_slow_rise_events.png", "slow_rise_zip22_crop.png", row0=0, nrows=3, ncols=3)
grid("shadow_events/zip7_shadow_events.png", "shadow_zip7_crop.png", row0=0, nrows=3, ncols=4, min_row=100)
