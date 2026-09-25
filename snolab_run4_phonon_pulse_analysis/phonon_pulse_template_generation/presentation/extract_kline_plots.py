#!/usr/bin/env python3
"""Extract the per-detector 'Summed PTOFamps, Rejecting ΣPF/PT' plots (the ones
with the red 10.37 keV K-line marker) from the Ge Activation ops PDF, label
them 'Zip N', and compose the 13-zip montage used on slide 2.

Detector attribution: each red-line plot is the first image after its 'ZN'
section caption in reading order (verified for all 13).
"""
import fitz
from PIL import Image, ImageDraw, ImageFont
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "..",
    "Ge Activation Data - Ops Shift 2_3114372f63d84582a99a75e4f45c5d0b-240626-1548-790.pdf")
OUT = os.path.join(HERE, "figures")

# (zip, page 1-based, xref of the red-line plot) — see attribution note above
PLOTS = [
    (1, 2, 10), (4, 3, 18), (6, 4, 26), (7, 6, 36), (9, 7, 44),
    (10, 9, 54), (13, 10, 62), (15, 12, 73), (16, 14, 84), (18, 15, 93),
    (19, 17, 104), (22, 18, 112), (24, 20, 123),
]
LEGEND_X = 972   # legend starts here in the 1436-wide originals; cropped off

doc = fitz.open(PDF)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 54)

panels = []
for z, page, xref in PLOTS:
    pix = fitz.Pixmap(doc, xref)
    if pix.n > 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    im = im.crop((0, 0, LEGEND_X, im.height))
    d = ImageDraw.Draw(im)
    d.rectangle([16, 10, 210, 78], fill="#1F3864")
    d.text((36, 18), f"Zip {z}", font=font, fill="white")
    im.save(os.path.join(OUT, f"kline_zip{z}.png"))
    panels.append(im)
    print(f"zip{z}: {im.size}")

# 5 x 3 montage, order as in PLOTS
cols, gap, bg = 5, 24, "white"
W, H = panels[0].size
rows = (len(panels) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W + (cols - 1) * gap,
                          rows * H + (rows - 1) * gap), bg)
for i, im in enumerate(panels):
    sheet.paste(im, ((i % cols) * (W + gap), (i // cols) * (H + gap)))
sheet.save(os.path.join(OUT, "kline_all_zips.png"))
print("montage:", sheet.size)
