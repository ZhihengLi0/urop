# presentation/ — 13-min talk on the Z7 collection efficiency (September 2026)

The deck is built around one figure — a single pulse read as ADC, as current
and as power — and then follows that pulse to the whole detector. One line of
logic per slide; the figure does the talking.

| file | what |
|---|---|
| `SNOLAB_R4_collection_efficiency_20260910.pptx` | 17 slides, 16:9, English, speaker notes on every slide: 11 main + 6 backup |
| `SNOLAB_R4_collection_efficiency_20260910.pdf` | PDF export of the deck (LibreOffice, `module load libreoffice`) |
| `speech_script.md` / `.pdf` | speaker script: per slide a Chinese paragraph and the matching English one, timing per slide, backup notes, likely questions with answers, a private glossary |
| `figures/` | slide-sized crops of the result figures in `../results/plots/current_power_overlay/`, the Z7 spectrum from `../../kline_population/`, and two drawn cards (the formula, the chain) |
| `make_figures.py` | regenerates `figures/` (run inside the CDMS singularity image) |
| `build_pptx.py` | regenerates the .pptx (python-pptx, host python) |
| `build_speech_pdf.py` | speech_script.md → HTML; then headless Chromium prints the PDF |

Slide flow (11 main): title → the question (chain; area under a current is a
charge) → from current to power, from power to energy (the formula, closed form)
→ **one pulse, read three ways** (the full figure) → the height: take it from the
fit (raw max 885 vs fit 717 ADC, +23 %) → the power pulse and its area
(quadratic 1.9 %, 305 eV) → why the fit is integrated and not the data (drift,
−169 vs 277 eV) → the same event in its other channels (3419 eV = 33 %) → every
event, one channel (PBS1: 285 eV, 15 % wide, lopsided = position) → summed over
the channels (30.5 % core, 7.5 % wide, PDS2 bracket, **32 ± 1 %**) → summary and
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
