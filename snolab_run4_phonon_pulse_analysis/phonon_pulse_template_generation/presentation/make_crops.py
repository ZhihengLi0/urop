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


def grid(src, out, row0, nrows, ncols, pad=6, min_row=140, col0=0):
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
    l = max(cols[col0][0] - pad, 0) if col0 else 0
    r = min(cols[col0 + ncols - 1][1] + pad, im.width)
    crop = im.crop((l, t, r, b))
    if row0 != 0:
        # stitch the channel-title strip on top so every crop keeps its labels
        titles = [bb for bb in rb if bb[1] - bb[0] <= 100 and bb[1] < panels[0][0]]
        if titles:
            tstrip = im.crop((l, max(titles[-1][0] - pad, 0),
                              r, titles[-1][1] + pad))
            combo = Image.new("RGB", (crop.width, tstrip.height + crop.height),
                              (255, 255, 255))
            combo.paste(tstrip, (0, 0))
            combo.paste(crop, (0, tstrip.height))
            crop = combo
    crop.save(os.path.join(OUT, out))
    print(f"{out}: rows {t}-{b}, x {l}-{r}  ({len(panels)} rows x {len(cols)} cols)")


# ---- stacked per-channel figures: panel 0 = PAS1, 1 = PBS1, 2 = PCS1, ...
# CAUTION (aligned_overlay only): its header text block is >120 px tall, so it
# survives the panel filter as block 0 — channel i sits at block i+1 there.
vpanel("aligned_overlay/zip7_lp_aligned_overlay.png", "aligned_overlay_zip7_PBS1.png", 2)
vpanel("aligned_overlay/zip7_lp_aligned_overlay.png", "aligned_overlay_zip7_PCS1.png", 3)

# zoom-only crops (right half of the row; the shadow bundle is clearest here)
def aligned_zoom(chan_block, out, xsplit=852):
    im = Image.open(os.path.join(PLOTS, "aligned_overlay/zip7_lp_aligned_overlay.png"))
    rb = [b for b in row_blocks(im) if b[1] - b[0] > 120]
    t, b = rb[chan_block]
    im.crop((xsplit, max(t - 4, 0), im.width, min(b + 6, im.height))).save(os.path.join(OUT, out))
    print(f"{out}: block {chan_block}, rows {t}-{b}")

aligned_zoom(3, "aligned_zoom_zip7_PCS1.png")   # PCS1: shadow bundle clearest
aligned_zoom(8, "aligned_zoom_zip7_PBS2.png")   # PBS2: shadow visible on the S2 face too
vpanel("nrmse/zip7_nrmse.png", "nrmse_zip7_PBS1.png", 1)
vpanel("nrmse/zip22_nrmse.png", "nrmse_zip22_PAS1.png", 0)

# annotate the NRMSE=0.4 cut with a red downward arrow in the valley.
# x_04 read off the log axis (decade ticks): see comments per file.
from PIL import ImageDraw as _ImageDraw, ImageFont as _ImageFont
def annotate_cut(fname, x_04):
    im = Image.open(os.path.join(OUT, fname)).convert("RGB")
    d = _ImageDraw.Draw(im)
    for _fp in ("/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            f = _ImageFont.truetype(_fp, 22)
            break
        except OSError:
            continue
    else:
        f = _ImageFont.load_default()
    H = im.height
    x = int(x_04)
    y_top, y_tip = int(H * 0.30), int(H * 0.82)
    d.line([(x, y_top), (x, y_tip)], fill=(210, 30, 30), width=4)
    d.polygon([(x, y_tip + 10), (x - 8, y_tip - 6), (x + 8, y_tip - 6)], fill=(210, 30, 30))
    d.text((x + 10, y_top - 4), "NRMSE = 0.4 cut", fill=(210, 30, 30), font=f)
    im.save(os.path.join(OUT, fname))
    print(f"{fname}: 0.4 arrow at x={x}")
annotate_cut("nrmse_zip7_PBS1.png", 462)   # 10^-1 at x≈308, decade≈255 px
annotate_cut("nrmse_zip22_PAS1.png", 243)  # 10^-1 at x≈155, decade≈146 px
vpanel("overlay_fan_cut/zip22_overlay_fan_cut_nrmse0.4.png", "fan_cut_zip22_PCS1.png", 2)
vpanel("overlay_fan_cut/zip7_overlay_fan_cut_nrmse0.4.png", "fan_cut_zip7_PBS1.png", 1)
vpanel("fitted_curves_overlay/zip22_fitted_curves_overlay_nrmse0.4_trise0.30ms.png",
       "fan_final_zip22_PCS1.png", 2)  # backup slide: Z22 after both cuts
# τ_rise-cut backup: good (PBS1, panel 1) vs bad (PDS2, panel 9) channel, before/after
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay_nrmse0.4.png", "fan_zip7_PDS2_nrmse.png", 9)
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay_nrmse0.4_trise0.30ms.png", "fan_zip7_PDS2_after.png", 9)
vpanel("time_constants/zip7_time_constants.png", "time_constants_zip7_PAS1.png", 0)
vpanel("time_constants/zip7_time_constants.png", "time_constants_zip7_PDS2.png", 9)  # zip7 has no PFS2: 11 panels, PDS2 = 9
# t_fall half of each strip (the right column of the rise|fall pair); PDS2 is
# the bad channel (broad tail), PAS1 a normal channel (narrow) — shown stacked
# for direct comparison on the slow-fall slide
def tfall_half(src, out):
    _im = Image.open(os.path.join(OUT, src))
    # rise|fall are a 1x2 subplot pair; keep the fall panel (right half),
    # then drop the centered title row (top) and the empty right of the 0-20 ms
    # axis (data lives in 0-8 ms) so the bars display large. Channel + median
    # are given in the slide caption instead.
    _fall = _im.crop((int(_im.width * 0.50), 0, _im.width, _im.height))
    _fall.crop((0, 30, int(_fall.width * 0.46), _fall.height)).save(
        os.path.join(OUT, out))
    print(f"{out}: t_fall panel, title trimmed, zoomed to ~0-7 ms")
tfall_half("time_constants_zip7_PDS2.png", "time_constants_zip7_PDS2_tfall.png")
tfall_half("time_constants_zip7_PAS1.png", "time_constants_zip7_PAS1_tfall.png")
vpanel("../../../deliverables/nxm/plots/zip7_pca_templates.png", "pca_zip7_PAS1.png", 0)
vpanel("../../../deliverables/nxm/plots/zip7_pca_templates.png", "pca_zip7_PBS1.png", 1)
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay.png", "fan_zip7_PBS1_before.png", 1)
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay_nrmse0.4.png",
       "fan_zip7_PBS1_nrmse.png", 1)
vpanel("fitted_curves_overlay/zip7_fitted_curves_overlay_nrmse0.4_trise0.30ms.png",
       "fan_zip7_PBS1_after.png", 1)
vpanel("pretrigger/zip7_pretrigger.png", "pretrigger_zip7_crop.png", 0)

# fan zooms for the algorithm slide: keep only the pulse region (left 47 %),
# drop the partial centered title row (top 26 px)
for _name in ["fan_zip7_PBS1_before", "fan_zip7_PBS1_nrmse"]:
    _f = Image.open(os.path.join(OUT, _name + ".png"))
    _f.crop((0, 26, int(_f.width * 0.47), _f.height)).save(
        os.path.join(OUT, _name + "_zoom.png"))
    print(f"{_name}_zoom.png: pulse-region zoom")

# ---- event x channel grids: few panels per crop so each panel stays legible
# fit_examples: first 3 channels; noise-trigger rows and K-line rows separately
grid("fit_examples/zip7_fit_examples.png", "fit_examples_zip7_noise.png", row0=0, nrows=2, ncols=3)
grid("fit_examples/zip7_fit_examples.png", "fit_examples_zip7_good.png", row0=2, nrows=2, ncols=3)
grid("slow_rise_events/zip22_slow_rise_events.png", "slow_rise_zip22_crop.png", row0=0, nrows=3, ncols=3)
grid("slow_rise_events/zip7_slow_rise_events.png", "slow_rise_zip7_crop.png", row0=0, nrows=3, ncols=3)
# τ_rise-cut backup: Z22 events that PASS NRMSE<=0.4 but are REMOVED by the
# τ_rise<=0.3ms cut (exact 0.3 threshold; made by scripts/plot_trise_removed_grid.py
# --det 22 --trise-min 3e-4), 3 events x first 4 channels
grid("trise_removed/zip22_trise_removed.png", "drift_zip22_crop.png", row0=0, nrows=3, ncols=4, min_row=100)
grid("shadow_events/zip7_shadow_events.png", "shadow_zip7_crop.png", row0=0, nrows=3, ncols=4, min_row=100)
# slow-fall follow-up: 3 sampled events x PBS2..PES2 (normal, normal, wild PDS2, normal);
# crop starts below the header row, so stamp the channel names back on
grid("slow_fall_events/zip7_PDS2_slow_fall.png", "slow_fall_zip7_crop.png",
     row0=2, nrows=3, ncols=4, col0=7)
from PIL import ImageDraw, ImageFont
_im = Image.open(os.path.join(OUT, "slow_fall_zip7_crop.png"))
_d = ImageDraw.Draw(_im)
for _fp in ("/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
    try:
        _f = ImageFont.truetype(_fp, 30)
        break
    except OSError:
        continue
else:
    _f = ImageFont.load_default()
_w = _im.width / 4
for _i, _c in enumerate(["PBS2", "PCS2", "PDS2", "PES2"]):
    _x = int(_i * _w + _w / 2 - 40)
    _d.rectangle([_x - 8, 4, _x + 105, 44], fill="#1F3864")
    _d.text((_x, 10), _c, font=_f, fill="white")
_im.save(os.path.join(OUT, "slow_fall_zip7_crop.png"))
print("slow_fall_zip7_crop.png: channel labels stamped")
# stamp channel labels on the K-line (good) fit-example crop, same channels
# as the noise block (PAS1/PBS1/PCS1); the source rows carry no header line
_im2 = Image.open(os.path.join(OUT, "fit_examples_zip7_good.png"))
_hdr = 16   # same header height/scale as the embedded titles on the noise crop
_pad = Image.new("RGB", (_im2.width, _im2.height + _hdr), (255, 255, 255))
_pad.paste(_im2, (0, _hdr))
_d2 = ImageDraw.Draw(_pad)
for _fp in ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
    try:
        _fsm = ImageFont.truetype(_fp, 13)
        break
    except OSError:
        continue
else:
    _fsm = ImageFont.load_default()
_w2 = _pad.width / 3
for _i, _c in enumerate(["PAS1", "PBS1", "PCS1"]):
    _x = int(_i * _w2 + _w2 / 2 - 16)
    _d2.text((_x, 1), _c, font=_fsm, fill="#262626")
_pad.save(os.path.join(OUT, "fit_examples_zip7_good.png"))
print("fit_examples_zip7_good.png: channel labels stamped")

