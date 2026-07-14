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


def pic(s, name, l, t, max_w, max_h, caption=None):
    path = os.path.join(FIG, name)
    w0, h0 = Image.open(path).size
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
r = p.add_run(); r.text = "Phonon Pulse Templates for SuperCDMS SNOLAB Run 4"
r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(36), True, NAVY, "Arial"
tb2 = textbox(s, IN(0.9), IN(3.7), IN(11.5), IN(0.9))
p = tb2.text_frame.paragraphs[0]
r = p.add_run()
r.text = "K-line event selection  ·  free-pretrigger two-exponential fits  ·  1x1 and NxM (PCA) templates"
r.font.size, r.font.color.rgb, r.font.name = Pt(18), GRAY, "Arial"
tb3 = textbox(s, IN(0.9), IN(5.6), IN(11.5), IN(0.8))
p = tb3.text_frame.paragraphs[0]
r = p.add_run(); r.text = "Zhiheng Li  —  July 15, 2026"
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
    "Per detector, the ops-shift study marked the 10.37 keV K-line position in PTOFamps — the red line in each panel below",
    "Our event selection: a PTOFamps window bracketing the red line (position ×/÷ 1.35) — deliberately minimal, no other cuts",
    "For every selected event: cache the fully unprocessed raw MIDAS traces of all channels + event metadata",
    "13 detectors (zips) × 27–30 series → ~120 GB raw cache; every later cut stays explicit and reversible",
], IN(0.25), IN(1.18), IN(12.3), IN(1.45), size=14)
pic(s, "kline_all_zips.png", IN(0.42), IN(2.72), IN(12.5), IN(4.35),
    "All 13 detectors, PTOFamps spectra (ops-shift study): red line = fitted mean of the 10.37 keV K-line. "
    "Selection window per detector = red-line position ×/÷ 1.35.")
notes(s, "Everything starts from the Ge activation data. After Cf activation "
         "every detector shows the 10.37 keV K-line. The ops-shift study "
         "located the K-line position in the PTOFamps spectrum of each "
         "detector - that is the red line in every panel here. Our event "
         "selection is exactly one condition: a window around the red line, "
         "a factor 1.35 both ways, and nothing else. For each selected event "
         "we cache the fully unprocessed raw MIDAS traces of all channels. "
         "You can already see on the weak detectors that the window will "
         "admit part of the noise-trigger population next to the K-line - "
         "that is intentional: the cache is raw, so every later cut stays "
         "explicit and reversible.")

# ------------------------------------------------------ 3 · per-trace algorithm
s = slide()
title(s, "Per-trace algorithm: low-pass → free-pretrigger fit → align")
bullets(s, [
    "1.  100 kHz 4th-order Butterworth low-pass (steady-state init — no filter start-up transient)",
    "2.  Baseline = median of samples 2000–12000, subtracted; normalize by the global trace peak",
    "3.  Two-exponential fit — all 5 parameters free, including the onset:",
    (1, "y(t) = A·[exp(−(t−t₀)/τ_fall) − exp(−(t−t₀)/τ_rise)] + b,   t₀ ∈ 16050 ± 3000 samples"),
    (1, "fit window 12550–24050 (stride 4);  τ_rise ∈ [1 µs, 5 ms],  τ_fall ∈ [10 µs, 20 ms]"),
    "4.  Quality numbers — fit_ok := A>0 and 0<τ_rise<τ_fall;  NRMSE := RMS(residual)/fit peak (recorded, no cut yet)",
    "5.  Align — shift the measured trace by (fitted onset − 16050), sub-sample interpolation: a pure translation",
], IN(0.55), IN(1.25), IN(12.3), IN(3.1), size=15)
tb = bullets(s, [
    "Why a free onset?  Real trigger times vary event-by-event — fitted onsets cluster ≈230 samples after the nominal 16050. Pinning the onset distorts every other parameter.",
], IN(0.55), IN(4.38), IN(12.3), IN(0.75), size=14)
for pgh in tb.text_frame.paragraphs:
    for r in pgh.runs:
        r.font.color.rgb = ACCENT
pic(s, "fan_zip7_PBS1_before.png", IN(0.55), IN(5.25), IN(6.0), IN(1.75),
    "Fitted curves at common onset, peak-normalized — ALL fit_ok events (no cut)")
pic(s, "fan_zip7_PBS1_nrmse.png", IN(6.85), IN(5.25), IN(6.0), IN(1.75),
    "Same, after NRMSE ≤ 0.4 — a single tight shape family remains (Z7 PBS1)")
notes(s, "The per-trace algorithm, five steps. Low-pass at 100 kilohertz, "
         "baseline subtraction, peak normalization, then a two-exponential fit "
         "where all five parameters are free, including the pulse onset. The "
         "onset is never pinned: real trigger times vary, and the fitted "
         "onsets cluster about 230 samples after the nominal pretrigger - "
         "pinning it would bias the time constants. Each fit records a "
         "physicality flag and an NRMSE; no cut yet. Finally the measured "
         "trace is aligned by shifting it by the fitted onset - a pure "
         "translation. The two fan plots show the output of the fit step: "
         "every fitted curve drawn at the common onset, peak-normalized. On "
         "the left, all physical fits - you can see slow components spreading "
         "off the main bundle. On the right, after the NRMSE cut, a single "
         "tight shape family remains. Where that cut comes from is the next "
         "part of the talk.")

# ------------------------------------------------------ 4 · fit example grids
s = slide()
title(s, "Fit quality at a glance — event × channel grids")
bullets(s, [
    "One row per event, one column per channel: low-passed trace (blue) vs 2-exp fit (red), NRMSE stamped per panel",
    "The same event fits consistently across channels; a noise trigger fails in all channels at once",
    "Every figure carries its full processing chain in the header → self-documenting",
], IN(0.55), IN(1.2), IN(12.3), IN(1.3), size=14)
pic(s, "fit_examples_zip7_noise.png", IN(0.55), IN(2.6), IN(6.0), IN(4.1),
    "Noise triggers: the fit fails in every channel at once")
pic(s, "fit_examples_zip7_good.png", IN(6.85), IN(2.6), IN(6.0), IN(4.1),
    "K-line events: consistent good fits across channels")
notes(s, "To judge the fits we use event-by-channel grids: each row is one "
         "event, each column one channel. A real K-line event fits well in "
         "all channels simultaneously, while a noise trigger - like the top "
         "rows here - fails everywhere at once. The per-panel NRMSE makes "
         "this quantitative. All our figures carry the processing chain "
         "stamped in the header, so each PNG is self-documenting.")

# ------------------------------------------------------ 5 · aligned overlay
s = slide()
title(s, "Alignment result — overlaid measured traces")
bullets(s, [
    "All fit_ok traces shifted to the common onset (blue) + point-by-point mean (red) + NRMSE-weighted mean of the fitted curves (orange, w = 1/max(NRMSE, 0.01)²)",
    "Peak zoom on a quiet detector: a tight bundle — the template input is well defined. Note the faint displaced bundle beside the main one, visible on both crystal faces (S1 and S2) — more on it later",
], IN(0.55), IN(1.2), IN(12.3), IN(1.5), size=14)
pic(s, "aligned_zoom_zip7_PCS1.png", IN(0.35), IN(3.1), IN(6.15), IN(3.4),
    "Z7 PCS1 (S1 face) — peak zoom; the faint displaced bundle is clearly visible")
pic(s, "aligned_zoom_zip7_PBS2.png", IN(6.85), IN(3.1), IN(6.15), IN(3.4),
    "Z7 PBS2 (S2 face) — same faint displaced bundle")
notes(s, "Here's what things look like after alignment - zoomed right on the "
         "peak. The blue band is thousands of measured traces stacked on top "
         "of each other; red is their average; orange is the weighted average "
         "of the fitted curves. On a quiet detector the bundle is very tight "
         "- the pulse shape really is highly consistent, so the raw material "
         "for a template is good. Now please notice one detail: in both "
         "channels there is a faint, displaced little bundle next to the "
         "main one - very clear in the left panel. And these two channels "
         "sit on opposite faces of the crystal, so this is not a quirk of "
         "one channel. Keep it in mind - we'll come back to what it is.")

# ------------------------------------------------------ 6 · NRMSE cut
s = slide()
title(s, "Quality cut 1: NRMSE ≤ 0.4 — where the number comes from")
bullets(s, [
    "NRMSE of fit_ok events is bimodal: good fits (median ≈ 0.05–0.1) vs noise triggers (≈ 1–2), valley at ≈ 0.4–0.5",
    "The cut sits in the valley — it is read off the distribution, not tuned on the templates",
    "Weak detectors (Z1, Z4, Z6, Z18, Z19, Z22, Z24): the PTOF window admits a noise-dominated mixture — this cut is what extracts the real-pulse population",
], IN(0.55), IN(1.2), IN(12.3), IN(1.55), size=14)
pic(s, "nrmse_zip7_PBS1.png", IN(1.9), IN(2.9), IN(9.5), IN(2.05),
    "Z7 PBS1 (quiet): two clean populations, log-log axes")
pic(s, "nrmse_zip22_PAS1.png", IN(1.9), IN(5.2), IN(9.5), IN(2.05),
    "Z22 PAS1 (weak): noise population dominates — the window alone is not enough")
notes(s, "First quality cut. The NRMSE distribution of physical fits is "
         "bimodal on every detector: a good-fit population around 0.05 to "
         "0.1, and a noise-trigger population around 1 to 2, separated by a "
         "valley at about 0.4. We place the cut in the valley - it is read "
         "off the distribution itself. On quiet detectors like Z7 the noise "
         "population is small; on weak detectors like Z22 it dominates, and "
         "this cut is what digs the real pulses out of the mixture.")

# ------------------------------------------ 7 · what the cut removes
s = slide()
title(s, "The rejected population is noise — verified in the raw traces")
bullets(s, [
    "Event grids of NRMSE-rejected events (median NRMSE > 0.4 across channels): the raw traces show no pulse — the cut removes noise triggers, not physics",
    "Fan-cut view: fitted curves that pass (green) vs cut away (red) on top of the aligned data, median NRMSE of each population stamped per channel",
], IN(0.55), IN(1.2), IN(12.3), IN(1.35), size=14)
pic(s, "slow_rise_zip22_crop.png", IN(0.55), IN(2.7), IN(5.9), IN(4.35),
    "Z22: NRMSE-rejected events — raw traces are noise")
pic(s, "fan_cut_zip22_PCS1.png", IN(6.7), IN(3.4), IN(6.3), IN(3.1),
    "Z22 PCS1: pass (green) vs rejected (red)")
notes(s, "Before trusting the cut we looked at what it throws away. These are "
         "event grids of the rejected population on Z22: the raw traces show "
         "no pulse at all - they are noise triggers whose slow two-exp fit "
         "happened to converge. The fan-cut view on the right overlays the "
         "passing fitted curves in green and the rejected ones in red on the "
         "aligned data: the green population is the fast physical pulse "
         "shape, the red one is spread out with a median NRMSE three times "
         "higher. So the cut removes noise, not physics.")

# --------------------------------------- 8 · follow-up 1: slow-fall tail
s = slide()
title(s, "Follow-up 1 — the slow-fall tail is a one-channel artifact")
bullets(s, [
    "The post-cut fan still shows slow-fall tails → sample them: NRMSE ≤ 0.4 AND τ_fall > 1.5 ms (reference channel PDS2), 10 random events, raw vs fit drawn in all 12 channels",
    "The same events are normal fast pulses in the other 11 channels — only PDS2 swings (τ_fall median 0.51 ms vs ≈ 0.25 ms elsewhere): a channel-specific low-frequency disturbance",
    "Conclusion: artifact, not physics → no τ_fall cut",
], IN(0.55), IN(1.2), IN(12.3), IN(1.55), size=14)
pic(s, "slow_fall_zip7_crop.png", IN(0.45), IN(2.9), IN(7.3), IN(4.1),
    "Z7, 3 of the sampled slow-fall events: normal pulses in PBS2/PCS2/PES2, low-frequency swings only in PDS2")
pic(s, "time_constants_zip7_PDS2.png", IN(8.0), IN(3.6), IN(5.1), IN(2.2),
    "Z7 PDS2: broad τ_fall tail — the artifact in the distributions")
notes(s, "The first lead comes from the fan plot after the cut: some curves "
         "still fall very slowly. We chased it with the same recipe: among "
         "events passing the cut, take fall times above one point five "
         "milliseconds, randomly sample ten, and draw raw versus fit in "
         "every channel. The result is clean: in the other eleven channels "
         "these events are perfectly normal fast pulses - only PDS2, one "
         "single channel, is swinging wildly. So it's not the event that's "
         "slow, it's that one channel's low-frequency disturbance. "
         "Conclusion: no fall cut is needed - artifact, not physics.")

# --------------------------------------- 9 · follow-up 2: genuine slow rise
s = slide()
title(s, "Follow-up 2 — genuine slow-rise pulses (“shadow” events)")
bullets(s, [
    "Same sampling recipe on the rise side: median NRMSE ≤ 0.4 AND median τ_rise > 0.2 ms → the raw traces show real pulses — onset aligned, peak late, consistent across channels",
    "They are the faint displaced bundle in the aligned overlays — a genuine second pulse shape (candidate surface/bulk effect, not settled)",
    "Real physics → cannot simply be cut away; exactly the shape variation the multi-template NxM method is built to capture",
], IN(0.55), IN(1.2), IN(12.3), IN(1.55), size=14)
pic(s, "shadow_zip7_crop.png", IN(1.2), IN(2.95), IN(10.9), IN(4.15),
    "Z7 shadow events (first 4 channels): raw (gray) / LP (blue) / fit (red) — genuine slow pulses, onset aligned, peak late")
notes(s, "The second lead is the slow rise. Same recipe: take events that "
         "fit well - NRMSE fine - but whose median rise time is above zero "
         "point two milliseconds, sample them, look at the raw traces. This "
         "time the conclusion is the opposite: these are real pulses. Onset "
         "aligned, peak arriving late, consistent across all channels - "
         "they are exactly the shadow from the alignment plot. So the slow "
         "rise cannot simply be cut away: there is real physics in it, "
         "possibly related to where in the crystal the event happens; that "
         "is not settled yet.")

# --------------------------------------- 10 · τ_rise ceiling on template input
s = slide()
title(s, "Slow drift also fits “slow”: a τ_rise ≤ 0.3 ms ceiling")
bullets(s, [
    "On noisy-window detectors a smooth baseline drift survives the NRMSE cut — a slow 2-exp hugs it with a tiny residual — and mimics a slow rise",
    "Fast pulses sit at τ_rise ≈ 0.1 ms (p90 ≈ 0.15 ms), far below the drift tail → a ceiling at 0.3 ms blocks the drift at ≈ 2–5% signal cost",
    "Keeps most genuine slow pulses, trims the very slowest — documented trade-off, final decision pending",
], IN(0.55), IN(1.2), IN(12.3), IN(1.75), size=14)
pic(s, "time_constants_zip7_PAS1.png", IN(1.4), IN(3.15), IN(10.5), IN(2.15),
    "Z7 PAS1: fitted τ_rise (median 0.105 ms) and τ_fall distributions")
tb = bullets(s, [
    "On quiet detectors both τ_rise and τ_fall distributions are narrow — the pulse shape is stable across events",
], IN(1.4), IN(5.75), IN(10.5), IN(1.0), size=13)
notes(s, "But on the slow-rise side there is also a troublemaker: on "
         "detectors with a noisy window, a slow baseline drift also fits as "
         "a slow rise, with a tiny residual - NRMSE cannot catch it. The "
         "real pulses cluster near zero point one milliseconds while the "
         "drift tail stretches much further, so for the template input we "
         "set a ceiling at zero point three milliseconds. That blocks the "
         "drift and keeps the vast majority of real pulses - including part "
         "of the shadow population; the price is that the very slowest "
         "genuine pulses get trimmed too. That trade-off is documented and "
         "not final - I would like your input on it later.")

# ------------------------------------------------- 11 · template family 1
s = slide()
title(s, "Template family 1 — analytic 2-exp, NRMSE-weighted (1x1)")
bullets(s, [
    "Per channel: weighted mean of ALL fit_ok fitted curves at the common onset, weight w = 1/max(NRMSE, 0.01)²",
    "Badly-fit events count less but are never excluded — robust and smooth (noise-free by construction)",
    "Delivered as peak-normalized 32768-bin ROOT TH1D per channel + summed PT/PS1/PS2 templates",
], IN(0.55), IN(1.2), IN(12.3), IN(1.55), size=14)
pic(s, "fan_zip7_PBS1_after.png", IN(1.4), IN(3.35), IN(10.5), IN(3.1),
    "Z7 PBS1, fitted curves after NRMSE ≤ 0.4 and τ_rise ≤ 0.3 ms — the NRMSE-weighted mean of this family is the 1x1 template")
notes(s, "First template family: the analytic one. For each channel we take "
         "every physical fitted curve at the common onset and average them "
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
    "Input: fitted curves passing fit_ok + NRMSE ≤ 0.4 + τ_rise ≤ 0.3 ms, at common onset, peak-normalized (PCA window 15550–24050, ≤ 3000 curves/channel)",
    "nxm0 = mean shape;  nxm1…nxm4 = first four principal components — a real pulse is fit as Σᵢ ampᵢ · nxmᵢ",
    "PC1 + PC2 already capture 96–98% of the shape variance; final step before delivery: normalize all five to unit peak — the delivered product",
], IN(0.55), IN(1.2), IN(12.3), IN(1.55), size=14)
pic(s, "pca_zip7_PAS1.png", IN(1.5), IN(2.95), IN(10.3), IN(2.0))
pic(s, "pca_zip7_PBS1.png", IN(1.5), IN(5.0), IN(10.3), IN(2.0),
    "Z7 PAS1 / PBS1: nxm0 (mean) + nxm1–4 (PCs) — the oscillating components encode rise/fall-time variation")
notes(s, "Second family: the NxM PCA templates, built to capture the shape "
         "variation we just saw. We run a PCA over the fitted curves that "
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
    "Delivered for all 13 zips, official cdmsbats PulseTemplates layout (zip{N}/{chan}, {chan}nxm0–4, summed PT/PS1/PS2):",
    (1, "SNOLAB_R4_20260706_ZhihengLi_zip{N}.root — 2-exp NRMSE-weighted (1x1)"),
    (1, "SNOLAB_R4_20260707_ZhihengLi_pca_zip{N}.root — NxM PCA (normalized)"),
    "Every step is traceable: raw cache → per-series fit checkpoints indexed by EventNumber → self-documenting figures (11 types × 13 zips, all versioned)",
    "Cuts derived from the data, validated in raw traces: NRMSE ≤ 0.4 (bimodal valley), τ_rise ≤ 0.3 ms (drift leakage)",
    "Open items:",
    (1, "final decision on the τ_rise ceiling vs the genuine slow-pulse population"),
    (1, "run the group's template-validation method on the new templates"),
], IN(0.55), IN(1.3), IN(12.3), IN(4.6), size=16)
notes(s, "To summarize: both template families are delivered for all 13 "
         "detectors in the official PulseTemplates format - the analytic "
         "1x1 templates and the PCA NxM set. The whole chain is traceable "
         "from raw traces to every figure, and both quality cuts were read "
         "off the data and verified in the raw traces. Two things remain: "
         "the final call on the rise-time ceiling versus the genuine slow "
         "pulses, and running the group's template-validation method on the "
         "new templates. Thank you - happy to take questions.")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
