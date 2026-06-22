# LED Calibration & Glitch Event Analysis Pipeline

Analysis of LED calibration data from the SuperCDMS CUTE R37 run (`23231213_192731`), including phonon pulse template generation, glitch event identification, and machine learning exploration.

---

## Data

- **Experiment**: SuperCDMS CUTE, R37 run
- **Data path (server)**: `/projects/standard/yanliusp/shared/data/CDMS/CUTE/R37/Raw/23231213_192731/`
- **Format**: MIDAS `.mid.gz`, 12 files total
- **Detectors**: Z1, Z2, Z3 (T3Z3), each with 11 phonon channels (T3Z3 has no PAS1)
- **Sampling rate**: 625,000 Hz (32,768 samples per event, ~52 ms)

---

## Files

| File | Description |
|------|-------------|
| `LED data_march 6th.ipynb` | Early exploration: step-by-step development of pulse selection and alignment |
| `LED data.ipynb` | Full clean pipeline: template generation, glitch identification, exponential fitting |
| `ML.ipynb` | Machine learning exploration: classifier, glitch detector, time-constant regressor |
| `template_dict.pkl` | Averaged pulse templates for each (Z, channel) |
| `glitch_event_dict.pkl` | Glitch event indices for each (Z, channel) |
| `good_event_dict.pkl` | Good event indices for each (Z, channel) |

---

## Research Process (`LED data_march 6th.ipynb`)

### Step 1: Load Data

Used `rawio.RawDataReader` to read a single `.mid.gz` file and extract waveforms from the Z3 PBS1 channel. Each event is a time-series of ADC values.

### Step 2: First Visualization (scanning from 22 ms)

- Applied amplitude threshold (`max - min > 1000`) to filter out no-pulse events
- Subtracted baseline (mean of first 5000 samples) and normalized to peak = 1
- Scanned from 22 ms to find where signal rises by more than 0.2, then aligned that point to 25.3 ms

**Issue found**: some events (e.g. event 12) were not aligning correctly because the scan started too late.

### Step 3: Improved Selection (scan from 0 ms + baseline constraint)

- Changed scan start to 0 ms to cover all possible pulse positions
- Added `abs(baseline) < 33000` filter to remove events with baseline drift (event 12 had baseline ~33200)
- Looped over all Z1/Z2/Z3 × 11 channels to produce batch plots

### Step 4: Glitch Event Discovery

Observed that some events have a negative dip just before the pulse rise (in the ~24.9–25.25 ms window). This pre-pulse dip is the signature of a glitch event.

**Glitch criterion**: after alignment, the minimum of the normalized signal in [24.9, 25.25] ms `< −0.05`

Glitch events found in F0012 (31 events):
- Z3 PFS1, PBS1, PDS1, PES1, PFS2, PBS2, PES2, PDS2: event 12
- Z3 PCS1, PBS1: event 18
- Z1 PDS2: event 29

### Step 5: Build Glitch Dictionary

Constructed a nested dictionary `glitch_event_dic[Z][channel] = [event indices]` and saved as `.npy`.

---

## Full Pipeline (`LED data.ipynb`)

### Data Loading

Reads all 12 `.mid.gz` files and merges into `all_events` (~629–775 events total). Results are cached with pickle to speed up re-runs.

### Helper Functions

**`find_rise(y_norm, x0_ms)`**
Scans from 0 ms in 0.05 ms steps, returns the time and index where the signal rises by more than 0.2 within one step.

**`preprocess_event(y_raw)`**
1. Subtract baseline (mean of first 5000 samples)
2. Check baseline offset (`abs(baseline) < 33100`)
3. Compute peak, require peak > 0
4. Auto-select quiet region for noise estimation (early pulse → use tail; late pulse → use front)
5. SNR check (`peak / noise_std > 5`)
6. Normalize to peak = 1

**`is_glitch(x_aligned, y_norm, noise_std_norm)`**
After alignment, checks the minimum in [24.9, 25.25] ms. Returns True if `< −5σ` (threshold adjustable).

### Step 2 & 3: Template Generation + Glitch/Good Dictionaries

For each (Z, channel) across all events:
1. `preprocess_event` → remove no-pulse or baseline-drifted events
2. `align_event` → shift time axis so rise lands at 25.3 ms
3. `is_glitch` → separate into glitch / good
4. `roll_to_align` → shift array on sample grid for consistent averaging
5. Average all good events → **pulse template**

Results saved as `template_dict.pkl`, `glitch_event_dict.pkl`, `good_event_dict.pkl`.

### Step 4: Exponential Fitting

Fits each template starting from sample 14000, trying a three-exponential model first, falling back to two-exponential if needed:

```
2-exp: -(amp1·exp(-t/t1) - amp1·exp(-t/t2)) + baseline
3-exp: -((amp1+amp2)·exp(-t/t1) - amp1·exp(-t/t2) - amp2·exp(-t/t3)) + baseline
```

Extracts rise time constant (t1) and decay time constants (t2, t3) for each channel, displayed as a 3×11 grid and summary table.

### Diagnostics

- **SNR distribution**: median ~130, min ~16, max ~1482 — signal quality is strong
- **Pre-pulse dip distribution**: most events cluster near 0σ; glitch events reach as low as −49σ. The two populations are clearly separated (5th percentile ~−3.4σ)

---

## Machine Learning Exploration (`ML.ipynb`)

Three models built on the same data as `LED data.ipynb`, using 9 statistical features per event: amplitude, baseline, peak, SNR, pre_min, rise time, half-decay, tail mean, has_rise.

### Model 1: Event Quality Classifier (3-class)

- **Task**: classify each (Z, channel, event) as `good` / `no_pulse` / `glitch`
- **Algorithm**: Random Forest (balanced class weights)
- **Result**: 5-fold CV F1-macro = 0.91 ± 0.13
- **Dataset**: 20,757 samples — no_pulse 19,849 / good 895 / glitch 13

### Model 2: Glitch Detector (binary)

- **Task**: distinguish good vs glitch among events with a pulse (908 samples: 895 good / 13 glitch)
- **Algorithms**: Random Forest vs MLP
- **Result**: RF achieves 100% glitch recall on the test set; MLP recall = 67%
- **Key finding**: `pre_min` (pre-pulse dip depth) is the most discriminative feature, consistent with the manual threshold approach

### Model 3: Decay Time Constant Regression

- **Task**: predict decay time constant t2 from the aligned waveform
- **Target**: t2 estimated via log-linear fit on the 5%–90% peak region (more robust than half-decay point)
- **Algorithms**: Random Forest Regressor and MLP Regressor
- **Limitation**: small labeled dataset (~13 glitch events total) limits generalization

---

## Future Plans

- **More data**: extend to additional series/runs to increase glitch sample count and improve ML generalization
- **PyTorch 1D-CNN**: train Model 3 directly on aligned waveforms (rather than statistical features) to predict t2
- **Cross-channel analysis**: investigate whether glitch events fire simultaneously across channels and detectors, and how energy is distributed
- **Automated pipeline**: package the full template generation and glitch identification workflow to support batch processing of new run data
