# presentation/ — 13-min talk on the Z7 collection efficiency (September 2026)

| file | what |
|---|---|
| `SNOLAB_R4_collection_efficiency_20260910.pptx` | 22 slides, 16:9, English, speaker notes on every slide: 14 main + 8 backup |
| `SNOLAB_R4_collection_efficiency_20260910.pdf` | PDF export of the deck (LibreOffice, `module load libreoffice`) |
| `speech_script.md` / `.pdf` | speaker script: per slide a Chinese paragraph and the matching English one, timing per slide, backup notes, likely questions with answers, a private glossary |
| `figures/` | slide-sized crops of the result figures in `../results/plots/current_power_overlay/`, the Z7 spectrum from `../../kline_population/`, and two drawn cards (the formula, the chain) |
| `make_figures.py` | regenerates `figures/` (run inside the CDMS singularity image) |
| `build_pptx.py` | regenerates the .pptx (python-pptx, host python) |
| `build_speech_pdf.py` | speech_script.md → HTML; then headless Chromium prints the PDF |

Slide flow (14 main): title → the question and why the trace alone does not
answer it (chain) → the events (Z7 spectrum, 2207 K-line events, 30 series) →
from current to power (the formula, closed-form integral, PBS1 bias point) →
**one pulse read three ways, the height** (raw max 885 vs fit 717 ADC, +23 %) →
the power and its area (quadratic term 1.9 % of peak, 305 eV) → every event:
fit the current, convert to power → why the fit is integrated and not the raw
trace (drift, −169 vs 277 eV) → one event, all channels (3419 eV = 33.0 %) →
every event, one channel (PBS1: peak 285 eV, 15 % wide, right-skewed) → every
channel (peaks must not be added; PDS2 fits 42 %) → summed over channels
(30.5 % core, bracket 31.5–32.9 %, **32 ± 1 %**) → where 32 % sits (R37 CUTE
26–41 %) and what is not nailed down (Z7 only, HV bias, no dI/dV, PDS2, the
12.5 % of events that fit nowhere) → summary.

Backup (8): the three formula versions (c₂ = 2 / 1 / −1, ±1 %), the official
Eabs reproduced to 0.2 %, and the six full result figures.

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
