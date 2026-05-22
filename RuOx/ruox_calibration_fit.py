"""
RuOx thermometer calibration curve fitting and extrapolation.
Sensor model: RU-1000-BF0.007 (BlueFors dilution refrigerator)
Data format: Log10(Ohms) vs Temperature (K)

Three fitting models:
  1. Chebyshev polynomial in log-log space: logR = sum( a_n * T_n(x) )
  2. Mott variable-range hopping (VRH): logR = A + B * T^(-1/4)
  3. Power-law polynomial: logR = A + B*logT + C*(logT)^2 + D*(logT)^3
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit
from scipy.special import chebyt
import warnings
warnings.filterwarnings("ignore")

# ─── data loading ────────────────────────────────────────────────────────────

def load_340(filepath):
    """Parse a Lake Shore .340 calibration file (format 4: LogOhms / Kelvin)."""
    logR, T = [], []
    with open(filepath) as f:
        in_data = False
        for line in f:
            line = line.strip()
            if line.startswith("No."):
                in_data = True
                continue
            if not in_data or not line:
                continue
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                logR.append(float(parts[1]))
                T.append(float(parts[2]))
    return np.array(T), np.array(logR)


sensors = {
    "R31279": "/users/9/li004628/urop/RuOx/R31279.340",
    "R31839": "/users/9/li004628/urop/RuOx/R31839.340",
}

# ─── model definitions ───────────────────────────────────────────────────────

def model_logpoly(logT, *coeffs):
    """Polynomial in log10(T): logR = c0 + c1*logT + c2*logT^2 + ..."""
    result = np.zeros_like(logT)
    for i, c in enumerate(coeffs):
        result += c * logT**i
    return result


def model_vrh(T, A, B):
    """Mott variable-range hopping: logR = A + B * T^(-1/4)"""
    return A + B * T**(-0.25)


def model_power3(logT, A, B, C, D):
    """Cubic in log10(T) — same as logpoly(deg=3) but explicit for clarity."""
    return A + B*logT + C*logT**2 + D*logT**3


# ─── extrapolation range ─────────────────────────────────────────────────────
# Calibrated: ~0.007 K to ~102 K
# Extrapolate low end to 0.003 K and high end to 300 K

T_extrap_low  = np.logspace(np.log10(0.003), np.log10(0.007), 40)
T_extrap_high = np.logspace(np.log10(102),    np.log10(300),   40)

# ─── fit and plot ─────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(18, 14))
fig.suptitle("RuOx Calibration Curve — Fit & Extrapolation\n(BlueFors Dilution Refrigerator)",
             fontsize=14, fontweight="bold")

gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

# axes layout:  top-left = sensor 1 full view, top-right = sensor 1 zoom low-T
#               bottom-left = sensor 2 full,   bottom-right = residuals comparison
ax_s1  = fig.add_subplot(gs[0, 0])
ax_s1z = fig.add_subplot(gs[0, 1])
ax_s2  = fig.add_subplot(gs[1, 0])
ax_res = fig.add_subplot(gs[1, 1])

colors = {
    "logpoly5": "#1f77b4",
    "vrh":      "#d62728",
    "power3":   "#2ca02c",
    "data":     "k",
}

summary_lines = []

for sensor_idx, (name, filepath) in enumerate(sensors.items()):
    T_cal, logR_cal = load_340(filepath)

    # work in log10 space
    logT_cal = np.log10(T_cal)

    # sort ascending in T for clean plots
    order = np.argsort(T_cal)
    T_cal    = T_cal[order]
    logR_cal = logR_cal[order]
    logT_cal = logT_cal[order]

    # dense prediction grid spanning 0.003 – 300 K
    T_pred    = np.logspace(np.log10(0.003), np.log10(300), 1200)
    logT_pred = np.log10(T_pred)

    # ── Model 1: degree-5 log-polynomial ────────────────────────────────────
    deg = 5
    p0_lp = np.zeros(deg + 1)
    p0_lp[0] = np.mean(logR_cal)
    popt_lp, _ = curve_fit(model_logpoly, logT_cal, logR_cal,
                           p0=p0_lp, maxfev=10000)
    logR_pred_lp = model_logpoly(logT_pred, *popt_lp)
    logR_fit_lp  = model_logpoly(logT_cal,  *popt_lp)
    rmse_lp = np.sqrt(np.mean((logR_fit_lp - logR_cal)**2))

    # ── Model 2: Mott VRH ────────────────────────────────────────────────────
    p0_vrh = [np.min(logR_cal), 0.5]
    popt_vrh, _ = curve_fit(model_vrh, T_cal, logR_cal,
                            p0=p0_vrh, maxfev=10000)
    logR_pred_vrh = model_vrh(T_pred,  *popt_vrh)
    logR_fit_vrh  = model_vrh(T_cal,   *popt_vrh)
    rmse_vrh = np.sqrt(np.mean((logR_fit_vrh - logR_cal)**2))

    # ── Model 3: cubic log-polynomial ───────────────────────────────────────
    p0_p3 = [np.mean(logR_cal), -1.0, 0.1, 0.0]
    popt_p3, _ = curve_fit(model_power3, logT_cal, logR_cal,
                           p0=p0_p3, maxfev=10000)
    logR_pred_p3 = model_power3(logT_pred, *popt_p3)
    logR_fit_p3  = model_power3(logT_cal,  *popt_p3)
    rmse_p3 = np.sqrt(np.mean((logR_fit_p3 - logR_cal)**2))

    summary_lines.append(
        f"{name}:  logpoly5 RMSE={rmse_lp:.4f}  VRH RMSE={rmse_vrh:.4f}  "
        f"cubic RMSE={rmse_p3:.4f}"
    )

    # ── pick axes ────────────────────────────────────────────────────────────
    ax_main = ax_s1 if sensor_idx == 0 else ax_s2
    ax_zoom = ax_s1z if sensor_idx == 0 else None

    for ax, xlim, title_sfx in [
        (ax_main, (0.003, 300), ""),
        *( [(ax_zoom, (0.003, 0.1), " — Low-T zoom")] if ax_zoom else [] )
    ]:
        ax.plot(T_cal, logR_cal, ".", color=colors["data"],
                ms=3, label="Calibration data", zorder=5)

        ax.plot(T_pred, logR_pred_lp,
                color=colors["logpoly5"], lw=1.8,
                label=f"Log-poly deg-5  (RMSE={rmse_lp:.4f})", zorder=3)
        ax.plot(T_pred, logR_pred_vrh,
                color=colors["vrh"], lw=1.8, ls="--",
                label=f"Mott VRH  (RMSE={rmse_vrh:.4f})", zorder=3)
        ax.plot(T_pred, logR_pred_p3,
                color=colors["power3"], lw=1.8, ls="-.",
                label=f"Cubic log-poly  (RMSE={rmse_p3:.4f})", zorder=3)

        # shade extrapolation regions
        cal_lo, cal_hi = T_cal.min(), T_cal.max()
        ax.axvspan(xlim[0], cal_lo, alpha=0.10, color="grey", label="Extrapolation")
        ax.axvspan(cal_hi,  xlim[1], alpha=0.10, color="grey")
        ax.axvline(cal_lo, color="grey", lw=0.8, ls=":")
        ax.axvline(cal_hi, color="grey", lw=0.8, ls=":")

        ax.set_xscale("log")
        ax.set_xlim(xlim)
        ax.set_xlabel("Temperature (K)")
        ax.set_ylabel("Log$_{10}$(R / Ω)")
        ax.set_title(f"Sensor {name}{title_sfx}")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, which="both", alpha=0.3)

    # ── residuals panel (sensor 2 omitted from zoom, put both in residuals) ──
    resid_lp  = logR_fit_lp  - logR_cal
    resid_vrh = logR_fit_vrh - logR_cal
    resid_p3  = logR_fit_p3  - logR_cal

    ls = "-" if sensor_idx == 0 else "--"
    lbl = f"{name} "
    ax_res.plot(T_cal, resid_lp,  color=colors["logpoly5"], lw=1.3, ls=ls,
                label=f"{lbl}log-poly5")
    ax_res.plot(T_cal, resid_vrh, color=colors["vrh"],      lw=1.3, ls=ls,
                label=f"{lbl}VRH")
    ax_res.plot(T_cal, resid_p3,  color=colors["power3"],   lw=1.3, ls=ls,
                label=f"{lbl}cubic")

ax_res.axhline(0, color="k", lw=0.8)
ax_res.set_xscale("log")
ax_res.set_xlabel("Temperature (K)")
ax_res.set_ylabel("Residual  (log$_{10}$Ω)")
ax_res.set_title("Fit Residuals — Both Sensors")
ax_res.legend(fontsize=6.5, ncol=2)
ax_res.grid(True, which="both", alpha=0.3)

# ─── print fit quality ────────────────────────────────────────────────────────
print("\nFit quality (RMSE in log10 Ohm units):")
for line in summary_lines:
    print(" ", line)

out_png = "/users/9/li004628/urop/RuOx/ruox_calibration_fit.png"
plt.savefig(out_png, dpi=150, bbox_inches="tight")
print(f"\nFigure saved: {out_png}")
plt.show()
