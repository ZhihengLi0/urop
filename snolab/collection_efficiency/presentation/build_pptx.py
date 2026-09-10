#!/usr/bin/env python3
"""Build the 13-min collection-efficiency deck (16:9, English, speaker notes).

    python3 build_pptx.py            # writes SNOLAB_R4_collection_efficiency_20260910.pptx
    module load libreoffice && soffice --headless --convert-to pdf <the pptx>

Every number on a slide is copied from the result text files in
../results/plots/current_power_overlay/ (energies.txt, the *_hist_*.txt) or from
../NOTES.md; nothing is computed here.
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "SNOLAB_R4_collection_efficiency_20260910.pptx")

NAVY = RGBColor(0x1F, 0x38, 0x64)
DARK = RGBColor(0x33, 0x33, 0x33)
GRAY = RGBColor(0x66, 0x66, 0x66)
RED = RGBColor(0xC0, 0x39, 0x2B)
SW, SH = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]
n_slide = 0


def textbox(s, l, t, w, h):
    tb = s.shapes.add_textbox(l, t, w, h)
    tb.text_frame.word_wrap = True
    return tb


def title(s, text, sub=None):
    tb = textbox(s, Inches(0.55), Inches(0.25), Inches(12.3), Inches(0.8))
    p = tb.text_frame.paragraphs[0]
    r = p.add_run(); r.text = text
    r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(26), True, NAVY, "Arial"
    if sub:
        p2 = tb.text_frame.add_paragraph()
        r2 = p2.add_run(); r2.text = sub
        r2.font.size, r2.font.color.rgb, r2.font.name = Pt(14), GRAY, "Arial"
    ln = s.shapes.add_shape(1, Inches(0.55), Inches(1.06), Inches(12.3), Emu(18000))
    ln.fill.solid(); ln.fill.fore_color.rgb = NAVY; ln.line.fill.background()


def bullets(s, items, l, t, w, h, size=15):
    """items: str (level 0) or (level, text); a text starting with '!' is red."""
    tb = textbox(s, l, t, w, h)
    tf = tb.text_frame
    first = True
    for it in items:
        lvl, txt = it if isinstance(it, tuple) else (0, it)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(6)
        r = p.add_run()
        red = txt.startswith("!")
        txt = txt.lstrip("!")
        r.text = ("• " if lvl == 0 else "    – ") + txt
        r.font.size = Pt(size if lvl == 0 else size - 2)
        r.font.color.rgb = RED if red else (DARK if lvl == 0 else GRAY)
        r.font.name = "Arial"
        r.font.bold = red
    return tb


def pic(s, name, l, t, max_w, max_h):
    path = os.path.join(FIG, name)
    w0, h0 = Image.open(path).size
    scale = min(max_w / w0, max_h / h0)
    w, h = int(w0 * scale), int(h0 * scale)
    s.shapes.add_picture(path, l + int((max_w - w) / 2), t + int((max_h - h) / 2),
                         width=w, height=h)


def caption(s, text, l, t, w, size=11):
    tb = textbox(s, l, t, w, Inches(0.4))
    r = tb.text_frame.paragraphs[0].add_run(); r.text = text
    r.font.size, r.font.color.rgb, r.font.name, r.font.italic = Pt(size), GRAY, "Arial", True


def footer(s, text):
    tb = textbox(s, Inches(0.55), Inches(7.05), Inches(11.2), Inches(0.35))
    r = tb.text_frame.paragraphs[0].add_run(); r.text = text
    r.font.size, r.font.color.rgb, r.font.name = Pt(9), GRAY, "Arial"


def new(ttl, sub=None, notes="", foot=None):
    global n_slide
    n_slide += 1
    s = prs.slides.add_slide(BLANK)
    if ttl:
        title(s, ttl, sub)
    tb = textbox(s, Inches(12.5), Inches(7.05), Inches(0.6), Inches(0.35))
    r = tb.text_frame.paragraphs[0].add_run(); r.text = str(n_slide)
    r.font.size, r.font.color.rgb, r.font.name = Pt(10), GRAY, "Arial"
    if foot:
        footer(s, foot)
    s.notes_slide.notes_text_frame.text = notes
    return s


L, T, W, H = Inches(0.55), Inches(1.25), Inches(12.3), Inches(5.7)

# ------------------------------------------------------------------ 1 title
s = new(None, notes="Title.")
tb = textbox(s, Inches(0.9), Inches(2.2), Inches(11.5), Inches(1.6))
p = tb.text_frame.paragraphs[0]
r = p.add_run(); r.text = "Phonon collection efficiency of Z7 from the 10.37 keV K line"
r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(34), True, NAVY, "Arial"
p = tb.text_frame.add_paragraph()
r = p.add_run(); r.text = "the energy a K-line event leaves in the TESs, from the fitted current pulse through the TES equations"
r.font.size, r.font.color.rgb, r.font.name = Pt(18), GRAY, "Arial"
tb = textbox(s, Inches(0.9), Inches(4.6), Inches(11.5), Inches(1.2))
p = tb.text_frame.paragraphs[0]
r = p.add_run(); r.text = "Zhiheng Li  ·  University of Minnesota  ·  SuperCDMS SNOLAB Run 4  ·  September 2026"
r.font.size, r.font.color.rgb, r.font.name = Pt(16), DARK, "Arial"
p = tb.text_frame.add_paragraph()
r = p.add_run(); r.text = "github.com/ZhihengLi0/urop  →  snolab/collection_efficiency/"
r.font.size, r.font.color.rgb, r.font.name = Pt(13), GRAY, "Arial"

# ------------------------------------------------------------------ 2 question
s = new("The question, and why the trace alone does not answer it",
        notes="Collection efficiency = energy absorbed by the TESs / 10.37 keV. "
              "The trace is a current; its integral is a charge, not an energy. "
              "So the current must be converted to power with the TES equations first.")
pic(s, "chain.png", L, T, W, Inches(2.5))
bullets(s, [
    "Collection efficiency = the energy that ends up in the TES films ÷ the 10.37 keV the event deposited",
    "What we record is a current: the TES current changes by δI(t) when phonons heat the film",
    "!The area under the current trace is a charge, not an energy — it cannot be compared with 10.37 keV",
    "So the current pulse has to be turned into a power pulse first, using the TES equations; the area under the power pulse is the energy",
    "Everything today is one detector, Z7 (the quietest one), and the K-line events of the Ge activation run",
], L, Inches(3.95), W, Inches(3.0), size=16)

# ------------------------------------------------------------------ 3 data
s = new("The events: the 10.37 keV K line of the Ge activation run, on Z7",
        notes="Z7 summed PTOFamps over 27 series, our own rebuild with no cut; "
              "the K line sits at 2e-6 A. K-line events: 2207 over 30 series; raw traces "
              "of all channels saved; the bias point of every channel read from detectorConfig.")
pic(s, "spectrum_zip7.png", L, T, Inches(7.9), Inches(4.3))
bullets(s, [
    "After the Cf activation every detector produces mono-energetic 10.37 keV events (71Ge electron capture)",
    "On Z7 the K line is well separated from the noise triggers: a clean sample of identical events",
    "2207 K-line events over 30 series; for each one the raw trace of every phonon channel was saved (11 channels read out on Z7)",
    "For each channel the bias point (I₀, R₀, R_p, R_sh) is read from the processing's detectorConfig",
    "Same sample as the pulse-template work — nothing new was selected",
], Inches(8.65), T, Inches(4.2), Inches(5.0), size=13)
caption(s, "Summed PTOFamps of Z7 rebuilt from the Prompt processing (purple); black: the ops note's histogram, "
           "which rejects SumPF/PT < 0.1; red line: the K line.", L, Inches(5.6), Inches(7.9), size=10)

# ------------------------------------------------------------------ 4 formula
s = new("From current to power: the TES equations, small-signal",
        notes="Method 1 of the CDMS collection-efficiency note, from Irwin & Hilton. Linear term "
              "dominates; quadratic term about 2%. Constants are measured per channel. "
              "ADC to ampere: 3.145728e9 ADC per A, i.e. 1 ADC = 0.318 nA.")
pic(s, "formula.png", L, T, W, Inches(4.2))
bullets(s, [
    "The power absorbed by the film is the change of Joule heating when the current moves by δI: a linear term plus a quadratic term (Irwin & Hilton; Method 1 of the CDMS collection-efficiency note)",
    "Both coefficients come from the measured bias point of that channel — nothing is fitted or tuned",
    "The trace is in ADC counts: 3 145 728 000 ADC = 1 A, so 1 ADC = 0.318 nA. Only the change above the baseline is used",
    "Three variants of the formula exist (c₂ = 2, 1, −1); they differ by under 1.2 % in energy, so the choice is not the main uncertainty (backup)",
], L, Inches(5.5), W, Inches(1.6), size=13)

# ------------------------------------------------------------------ 5 peak top
s = new("One pulse read three ways: ADC, current, power  —  the height",
        "Z7 PBS1, event 30646, zoomed on the peak; every curve is the same trace",
        notes="Grey dots raw samples, blue 100 kHz low pass (what the fit sees), green 20 kHz "
              "(official Eabs prefilter), red the two-exponential fit. 98 samples within 10% of the "
              "peak, so the largest raw sample is the largest noise excursion: 885 vs 717 ADC, 23% high. "
              "Filtering reduces the bias, the fit removes it.")
pic(s, "peak_top.png", L, T, W, Inches(5.1))
caption(s, "Grey: raw samples.  Blue: 100 kHz low pass (what the fit sees).  Green: 20 kHz (the official Eabs prefilter).  "
           "Red: the two-exponential fit; pink band = fit ± 1σ noise.  Yellow: the flat top, 98 samples within 10 % of the peak.  "
           "Largest raw sample 885 ADC against 717 from the fit: +23 %.", L, Inches(6.4), W, size=11)

# ------------------------------------------------------------------ 6 peak bottom
s = new("One pulse read three ways  —  the power, and its area",
        "same event; the fitted current put through the formula",
        notes="Red: power from the fit = linear + quadratic. Quadratic drawn x20 to be visible: "
              "1.91% of peak power, 1.30% of energy. Shaded area = 305.2 eV, 99% inside this window. "
              "Bias point printed at the bottom.")
pic(s, "peak_bottom.png", L, T, W, Inches(3.3))
bullets(s, [
    "Red: the power pulse from the fitted current — the two terms added. Blue dashed: the linear term alone, almost the whole thing. Purple dotted: the quadratic term alone, drawn ×20 so it can be seen",
    "!Peak 104.6 fW = 102.6 (linear) + 2.0 (quadratic): the quadratic term is 1.9 % of the peak power and 1.3 % of the energy — the power pulse has the shape of the current pulse",
    "!The shaded area is the energy this channel absorbed: 305.2 eV; 99 % of it lies inside this 1.3 ms window",
    "Grey dots and green: the same formula applied to the raw and 20 kHz traces, for comparison only. Bottom line: the measured bias point that fixes the two coefficients",
], L, Inches(4.7), W, Inches(2.4), size=13)

# ------------------------------------------------------------------ 7 fit+power overlay
s = new("Every event gets the same treatment: fit the current, convert to power",
        "Z7 PBS1, two of the 15 example events of series 24260617_063934",
        notes="Left axis current in uA, right axis power in fW tied by the linear coefficient. "
              "Dashed navy the fitted current, red the power from it, grey the raw trace for "
              "reference. Yellow band the official Eabs window. Energies of the 15 events "
              "range 198 to 448 eV in this one channel.")
pic(s, "pulse_ev30646.png", L, T, Inches(6.05), Inches(2.4))
pic(s, "pulse_ev100231.png", Inches(6.8), T, Inches(6.05), Inches(2.4))
pic(s, "pulse_legend.png", Inches(2.0), Inches(3.7), Inches(9.3), Inches(0.4))
bullets(s, [
    "Each trace is fitted with A·[e^(−t/τ_f) − e^(−t/τ_r)] directly in current units, with the pulse start left free (±4.8 ms around the trigger)",
    "Left axis: fitted current δI in µA (navy dashed). Right axis: the power it implies in fW (red). The raw trace (grey) is only drawn for reference",
    "The two curves lie on top of each other because the quadratic term is only 2 % — the right axis is just the left axis times 4.5×10⁻⁷ V",
    "Yellow band: the official Eabs integration window (−0.5 to +1 ms). The fit needs no window",
    "Fits are kept if the residual is under 20 % of the pulse height (NRMSE ≤ 0.2; typical values 0.03–0.07). Same channel, 15 events: energies from 198 to 448 eV",
], L, Inches(4.2), W, Inches(2.9), size=13)

# ------------------------------------------------------------------ 8 cumulative
s = new("Why the fit is integrated and not the raw trace",
        "cumulative energy ∫₀ᵗ P dt over the whole 52 ms trace, Z7 PBS1",
        notes="Red: from the fitted pulse, flat before, rises within 1 ms, flat after; the end value "
              "equals the closed form (green dashed). Grey: from the raw trace, drifts; for event "
              "210571 it ends at -169 eV against 277 eV from the fit. A 1 nA baseline drift over "
              "15 ms is already 42 eV.")
pic(s, "cum_ev30646.png", L, T, Inches(6.05), Inches(2.4))
pic(s, "cum_ev210571.png", Inches(6.8), T, Inches(6.05), Inches(2.4))
pic(s, "cum_legend.png", Inches(3.3), Inches(3.7), Inches(6.7), Inches(0.4))
bullets(s, [
    "Horizontal axis: the whole trace, 0 to 52.43 ms; the trigger is the dotted line at 26.2 ms. Vertical: energy accumulated so far",
    "Red, from the fitted pulse: zero before the pulse, up within 1 ms, then flat. Its end value is exactly the closed-form integral (green dashed) — the energy does not depend on any window",
    "!Grey, from the raw trace: it drifts. A baseline offset of 1 nA over 15 ms already adds 42 eV. For the right-hand event the raw integral ends at −169 eV against 277 eV from the fit",
    "This is the reason the energy is taken from the fitted pulse, as a formula in A, τ_r, τ_f, and not from a numerical integral of the data",
], L, Inches(4.2), W, Inches(2.9), size=13)

# ------------------------------------------------------------------ 9 all channels
s = new("One event, all channels: the energies add up to 33 % of 10.37 keV",
        "Z7 event 30646; four of the eleven channels shown, same axes as before",
        notes="PBS1 305, PES1 489 (largest), PES2 195 (smallest), PDS2 391 but NRMSE 0.14 and the "
              "low-frequency swing after 5 ms. Sum over 11 channels 3419 eV = 33.0%; official-window "
              "raw sum 3397 eV = 32.8%, 0.6% apart.")
pic(s, "allchan_PBS1.png", L, T, Inches(6.05), Inches(2.1))
pic(s, "allchan_PES1.png", Inches(6.8), T, Inches(6.05), Inches(2.1))
pic(s, "allchan_PES2.png", L, Inches(3.4), Inches(6.05), Inches(2.1))
pic(s, "allchan_PDS2.png", Inches(6.8), Inches(3.4), Inches(6.05), Inches(2.1))
bullets(s, [
    "The channels see very different shares: PES1 489 eV, PES2 195 eV — the event happened closer to one side. Time constants also differ (τ_f 150–250 µs)",
    "!Sum over the 11 channels: 3419 eV = 33.0 % of 10.37 keV. The official window applied to the raw traces gives 3397 eV = 32.8 %, 0.6 % apart",
    "PDS2 (bottom right) carries a slow swing after 5 ms — a low-frequency artefact of that channel; its fit residual is 0.14, three times the others",
], L, Inches(5.6), W, Inches(1.5), size=12.5)

# ------------------------------------------------------------------ 10 PBS1 histogram
s = new("Every K-line event, one channel: the energy distribution of PBS1",
        "1917 events over 30 series; one entry = one event = one fit integrated",
        notes="Red filled: fitted-pulse energy, peak 284.8 eV, sigma 42.4 eV (14.9%). Grey outline: "
              "official window on the raw trace, 284.2 eV. Dashed: Gaussian fit to the core only, "
              "so its centre is the peak, not the mean. Right tail to 600 eV: events near PBS1. "
              "290 events dropped by the NRMSE cut.")
pic(s, "hist_PBS1.png", L, T, Inches(8.3), Inches(5.6))
bullets(s, [
    "Horizontal: energy absorbed in PBS1, 10 eV per bin. Vertical: number of events",
    "Red: from the fitted pulse. Grey outline: the official window on the raw trace. Same peak to 0.2 %",
    "!Peak 285 eV, width 42 eV = 15 % — for a line whose energy is fixed",
    "The dashed curve is a Gaussian fitted to the core only, so μ is the peak position, not the mean",
    "The distribution is right-skewed: the tail to 600 eV is events that happened near this channel",
    "So one channel's width is mostly event position, not noise — the noise floor of a single fit is a few percent",
    "290 of the 2207 events fail the fit-quality cut in this channel",
], Inches(9.0), T, Inches(3.9), Inches(5.7), size=12)

# ------------------------------------------------------------------ 11 all channels hist
s = new("Every channel: each is skewed, and the peaks must not be added",
        "four of the eleven panels; all eleven in the backup",
        notes="PBS1 peak 285 sigma 15%; PFS1 the narrowest 6.8%; PES1 broad tail to 1.4 keV; PDS2 "
              "fits only 42% of events, left out of the sum. Right skew: peak below mean everywhere. "
              "Sum of the ten core-channel means = 3162 eV; sum of Gaussian peaks would be 21% low.")
pic(s, "hist_PBS1_panel.png", L, T, Inches(4.35), Inches(2.75))
pic(s, "hist_PFS1_panel.png", Inches(5.0), T, Inches(4.35), Inches(2.75))
pic(s, "hist_PES1_panel.png", L, Inches(4.1), Inches(4.35), Inches(2.75))
pic(s, "hist_PDS2_panel.png", Inches(5.0), Inches(4.1), Inches(4.35), Inches(2.75))
bullets(s, [
    "Every channel is right-skewed, so its Gaussian peak sits below its mean: PBS1 285 vs 311 eV, PES1 256 vs 358 eV",
    "!Peaks of skewed distributions do not add — the sum of the eleven peaks is 21 % low. Means do add. The per-event sum on the next slide is the honest quantity",
    "Widths range from 6.8 % (PFS1) to 27 % (PDS1, PES2): the channels differ in how much of the position spread they see",
    "!PDS2 fits only 42 % of the events (the low-frequency artefact fails the residual cut) and is left out of the core sum; ten channels remain, each fitting ≥ 95 % of events",
], Inches(9.55), T, Inches(3.4), Inches(5.7), size=11.5)

# ------------------------------------------------------------------ 12 sum
s = new("Summed over channels: collection efficiency 32 ± 1 %",
        "the total energy the TESs absorbed per K-line event",
        notes="Grey: ten core channels, 1827 events, mu 3162 eV = 30.5%, sigma 7.5%. Green: all eleven "
              "channels but only the 797 events where PDS2 fits, 3263 eV. Adding PDS2 gives a bracket "
              "31.5 to 32.9 because that subsample is biased (its core sum is 4.8% low). Red line "
              "10.37 keV.")
pic(s, "hist_sum.png", L, T, Inches(8.3), Inches(5.6))
bullets(s, [
    "Bottom axis: the summed energy of one event; top axis: the same number as a fraction of 10.37 keV",
    "!Grey: the ten core channels, 1827 events — peak 3162 eV = 30.5 %, width 7.5 %",
    "Summing over channels turns the skewed 15–27 % single-channel distributions into a symmetric 7.5 % one: the position dependence cancels",
    "Green: all eleven channels, but only the 797 events where PDS2 fits, 3263 eV. That subsample is biased — its ten-channel sum is 4.8 % low — so PDS2's share can only be bracketed",
    "!Full efficiency between 31.5 % and 32.9 %: 32 ± 1 %",
    "The way to shrink the bracket is to make PDS2 fittable, not more statistics",
    "Red line: 10.37 keV — about two thirds of the energy never reaches the TESs",
], Inches(9.0), T, Inches(3.9), Inches(5.7), size=12)

# ------------------------------------------------------------------ 13 context & caveats
s = new("Where 32 % sits, and what is not yet nailed down",
        notes="Compare with the CDMS collection-efficiency note on the R37 CUTE tower: 26-41%. "
              "Caveats: Z7 only; HV bias of Z7 unknown, all numbers assume 0 V; no dIdV so loop gain "
              "and inductance unknown, inductor term dropped; PDS2 artefact; 276 events fit in no "
              "channel; official window agrees to 0.6% on the example event.")
bullets(s, [
    "The CDMS collection-efficiency note (R37, CUTE tower) reports Z1 26.2 % / 29.2 % (0 V / 50 V), Z3 40.9 % / 41.2 %, Z6 26.3 % — our 32 % for Z7 falls inside that range",
    "Their method integrates the raw pulse until it has decayed by 90 %; ours integrates the fitted pulse in closed form. On the example event the official window and the fit agree to 0.6 %",
    "!Only Z7 so far. Every other detector needs its own bias points and its own fits — the scripts take the detector number",
    "!The HV bias of Z7 during these series is not established; all numbers assume 0 V. With a bias, Luke phonons would enlarge the deposited energy and the denominator changes",
    "!No dI/dV data on MSI, so loop gain and inductance are unknown; the small-signal formula drops the inductor term (a fast, small correction) — it could not be checked",
    "PDS2's low-frequency artefact is the ±1 %: fixing it collapses the bracket to one number",
    "276 of the 2207 events (12.5 %) fit in no channel at all and are not in the histograms; whether they carry a different energy has not been checked",
], L, T, W, Inches(5.7), size=14)

# ------------------------------------------------------------------ 14 summary
s = new("Summary",
        notes="Chain: current -> power (TES equations) -> energy (closed-form integral of the fit) -> "
              "sum over channels -> 32 ± 1%. Next: other detectors, PDS2, HV bias, dIdV.")
bullets(s, [
    "The trace is a current. Turned into power with the TES equations (measured bias point per channel), its integral is the absorbed energy; the quadratic term is 2 %",
    "The energy is taken from the fitted pulse, not the data: no bias from the noisy maximum, no drift from the baseline, no integration window",
    "One channel: a 15 % wide, right-skewed distribution — event position. Summed over ten channels: symmetric, 7.5 % wide",
    "!Z7 absorbs 32 ± 1 % of a 10.37 keV event in its TESs; the ±1 % is PDS2",
    "Next: the other twelve detectors; make PDS2 fittable; settle the HV bias; get dI/dV for the loop gain and the inductor term; look at the 12.5 % of events that fit nowhere",
    "Code and figures: snolab/collection_efficiency/ (scripts, fit cache, NOTES.md with the derivation)",
], L, T, W, Inches(5.7), size=15)

# ================================================================== backups
s = new("Backup — the three versions of the power formula",
        notes="c2 = 2 is Method 1 of the CDMS note, c2 = 1 the exact small-signal result, c2 = -1 Method 2. "
              "Relative to exact: method 1 +0.58%, method 2 -1.15% in energy on the example event.")
bullets(s, [
    "P = I₀(R_L − R₀)·δI + c₂·R_L·(δI)²",
    (1, "c₂ = 2: Method 1 of the CDMS collection-efficiency note — used throughout this talk"),
    (1, "c₂ = 1: the exact small-signal expression from the two TES equations"),
    (1, "c₂ = −1: Method 2 of the same note"),
    "Because the quadratic term is 1.3 % of the energy, the three differ little: relative to the exact form, Method 1 is +0.58 % and Method 2 is −1.15 % on the example event",
    "The 15 % single-channel width and the PDS2 bracket are both far larger, so the formula choice is not the limiting uncertainty",
    "The inductor term of the full equations is neglected: it needs L and the loop gain from dI/dV, which do not exist for these series on MSI",
], L, T, W, Inches(5.7), size=15)

s = new("Backup — the official Eabs, reproduced to 0.2 %",
        notes="What the official quantity does, reverse engineered and matched to 0.2%.")
bullets(s, [
    "Trigger at bin 16383 of 32768; sample spacing 1.6 µs (52.43 ms per trace)",
    "Baseline = mean of bins 93 .. 15758, subtracted",
    "Prefilter: 5-pole 20 kHz Butterworth",
    "Window: −500 µs to +1000 µs around the trigger (bins 16071 .. 17008)",
    "Power from the same Method-1 formula, summed over the window × 1.6 µs",
    "Our reproduction matches the official Eabs to 0.2 %; the grey outlines on the histogram slides are this quantity",
    "The fitted pulse puts 98–99 % of its energy inside that window on PBS1 (84–99 % over all channels, median 98.8 %) — the window is fine for the fit; what hurts the raw trace is the drift, not the tail",
], L, T, W, Inches(5.7), size=15)

for ttl, name, note in [
    ("Backup — the full peak figure", "peak_full.png",
     "The figure of slides 5 and 6 in one piece."),
    ("Backup — 15 events, fitted current and power (PBS1)", "pulse_15events.png",
     "All 15 example events of series 24260617_063934."),
    ("Backup — 15 events, cumulative energy (PBS1)", "cum_15events.png",
     "Fit vs raw for all 15 example events."),
    ("Backup — event 30646, all channels, current and power", "allchan_pulses.png",
     "All eleven channels; sum 3419 eV = 33.0%."),
    ("Backup — event 30646, all channels, cumulative energy", "allchan_cum.png",
     "Fit vs raw for every channel; PDS2 swings by ±300 eV."),
    ("Backup — energy distribution of every channel", "hist_allchan.png",
     "All eleven panels; PDS2 marked as left out of the sum."),
]:
    s = new(ttl, notes=note, foot="collection_efficiency/results/plots/current_power_overlay/")
    pic(s, name, L, T, W, Inches(5.75))

prs.save(OUT)
print(f"saved {OUT}: {n_slide} slides")
