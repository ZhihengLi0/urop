"""
RuOx thermometer calibration curve fitting and extrapolation.
Sensor model: RU-1000-BF0.007 (BlueFors dilution refrigerator)
Data format: Log10(Ohms) vs Temperature (K)

Three fitting models:
  1. Log-polynomial degree-5: logR = sum( c_n * logT^n )
  2. Mott VRH (piecewise): logR = A_i + B_i * T^{-1/4}  per segment
  3. Cubic log-polynomial: logR = A + B*logT + C*logT^2 + D*logT^3
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = "/users/9/li004628/urop/RuOx"
RAW_DIR  = BASE_DIR + "/origin data"

# Room-temperature anchor point for R31279 (C6: MXC-Flange, measured at 294 K)
ROOM_TEMP_POINTS = {
    "R31279": (294.0, np.log10(1012.9)),   # 1.0129 kΩ → log10(1012.9 Ω)
    "R31839": (294.0, np.log10(1016.9)),   # 1.0169 kΩ → log10(1016.9 Ω)
}

VRH_BREAKS = [1.0, 10.0]   # Mott piecewise segment boundaries (K)


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
    "R31279": f"{RAW_DIR}/R31279.340",
    "R31839": f"{RAW_DIR}/R31839.340",
}


# ─── model definitions ───────────────────────────────────────────────────────

def model_logpoly(logT, *coeffs):
    result = np.zeros_like(logT)
    for i, c in enumerate(coeffs):
        result += c * logT**i
    return result


def model_power3(logT, A, B, C, D):
    return A + B*logT + C*logT**2 + D*logT**3


def fit_vrh_piecewise(T_cal, logR_cal, T_breaks=VRH_BREAKS):
    """
    Piecewise linear fit in Mott variable space: x = T^{-1/4} vs logR.
    Returns a callable predict(T_new) -> logR_new.
    """
    order = np.argsort(T_cal)
    T_s = T_cal[order]
    R_s = logR_cal[order]
    x_s = T_s ** (-0.25)

    inner = [b for b in T_breaks if T_s[0] < b < T_s[-1]]
    edges = [T_s[0]] + inner + [T_s[-1]]

    segments = []
    for j in range(len(edges) - 1):
        lo, hi = edges[j], edges[j + 1]
        mask = (T_s >= lo) & (T_s <= hi)
        if mask.sum() < 2:
            continue
        coeffs = np.polyfit(x_s[mask], R_s[mask], 1)
        segments.append((lo, hi, coeffs))

    def predict(T_new):
        T_arr = np.asarray(T_new, dtype=float)
        x_arr = T_arr ** (-0.25)
        result = np.empty_like(T_arr)
        for i in range(len(T_arr)):
            Ti = T_arr[i]
            if Ti <= segments[0][0]:
                result[i] = np.polyval(segments[0][2], x_arr[i])
            elif Ti >= segments[-1][1]:
                result[i] = np.polyval(segments[-1][2], x_arr[i])
            else:
                for lo, hi, coeffs in segments:
                    if lo <= Ti <= hi:
                        result[i] = np.polyval(coeffs, x_arr[i])
                        break
        return result

    return predict


# ─── plot setup ──────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(18, 14))
fig.suptitle(
    "RuOx Calibration Curve — Fit & Extrapolation\n(BlueFors Dilution Refrigerator)",
    fontsize=14, fontweight="bold",
)
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_s1  = fig.add_subplot(gs[0, 0])
ax_s1z = fig.add_subplot(gs[0, 1])
ax_s2  = fig.add_subplot(gs[1, 0])
ax_res = fig.add_subplot(gs[1, 1])

colors = {
    "logpoly5": "#1f77b4",
    "vrh":      "#d62728",
    "power3":   "#2ca02c",
    "data":     "k",
    "room_T":   "#ff7f0e",
}

summary_lines = []

for sensor_idx, (name, filepath) in enumerate(sensors.items()):
    T_cal, logR_cal = load_340(filepath)

    # Append room-temperature anchor point if available
    room_T_marker = None
    if name in ROOM_TEMP_POINTS:
        T_rt, logR_rt = ROOM_TEMP_POINTS[name]
        room_T_marker = (T_rt, logR_rt)
        T_cal    = np.append(T_cal,    T_rt)
        logR_cal = np.append(logR_cal, logR_rt)

    order = np.argsort(T_cal)
    T_cal    = T_cal[order]
    logR_cal = logR_cal[order]
    logT_cal = np.log10(T_cal)

    T_pred    = np.logspace(np.log10(0.005), np.log10(300), 1200)
    logT_pred = np.log10(T_pred)

    # ── Model 1: degree-5 log-polynomial ─────────────────────────────────────
    deg = 5
    p0_lp = np.zeros(deg + 1); p0_lp[0] = np.mean(logR_cal)
    popt_lp, _ = curve_fit(model_logpoly, logT_cal, logR_cal,
                           p0=p0_lp, maxfev=10000)
    logR_pred_lp = model_logpoly(logT_pred, *popt_lp)
    logR_fit_lp  = model_logpoly(logT_cal,  *popt_lp)
    rmse_lp = np.sqrt(np.mean((logR_fit_lp - logR_cal)**2))

    # ── Model 2: piecewise Mott VRH ───────────────────────────────────────────
    vrh_predict  = fit_vrh_piecewise(T_cal, logR_cal)
    logR_pred_vrh = vrh_predict(T_pred)
    logR_fit_vrh  = vrh_predict(T_cal)
    rmse_vrh = np.sqrt(np.mean((logR_fit_vrh - logR_cal)**2))

    # ── Model 3: cubic log-polynomial ────────────────────────────────────────
    p0_p3 = [np.mean(logR_cal), -1.0, 0.1, 0.0]
    popt_p3, _ = curve_fit(model_power3, logT_cal, logR_cal,
                           p0=p0_p3, maxfev=10000)
    logR_pred_p3 = model_power3(logT_pred, *popt_p3)
    logR_fit_p3  = model_power3(logT_cal,  *popt_p3)
    rmse_p3 = np.sqrt(np.mean((logR_fit_p3 - logR_cal)**2))

    summary_lines.append(
        f"{name}:  logpoly5 RMSE={rmse_lp:.4f}  "
        f"VRH-piecewise RMSE={rmse_vrh:.4f}  cubic RMSE={rmse_p3:.4f}"
    )

    # ── pick axes ─────────────────────────────────────────────────────────────
    ax_main = ax_s1 if sensor_idx == 0 else ax_s2
    ax_zoom = ax_s1z if sensor_idx == 0 else None

    for ax, xlim, title_sfx in [
        (ax_main, (0.003, 300), ""),
        *([(ax_zoom, (0.005, 0.1), " — Low-T zoom")] if ax_zoom else []),
    ]:
        ax.plot(T_cal, logR_cal, ".", color=colors["data"],
                ms=3, label="Calibration data", zorder=5)

        # Mark room-temperature point distinctly
        if room_T_marker and ax is ax_main:
            ax.plot(*room_T_marker, "D", color=colors["room_T"], ms=7, zorder=6,
                    label=f"Room-T anchor ({room_T_marker[0]:.0f} K)")

        ax.plot(T_pred, logR_pred_lp,
                color=colors["logpoly5"], lw=1.8,
                label=f"Log-poly deg-5  (RMSE={rmse_lp:.4f})", zorder=3)
        ax.plot(T_pred, logR_pred_vrh,
                color=colors["vrh"], lw=1.8, ls="--",
                label=f"Mott VRH piecewise  (RMSE={rmse_vrh:.4f})", zorder=3)
        ax.plot(T_pred, logR_pred_p3,
                color=colors["power3"], lw=1.8, ls="-.",
                label=f"Cubic log-poly  (RMSE={rmse_p3:.4f})", zorder=3)

        # Shade extrapolation regions (outside calibration range, excl. room-T anchor)
        orig_T_min = T_cal[0] if name not in ROOM_TEMP_POINTS else T_cal[:-1].min()
        orig_T_max = T_cal[-1] if name not in ROOM_TEMP_POINTS else T_cal[-2]
        ax.axvspan(xlim[0], orig_T_min, alpha=0.10, color="grey", label="Extrapolation")
        ax.axvspan(orig_T_max, xlim[1], alpha=0.10, color="grey")
        ax.axvline(orig_T_min, color="grey", lw=0.8, ls=":")
        ax.axvline(orig_T_max, color="grey", lw=0.8, ls=":")

        ax.set_xscale("log")
        ax.set_xlim(xlim)
        ax.set_xlabel("Temperature (K)")
        ax.set_ylabel("Log$_{10}$(R / Ω)")
        ax.set_title(f"Sensor {name}{title_sfx}")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, which="both", alpha=0.3)

    # ── residuals ─────────────────────────────────────────────────────────────
    resid_lp  = logR_fit_lp  - logR_cal
    resid_vrh = logR_fit_vrh - logR_cal
    resid_p3  = logR_fit_p3  - logR_cal

    ls = "-" if sensor_idx == 0 else "--"
    lbl = f"{name} "
    ax_res.plot(T_cal, resid_lp,  color=colors["logpoly5"], lw=1.3, ls=ls,
                label=f"{lbl}log-poly5")
    ax_res.plot(T_cal, resid_vrh, color=colors["vrh"],      lw=1.3, ls=ls,
                label=f"{lbl}VRH-piecewise")
    ax_res.plot(T_cal, resid_p3,  color=colors["power3"],   lw=1.3, ls=ls,
                label=f"{lbl}cubic")

ax_res.axhline(0, color="k", lw=0.8)
ax_res.set_xscale("log")
ax_res.set_xlabel("Temperature (K)")
ax_res.set_ylabel("Residual  (log$_{10}$Ω)")
ax_res.set_title("Fit Residuals — Both Sensors")
ax_res.legend(fontsize=6.5, ncol=2)
ax_res.grid(True, which="both", alpha=0.3)

print("\nFit quality (RMSE in log10 Ohm units):")
for line in summary_lines:
    print(" ", line)

out_png = f"{BASE_DIR}/ruox_calibration_fit.png"
plt.savefig(out_png, dpi=150, bbox_inches="tight")
print(f"\nFigure saved: {out_png}")
plt.show()
