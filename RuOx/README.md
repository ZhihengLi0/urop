# RuOx Thermometer Calibration Curve Extension

**Project:** SuperCDMS Dark Matter Experiment — BlueFors XLD Dilution Refrigerator  
**Sensors:** R31279 (MXC-Flange, C6) · R31839 (MXC-Flange2, C7)  
**Date:** May 26, 2026  
**Author:** Zhiheng Li

---

## Objective

The factory-supplied Lake Shore `.340` calibration files for both RuOx sensors cover only the range **7 mK – 102 K**. This work extends the calibration curves to span the full operational range:

- **Lower bound:** 5 mK (base temperature of the mixing chamber)
- **Upper bound:** 300 K (room temperature / warm-up endpoint)

The extended files conform to the Lake Shore `.340` format (Data Format 4: Log Ohms / Kelvin) and are directly loadable by the temperature controller.

---

## Repository Structure

```
RuOx/
├── README.md                       ← this file
├── ruox_calibration_fit.py         ← fitting script (single sensor, exploratory)
├── generate_fitted_340.py          ← production script (generates all 6 .340 files)
├── ruox_calibration_fit.png        ← calibration curve plot
├── origin data/                    ← factory .340 files (raw)
├── R31279/
│   ├── R31279_fit_logpoly5.340
│   ├── R31279_fit_PCHIP.340        ← recommended for production use
│   └── R31279_fit_cubic_logpoly.340
└── R31839/
    ├── R31839_fit_logpoly5.340
    ├── R31839_fit_PCHIP.340        ← recommended for production use
    └── R31839_fit_cubic_logpoly.340
```

---

## Constraints

### Breakpoint Budget

The Lake Shore controller accepts a maximum of **198 breakpoints** per file. Points were distributed to ensure near-uniform spacing on a logarithmic temperature axis:

| Segment | Range | Points | Spacing (decades/step) |
|---------|-------|--------|------------------------|
| Low-T   | 5 mK – 100 K  | 178 | ~0.0243 |
| High-T  | 100 K – 300 K | 20  | ~0.0251 |
| **Total** | **5 mK – 300 K** | **198** | — |

The 294 K room-temperature anchor point was explicitly forced into the high-T grid.

### Monotonicity

The `.340` format requires resistance to increase **strictly monotonically** as temperature decreases (negative temperature coefficient). The generation script enforces this by comparing formatted values to 5 decimal places and dropping any breakpoint that violates strict monotonicity.

---

## Room-Temperature Anchor Points

Two anchor points were measured at room temperature (294 K) using the BlueFors thermometry unit and appended to the calibration datasets before fitting:

| Sensor | R at 294 K | log₁₀(R / Ω) |
|--------|-----------|---------------|
| R31279 | 1012.9 Ω | 3.00557 |
| R31839 | 1016.9 Ω | 3.00727 |

Both values are lower than the resistance at 102 K (the factory calibration upper limit), confirming globally monotone behavior across 5 mK – 294 K for both sensors.

> **Note on R31279:** An earlier measurement gave 1102.5 Ω at 294 K — higher than the 102 K value (~1025 Ω), which would imply a non-physical positive temperature coefficient. After re-measurement, 1012.9 Ω was confirmed and used in all fits.

---

## Fitting Models

Three models were implemented and compared:

### Model 1 — Log-polynomial, degree 5

$$\log_{10} R = \sum_{n=0}^{5} c_n \left(\log_{10} T\right)^n$$

Fitted via `scipy.optimize.curve_fit`. Smooth global interpolation and extrapolation.  
RMSE: ~0.0009 (R31279), ~0.0007 (R31839).

### Model 2 — PCHIP spline + Mott VRH extrapolation *(recommended)*

- **Within calibration range:** `PchipInterpolator` in log₁₀(T) space — passes exactly through every calibration point while preserving local monotonicity.
- **Below calibration minimum:** Mott Variable-Range Hopping (VRH) model,

$$\log_{10} R = A + B \cdot T^{-1/4}$$

fitted to the 20 lowest-temperature calibration points. Physically motivated by hopping conductance in disordered systems at ultra-low temperatures.

RMSE on calibration data: 0.0000 (exact interpolation).

### Model 3 — Cubic log-polynomial

$$\log_{10} R = A + B\log_{10}T + C(\log_{10}T)^2 + D(\log_{10}T)^3$$

Smooth, stable lower-degree global polynomial.  
RMSE: ~0.0023 (R31279), ~0.0014 (R31839).

### Comparison

| Model | R31279 RMSE | R31839 RMSE | Calibration range | Low-T extrapolation |
|-------|-------------|-------------|-------------------|---------------------|
| Log-poly deg-5 | 0.0009 | 0.0007 | Smooth fit | Polynomial |
| **PCHIP + Mott** | **0.0000** | **0.0000** | **Exact interpolation** | **Mott VRH (physical)** |
| Cubic log-poly | 0.0023 | 0.0014 | Smooth fit | Polynomial |

**PCHIP + Mott is recommended** for production use: it preserves all calibration data exactly and uses a physically grounded model for sub-mK extrapolation.

---

## Output Files

All six `.340` files were validated for:

- Correct header format (Data Format 4)
- Strictly monotone log₁₀(R) as T decreases
- 294 K anchor point present and correctly placed
- Breakpoint count ≤ 198

---

## Debugging Notes

| Issue | Root Cause | Resolution |
|-------|-----------|------------|
| Non-monotone calibration for R31279 | Erroneous 294 K anchor (1102.5 Ω > 102 K value) | Re-measured; corrected to 1012.9 Ω |
| Monotone filter removing too many points | Floating-point equality at 5 d.p. | Compare formatted strings instead of raw floats |
| PCHIP residuals non-zero at calibration points | Extrapolate mode perturbing interior | Separated interior (PCHIP) and exterior (Mott) explicitly |
| Output grid missing 294 K | logspace endpoint rounding | Force 294.0 K into grid with `np.unique` + `np.append` |
| Assertion error on grid size | Unique call collapsing near-duplicate points | Adjusted logspace bounds to avoid collision |

---

## Environment

| Component | Details |
|-----------|---------|
| Language | Python 3.9 (Anaconda) |
| Key libraries | NumPy, SciPy (`curve_fit`, `PchipInterpolator`), Matplotlib |
| Platform | University of Minnesota MSI — Agate cluster (OnDemand Jupyter) |

---

## Next Steps

- Upload `*_fit_PCHIP.340` files to the Lake Shore controller and verify temperature readout during the next cooldown
- Compare controller-displayed temperature with CMN thermometer readings in the 5–100 mK range
- If significant deviation is observed below 10 mK, refit the Mott VRH segment using only sub-10 mK calibration points
