# presentation/ — 13-min talk on the Z7 collection efficiency (September 2026)

The deck is built around one figure — a single pulse read as ADC, as current
and as power — and then follows that pulse to the whole detector. One line of
logic per slide; the figure does the talking.

| file | what |
|---|---|
| `SNOLAB_R4_collection_efficiency_20260910.pptx` | 17 slides, 16:9, English, speaker notes on every slide: 11 main + 6 backup |
| `SNOLAB_R4_collection_efficiency_20260910.pdf` | PDF export of the deck (LibreOffice, `module load libreoffice`) |
| `..._zh.pptx` / `..._zh.pdf` | the same deck slide for slide in Chinese, for reading (`build_pptx_zh.py`); figures unchanged |
| `..._en_zh_side_by_side.pdf` | both decks on one page per slide, English left and Chinese right, for comparing |
| `speech_script.md` / `.pdf` | speaker script: per slide a Chinese paragraph and the matching English one, timing per slide, backup notes, likely questions with answers, a private glossary |
| `figures/` | slide-sized crops of the result figures in `../results/plots/current_power_overlay/`, the Z7 spectrum from `../../kline_population/`, and two drawn cards (the formula, the chain) |
| `make_figures.py` | regenerates `figures/` (run inside the CDMS singularity image) |
| `build_pptx.py` | regenerates the .pptx (python-pptx, host python) |
| `build_speech_pdf.py` | speech_script.md → HTML; then headless Chromium prints the PDF |

Slide flow (12 main): title → the main idea (the chain of steps) → the formula and the two numbers it needs (Method 1 of the CDMS note, with
Method 2 mentioned; closed form, bias point)
→ **example: one pulse** (the full figure; the fit is on the 100 kHz low-passed trace) → the height: take it from the
fit (raw max 885 vs fit 717 ADC, +23 %) → the power pulse and its area
(quadratic 1.9 %, 305 eV) → why the fit is integrated and not the data (drift,
−169 vs 277 eV) → the same event in its other channels (3419 eV = 33 %) → every
event, one channel (PBS1: 285 eV, 15 % wide, lopsided = position) → summed over
the channels (10 channels, **30.5 %**, σ/μ = 7.5 % as the uncertainty; PDS2 left out) → summary and
what is open (Z7 only, HV bias, no dI/dV, PDS2, 12.5 % of events fit nowhere).

Backup (6): the Z7 spectrum, the three formula versions and the official Eabs,
and four full result figures.

Every number on the slides is copied from `../results/plots/current_power_overlay/*.txt`
and `../NOTES.md`; nothing is recomputed in this directory.

Rebuild:

```bash
SIF=/projects/standard/yanliusp/shared/singularity_images/cdmsfull_V07-02-00.sif
singularity exec -B "$HOME" $SIF python3 make_figures.py
python3 build_pptx.py
module load libreoffice && libreoffice --headless --convert-to pdf SNOLAB_R4_collection_efficiency_20260910.pptx
python3 build_speech_pdf.py speech_script.md speech_script.html
chromium-browser --headless --no-sandbox --print-to-pdf=speech_script.pdf --no-pdf-header-footer speech_script.html
```

## Revision after Prof. Liu's annotations (September 2026)

The annotated copy is `纠正意见.pdf` (it marks the 17-slide version, so its page
numbers from 3 on are one lower than the current deck). Applied:

- slide 2: "for detectors operated at 0 V (no NTL effect)" on the definition;
  energy summed over all channels; the chain uses δP; the two lines about the
  current pulse and its area removed; the sample is "from SNOLAB R4";
- slide 4: δP throughout; I₀(R_L−R₀) written as 0.45 µV; the −∞..+∞ line removed;
- slide 5: titled "Example: one pulse", the subtitle's description in bold, and a
  line stating the fit is done on the 100 kHz low-passed trace, not on raw;
- slide 8: the raw current of the two events added above their cumulative
  energy (`zip7_24260617_063934_raw_and_cumulative_PBS1_slide.png`);
- slide 9: "remember it" removed.

The derivation slide (circuit plus five steps) was taken out again on request:
the derivation is for the speaker to know, not to present. `figures/circuit.png`
and `figures/derivation.png` are still generated as a reference, and the
speaker script answers it under Likely questions (Q10, Q11).
