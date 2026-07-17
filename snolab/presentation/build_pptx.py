#!/usr/bin/env python3
"""Build the 10-min SNOLAB R4 template-project slide deck (16:9, English)."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "SNOLAB_R4_pulse_templates_20260715.pptx")

NAVY = RGBColor(0x1F, 0x38, 0x64)
DARK = RGBColor(0x33, 0x33, 0x33)
GRAY = RGBColor(0x66, 0x66, 0x66)
ACCENT = RGBColor(0xC0, 0x50, 0x4D)

SW, SH = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


def slide():
    return prs.slides.add_slide(BLANK)


def textbox(s, l, t, w, h):
    tb = s.shapes.add_textbox(l, t, w, h)
    tb.text_frame.word_wrap = True
    return tb


def title(s, text, sub=None):
    tb = textbox(s, Inches(0.55), Inches(0.28), Inches(12.3), Inches(0.75))
    p = tb.text_frame.paragraphs[0]
    r = p.add_run(); r.text = text
    r.font.size, r.font.bold, r.font.color.rgb = Pt(27), True, NAVY
    r.font.name = "Arial"
    if sub:
        p2 = tb.text_frame.add_paragraph()
        r2 = p2.add_run(); r2.text = sub
        r2.font.size, r2.font.color.rgb, r2.font.name = Pt(14), GRAY, "Arial"
    # thin rule under the title
    ln = s.shapes.add_shape(1, Inches(0.55), Inches(1.02), Inches(12.3), Emu(18000))
    ln.fill.solid(); ln.fill.fore_color.rgb = NAVY; ln.line.fill.background()


def bullets(s, items, l, t, w, h, size=15):
    """items: list of (level, text) or str (level 0)."""
    tb = textbox(s, l, t, w, h)
    tf = tb.text_frame
    first = True
    for it in items:
        lvl, txt = it if isinstance(it, tuple) else (0, it)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = lvl
        p.space_after = Pt(5)
        r = p.add_run()
        r.text = ("• " if lvl == 0 else "– ") + txt
        r.font.size = Pt(size if lvl == 0 else size - 2)
        r.font.color.rgb = DARK if lvl == 0 else GRAY
        r.font.name = "Arial"
    return tb


def pic(s, name, l, t, max_w, max_h, caption=None, stretch=False):
    path = os.path.join(FIG, name)
    w0, h0 = Image.open(path).size
    if stretch:                      # fill the whole box, aspect not preserved
        w, h = int(max_w), int(max_h)
    else:
        scale = min(max_w / w0, max_h / h0)
        w, h = int(w0 * scale), int(h0 * scale)
    # center inside the box
    left = l + int((max_w - w) / 2)
    s.shapes.add_picture(path, left, t, width=w, height=h)
    if caption:
        tb = textbox(s, l, t + h + Emu(30000), max_w, Inches(0.3))
        p = tb.text_frame.paragraphs[0]
        r = p.add_run(); r.text = caption
        r.font.size, r.font.italic, r.font.color.rgb = Pt(11), True, GRAY
        r.font.name = "Arial"
        p.alignment = PP_ALIGN.CENTER
    return h


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


IN = Inches  # shorthand

# ---------------------------------------------------------------- 1 · title
s = slide()
tb = textbox(s, IN(0.9), IN(2.3), IN(11.5), IN(1.6))
p = tb.text_frame.paragraphs[0]
r = p.add_run(); r.text = "NxM Templates for SuperCDMS SNOLAB Run 4 — Ge Activation Data"
r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(36), True, NAVY, "Arial"
tb2 = textbox(s, IN(0.9), IN(3.7), IN(11.5), IN(0.9))
p = tb2.text_frame.paragraphs[0]
r = p.add_run()
r.text = "K-line event selection  ·  free-pretrigger two-exponential fits  ·  1x1 and NxM (PCA) templates"
r.font.size, r.font.color.rgb, r.font.name = Pt(18), GRAY, "Arial"
tb3 = textbox(s, IN(0.9), IN(5.6), IN(11.5), IN(0.8))
p = tb3.text_frame.paragraphs[0]
r = p.add_run(); r.text = "Zhiheng Li  —  July 2026"
r.font.size, r.font.color.rgb, r.font.name = Pt(16), DARK, "Arial"
notes(s, "Today I will present the phonon pulse-template work for SNOLAB Run 4: "
         "how we selected events on the Ge-activation K-line, the fit-and-align "
         "pipeline, the quality cuts and how each was derived, and the two "
         "template families we delivered for all 13 detectors.")

# ------------------------------------------------- 2 · motivation / selection
s = slide()
title(s, "From the Ge-activation K-line to an event sample",
      "Goal: one clean, minimally-biased pulse population per detector × channel")
bullets(s, [
    "Per detector, Prof. Saab's study marked the 10.37 keV K-line position in PTOFamps — the red line in each panel below",
    "Our event selection: a PTOFamps window bracketing the red line — position ×/÷ 1.35, a rough, somewhat arbitrary eyeballed choice; deliberately minimal, no other cuts",
    "For every selected event: cache the fully unprocessed raw MIDAS traces of all channels + event metadata",
    "13 detectors (zips) × 27–30 series → ~120 GB raw cache",
], IN(0.25), IN(1.18), IN(12.3), IN(1.45), size=14)
# credit box, top-right of the title band
ctb = textbox(s, IN(9.35), IN(0.30), IN(3.5), IN(0.72))
for i, (txt, link) in enumerate([
        ("Data: Ge Activation Data — Ops Shift 260612", None),
        ("Credit: Prof. Tarek Saab  ·  SuperCDMS Confluence",
         "https://confluence.slac.stanford.edu/spaces/CDMS/pages/716899864/Ge+Activation+Data+-+Ops+Shift+260612")]):
    p = ctb.text_frame.paragraphs[0] if i == 0 else ctb.text_frame.add_paragraph()
    r = p.add_run(); r.text = txt
    r.font.size, r.font.color.rgb, r.font.name = Pt(10), GRAY, "Arial"
    if link:
        r.hyperlink.address = link
    p.alignment = PP_ALIGN.RIGHT
pic(s, "kline_all_zips.png", IN(0.42), IN(2.72), IN(12.5), IN(4.35),
    "All 13 detectors, PTOFamps spectra (Prof. Saab's study)")
notes(s, "Everything starts from the Ge activation data. After Cf activation "
         "every detector shows the 10.37 keV K-line. Professor Saab's study "
         "located the K-line position in the PTOFamps spectrum of each "
         "detector - that is the red line in every panel here. Our event "
         "selection is exactly one condition: a window around the red line, "
         "a factor 1.35 both ways - a rough, eyeballed choice - and nothing "
         "else. For each selected event "
         "we cache the fully unprocessed raw MIDAS traces of all channels. "
         "You can already see on the weak detectors that the window will "
         "admit part of the noise-trigger population next to the K-line - "
         "that is intentional: the cache is raw, so every later cut stays "
         "explicit and reversible.")

# ------------------------------------------------------ 3 · fit quality grids (overview)
s = slide()
title(s, "Fit quality at a glance — event × channel grids")
bullets(s, [
    "One row per event, one column per channel: the low-passed trace (blue) with the fitted pulse model (red) overlaid",
    "A real event fits well in every channel at once; a noise trigger fails in every channel — a clean handle on which events are real (how we fit each trace: next slide)",
], IN(0.55), IN(1.2), IN(12.3), IN(1.3), size=14)
pic(s, "fit_examples_zip7_noise.png", IN(0.2), IN(2.75), IN(6.55), IN(3.55),
    "Noise triggers (Z7): the fit fails in every channel at once")
pic(s, "fit_examples_zip7_good.png", IN(6.6), IN(2.75), IN(6.55), IN(3.55),
    "K-line events (Z7): consistent good fits across channels")
notes(s, "Before the algorithm, a quick look at the data itself. We use "
         "event-by-channel grids: each row is one event, each column one "
         "channel, with the low-passed trace in blue and a fitted pulse model "
         "in red on top. The pattern is already clear: a real K-line event "
         "fits well in every channel at once, while a noise trigger fails in "
         "every channel at once. So the events split cleanly into two kinds. "
         "How we actually fit and align each trace is the next slide, and how "
         "we turn that split into a quantitative cut comes shortly after.")

# ------------------------------------------------------ 4 · per-trace algorithm
s = slide()
title(s, "Per-trace algorithm: low-pass → fit → align")
def steps_box(top, height, items):
    _tb = textbox(s, IN(0.55), top, IN(12.3), height)
    _first = True
    for head, rest in items:
        p = _tb.text_frame.paragraphs[0] if _first else _tb.text_frame.add_paragraph()
        _first = False
        p.space_after = Pt(6)
        r = p.add_run(); r.text = head
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(16), True, NAVY, "Arial"
        r = p.add_run(); r.text = rest
        r.font.size, r.font.color.rgb, r.font.name = Pt(16), DARK, "Arial"

steps_box(IN(1.2), IN(1.35), [
    ("1.  Low-pass", " — 100 kHz 4th-order Butterworth"),
    ("2.  Normalize", " — subtract the baseline, scale the trace to unit peak"),
    ("3.  Fit", " — two-exponential model, all 5 parameters free (including the pretrigger t₀):"),
])
pic(s, "formula_2exp.png", IN(2.6), IN(2.62), IN(8.1), IN(0.95))
steps_box(IN(3.65), IN(1.5), [
    ("4.  Two quality numbers per trace", " (recorded here, not cut yet):"),
])
# the two quality-number sub-lines, plain English
q_tb = textbox(s, IN(1.15), IN(4.02), IN(11.6), IN(0.9))
for i, (lead, rest) in enumerate([
        ("fit_ok", " — amplitude is positive, and the pulse rises faster than it falls"),
        ("NRMSE", " — RMS of the fit residual ÷ pulse peak  (smaller = better fit)")]):
    p = q_tb.text_frame.paragraphs[0] if i == 0 else q_tb.text_frame.add_paragraph()
    p.space_after = Pt(4)
    r = p.add_run(); r.text = "•  " + lead
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(15), True, DARK, "Arial"
    r = p.add_run(); r.text = rest
    r.font.size, r.font.color.rgb, r.font.name = Pt(15), DARK, "Arial"
notes(s, "The per-trace algorithm. First a low-pass filter to "
         "smooth away the high-frequency noise, then the baseline is "
         "subtracted and the trace is scaled to unit peak - without that "
         "normalization the traces could not be overlaid or compared. The "
         "core is the fit: a two-exponential function, one exponential for "
         "the rise and one for the fall, with all five parameters free, "
         "including the pretrigger - the pulse start time. The pretrigger is "
         "never pinned: real trigger times vary, and the fitted pretriggers "
         "cluster about 230 samples after the nominal value - pinning it "
         "would bias the time constants. Each fit records two quality "
         "numbers: fit_ok, a physicality check - positive amplitude, rise "
         "faster than fall - and the NRMSE, the normalized root-mean-square "
         "error, the fit residual divided by the pulse height. At this stage "
         "we only record them. Step five, alignment, and its output get "
         "their own slide next.")

# ------------------------------------------------------ 5 · alignment result
s = slide()
title(s, "5. Align — shift each trace to a common pretrigger")
bullets(s, [
    "Shift the measured trace by (fitted pretrigger − 16050) — a pure translation. Drawn at the common pretrigger, the fitted curves stack into one shape family:",
], IN(0.55), IN(1.2), IN(12.3), IN(0.95), size=16)
pic(s, "fan_zip7_PBS1_before_zoom.png", IN(0.55), IN(2.55), IN(6.35), IN(3.95),
    "All fit_ok fitted curves (Z7 PBS1) — no cut")
pic(s, "fan_zip7_PBS1_nrmse_zoom.png", IN(6.9), IN(2.55), IN(6.35), IN(3.95),
    "After NRMSE ≤ 0.4 (Z7 PBS1) — one tight shape family")
notes(s, "Step five: alignment. Each measured trace is shifted by its fitted "
         "pretrigger minus the nominal 16050 - a pure translation, nothing "
         "about the waveform is regenerated. Once everything is at the common "
         "pretrigger, the fitted curves stack up. On the left, all physical "
         "fits: you can see the slow stragglers spreading off the main "
         "bundle. On the right, after the NRMSE cut, a single tight, "
         "consistent shape family remains. That tight family is what makes a "
         "well-defined template possible - and where the cut comes from is "
         "what I show next.")

# ------------------------------------------------------ 6 · NRMSE cut
s = slide()
title(s, "Quality cut 1: NRMSE ≤ 0.4 — where the number comes from")
bullets(s, [
    "NRMSE of fit_ok events is bimodal: good fits (median ≈ 0.05–0.1) vs noise triggers (≈ 1–2), valley at ≈ 0.4–0.5",
    "The cut sits in the valley — it is read off the distribution, not tuned on the templates",
    "Weak detectors (Z1, Z4, Z6, Z18, Z19, Z22, Z24): same bimodal picture, noise peak dominates",
], IN(0.55), IN(1.2), IN(12.3), IN(1.55), size=14)
pic(s, "nrmse_zip7_PBS1.png", IN(1.4), IN(3.1), IN(10.5), IN(3.4),
    "Z7 PBS1: two clean populations, log-log axes")
notes(s, "First quality cut. The NRMSE distribution of physical fits is "
         "bimodal on every detector: a good-fit population around 0.05 to "
         "0.1, and a noise-trigger population around 1 to 2, separated by a "
         "valley at about 0.4. We place the cut in the valley - it is read "
         "off the distribution itself. This is Z7 PBS1, the channel used "
         "throughout the talk. The weak detectors - Z22, for example - show "
         "the same bimodal picture with the noise peak dominating, and there "
         "this same cut is what digs the real pulses out of the mixture. "
         "(If someone asks what a weak detector looks like, show the backup "
         "slide.)")

# ------------------------------------------ 7 · what the cut removes
s = slide()
title(s, "The rejected population is noise — verified in the raw traces")
bullets(s, [
    "Event grids of NRMSE-rejected events (median NRMSE > 0.4 across channels): the raw traces show no pulse — the cut removes noise triggers, not physics",
], IN(0.55), IN(1.2), IN(12.3), IN(1.0), size=14)
pic(s, "slow_rise_zip7_crop.png", IN(0.4), IN(2.7), IN(5.9), IN(4.35),
    "Z7: NRMSE-rejected events — raw traces are noise")
# fan-cut figure enlarged to fill the right column; its legend is pulled out
# into the readable colour-coded text below
pic(s, "fan_cut_zip7_PBS1.png", IN(6.5), IN(2.45), IN(6.85), IN(3.75), stretch=True)
_lg = textbox(s, IN(6.6), IN(6.35), IN(6.7), IN(1.05))
_lg.text_frame.word_wrap = True
_GREEN, _RED, _BLUE = RGBColor(0x2E, 0x7D, 0x32), RGBColor(0xC0, 0x39, 0x2B), RGBColor(0x4A, 0x70, 0xB0)
_p = _lg.text_frame.paragraphs[0]
for _txt, _col, _bold in [("Z7 PBS1   ", DARK, True),
                          ("── passes the cut (kept)", _GREEN, True),
                          ("      ── cut away = rejected", _RED, True)]:
    _r = _p.add_run(); _r.text = _txt
    _r.font.size, _r.font.bold, _r.font.color.rgb, _r.font.name = Pt(14), _bold, _col, "Arial"
_p2 = _lg.text_frame.add_paragraph()
for _txt, _col, _bold in [("faint blue = measured traces", _BLUE, False),
                          ("      1931 kept / 77 cut (~3.8%)", DARK, False)]:
    _r = _p2.add_run(); _r.text = _txt
    _r.font.size, _r.font.bold, _r.font.color.rgb, _r.font.name = Pt(14), _bold, _col, "Arial"
notes(s, "Before trusting the cut we looked at what it throws away. These are "
         "event grids of the rejected population on Z7: the raw traces show "
         "no pulse at all - they are noise triggers whose slow two-exp fit "
         "happened to converge. The fan-cut view on the right overlays the "
         "passing fitted curves in green and the rejected ones in red on the "
         "aligned data: the green population is the fast physical pulse "
         "shape, the red one is spread out with a median NRMSE forty times "
         "higher - 1.87 against 0.045 - and on this channel only three "
         "point eight percent of the events get cut. So the cut removes "
         "noise triggers, and no real pulses are lost.")

# --------------------------------------- 8 · follow-up 1: slow-fall tail
s = slide()
title(s, "Follow-up 1 — the slow-fall tail is a one-channel artifact")
bullets(s, [
    "The post-cut fan still shows slow-fall tails → sample them: NRMSE ≤ 0.4 AND τ_fall > 1.5 ms, 10 random events, raw vs fit drawn in all 12 channels",
    "The sampled events are real pulses → kept. Their extreme fall times trace to one channel: only PDS2 swings (τ_fall median 0.51 ms vs ≈ 0.25 ms elsewhere) — a low-frequency disturbance",
    "Conclusion: no τ_fall cut — slow-fall events passing NRMSE stay in; the extreme tail is a one-channel artifact, not physics",
], IN(0.55), IN(1.2), IN(12.3), IN(1.55), size=14)
pic(s, "slow_fall_zip7_crop.png", IN(0.3), IN(2.95), IN(6.7), IN(4.0),
    "Z7, 3 sampled slow-fall events: normal in PBS2/PCS2/PES2, swings only in PDS2")
# the two t_fall histograms side by side, cropped to the useful 0-7 ms
pic(s, "time_constants_zip7_PAS1_tfall.png", IN(7.05), IN(3.35), IN(3.05), IN(2.3),
    "Z7 PAS1 — normal channel: narrow (median 0.25 ms)")
pic(s, "time_constants_zip7_PDS2_tfall.png", IN(10.2), IN(3.35), IN(3.05), IN(2.3),
    "Z7 PDS2 — bad channel: broad tail (median 0.51 ms)")
_ft = textbox(s, IN(7.05), IN(2.62), IN(6.2), IN(0.55))
_pft = _ft.text_frame.paragraphs[0]
_rft = _pft.add_run(); _rft.text = "Fitted τ_fall distribution, same 0–7 ms axis:"
_rft.font.size, _rft.font.bold, _rft.font.color.rgb, _rft.font.name = Pt(15), True, NAVY, "Arial"
notes(s, "The first lead comes from the fan plot after the cut: some curves "
         "still fall very slowly. We chased it by sampling: among events "
         "passing the cut, take fall times above one point five "
         "milliseconds, randomly sample ten, and draw raw versus fit in "
         "every channel. Two findings. First, the sampled events are real "
         "pulses - so they stay in, and we apply no fall cut. Second, their "
         "extreme fall times all trace back to one channel: only PDS2 is "
         "swinging wildly, while the same events are normal fast pulses in "
         "the other eleven channels - so the extreme tail is a one-channel "
         "low-frequency artifact, not slow physics.")

# ------------------------------------------------- 11 · template family 1
s = slide()
title(s, "Template family 1 — analytic 2-exp, NRMSE-weighted (1x1)")
bullets(s, [
    "NRMSE-weighted mean of the fit_ok 2-exp curves",
    "Smooth & noise-free by construction",
    "ROOT TH1D, peak-normalized (+ summed PT / PS1 / PS2)",
], IN(0.55), IN(1.25), IN(12.3), IN(1.5), size=18)
pic(s, "fan_zip7_PBS1_after.png", IN(1.4), IN(3.35), IN(10.5), IN(3.1),
    "Z7 PBS1, fitted curves after NRMSE ≤ 0.4 and τ_rise ≤ 0.3 ms — the NRMSE-weighted mean of this family is the 1x1 template")
notes(s, "First template family: the analytic one. For each channel we take "
         "every physical fitted curve at the common pretrigger and average them "
         "with a weight of one over NRMSE squared - badly fit events count "
         "less but nothing is excluded by hand. After the cuts, shown here, "
         "a single tight shape family remains, and its weighted mean is the "
         "1x1 template - smooth and noise-free by construction because it is "
         "built from analytic curves, delivered as peak-normalized ROOT "
         "histograms.")

# ------------------------------------------------- 12 · template family 2
s = slide()
title(s, "Template family 2 — NxM PCA templates")
bullets(s, [
    "Per-channel PCA over the clean fitted curves (fit_ok + NRMSE ≤ 0.4 + τ_rise ≤ 0.3 ms)",
    "nxm0 = mean shape;  nxm1–4 = principal components;  real pulse = Σᵢ ampᵢ · nxmᵢ",
    "PC1 + PC2 ≈ 96–98% of the shape variance;  delivered peak-normalized",
], IN(0.55), IN(1.22), IN(12.3), IN(1.5), size=16)
pic(s, "pca_zip7_PBS1.png", IN(1.1), IN(3.3), IN(11.1), IN(3.1),
    "Z7 PBS1: nxm0 (mean) + nxm1–4 (PCs) — the oscillating components encode rise/fall-time variation")
notes(s, "Second family: the NxM PCA templates, built to capture the "
         "pulse-shape variation across events. We run a PCA over the fitted curves that "
         "pass all cuts, in a window around the pulse. The mean shape "
         "becomes template zero, and the first four principal components "
         "become templates one to four - they oscillate and can be "
         "negative, and the optimal filter fits a real pulse as a linear "
         "combination of them. The first two components already capture 96 "
         "to 98 percent of the shape variance on every detector.")

# ------------------------------------------------- 13 · summary
s = slide()
title(s, "Delivered — and what remains")
bullets(s, [
    "Two template families built for all 13 detectors:  1x1 (2-exp weighted)  +  NxM PCA",
    "Delivered in the official cdmsbats PulseTemplates format",
    "Cuts read off the data, verified in raw traces:  NRMSE ≤ 0.4,  τ_rise ≤ 0.3 ms",
], IN(0.55), IN(1.7), IN(12.3), IN(3.5), size=22)
notes(s, "To summarize: both template families are delivered for all 13 "
         "detectors in the official PulseTemplates format - the analytic "
         "1x1 templates and the PCA NxM set. The whole chain is traceable "
         "from raw traces to every figure, and both quality cuts were read "
         "off the data and verified in the raw traces. Two things remain: "
         "the final call on the rise-time ceiling versus the genuine slow "
         "pulses, and running the group's template-validation method on the "
         "new templates. Thank you - happy to take questions.")

# ------------------------------------------- backup · weak detectors (Z22)
s = slide()
title(s, "Backup — weak detectors (example: Z22)")
bullets(s, [
    "Z1 / Z4 / Z6 / Z18 / Z19 / Z22 / Z24: K-line sits inside the noise population — the PTOF window admits a noise-dominated mixture",
    "Same bimodal NRMSE picture, noise peak dominates; the same 0.4 cut digs the real pulses out — Z22 PCS1: 7198 kept / 4788 cut (~40%)",
    "Kept bundle broader than on quiet detectors; steep red curves = fits latching onto sharp noise spikes, not fast pulses being cut",
    "τ_rise ≤ 0.3 ms (after NRMSE): removes 55–74% on weak zips (Z22: 71%) vs 1.6% on Z7 — residual slow drift",
], IN(0.55), IN(1.1), IN(12.3), IN(2.15), size=13)
pic(s, "nrmse_zip22_PAS1.png", IN(0.4), IN(3.35), IN(6.3), IN(1.7),
    "Z22 PAS1: NRMSE histogram — noise dominates")
pic(s, "fan_cut_zip22_PCS1.png", IN(6.9), IN(3.35), IN(6.3), IN(1.7),
    "Z22 PCS1: kept (green) vs cut (red)")
pic(s, "fan_final_zip22_PCS1.png", IN(2.2), IN(5.55), IN(8.9), IN(1.55),
    "Z22 PCS1 after NRMSE ≤ 0.4 + τ_rise ≤ 0.3 ms — final shape family (760 fits)")
notes(s, "Backup. On the weak detectors the K-line overlaps the noise "
         "population, so the PTOF window admits a noise-dominated mixture. "
         "The NRMSE distribution is still bimodal but the noise peak "
         "dominates, and the same 0.4 cut is what extracts the real pulses "
         "- on Z22 PCS1 about forty percent of the physical fits are "
         "removed. The kept bundle is broader than on a quiet detector, and "
         "the steep red curves are fits latching onto sharp noise spikes, "
         "not fast pulses being thrown away. The rise-time ceiling then "
         "removes fifty-five to seventy-four percent of what survived the "
         "NRMSE cut on the weak zips - residual slow drift - versus one "
         "point six percent on Z7. The surviving shape family is at the "
         "bottom.")

# page numbers: "N / total" bottom-right, skip the title slide
_slides = list(prs.slides)
_total = len(_slides)
for _i, _s in enumerate(_slides, start=1):
    if _i == 1:
        continue
    _pn = _s.shapes.add_textbox(SW - Inches(1.35), SH - Inches(0.45),
                                Inches(1.1), Inches(0.3))
    _p = _pn.text_frame.paragraphs[0]
    _r = _p.add_run(); _r.text = f"{_i} / {_total}"
    _r.font.size, _r.font.color.rgb, _r.font.name = Pt(11), GRAY, "Arial"
    _p.alignment = PP_ALIGN.RIGHT

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
