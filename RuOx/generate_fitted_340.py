"""
Generate extrapolated .340 calibration files using three fitting models.
Reads original calibration data from 原始数据/ subdirectory.
Outputs fitted files into per-sensor subdirectories (R31279/, R31839/).

Models:
  1. Log-polynomial degree-5 (logR vs logT)
  2. Mott VRH — piecewise linear in T^{-1/4} vs logR space (3 segments)
  3. Cubic log-polynomial (logR vs logT)
"""

import numpy as np
import os
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = "/users/9/li004628/urop/RuOx"
RAW_DIR  = os.path.join(BASE_DIR, "origin data")

# Room-temperature measurement for R31279 (C6: MXC-Flange, measured at 294 K)
ROOM_TEMP_POINTS = {
    "R31279": (294.0, np.log10(1102.5)),   # 1.1025 kΩ → log10(1102.5 Ω)
}

# Mott piecewise breakpoints (K) — segments: T<1, 1≤T<10, T≥10
VRH_BREAKS = [1.0, 10.0, 100.0]

# Output temperature grid: 0.003 K → 300 K, 198 log-spaced points
T_NEW    = np.logspace(np.log10(0.003), np.log10(300), 198)
logT_NEW = np.log10(T_NEW)


# ─── helpers ─────────────────────────────────────────────────────────────────

def load_340(filepath):
    """Parse a Lake Shore .340 file (format 4: Log Ohms / Kelvin)."""
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


def write_340(filepath, serial, T_points, logR_points, setpoint_limit=300.0):
    """Write a Lake Shore .340 format file, sorted high → low temperature."""
    order = np.argsort(T_points)[::-1]
    T_out    = T_points[order]
    logR_out = logR_points[order]
    n = len(T_out)

    lines = [
        "Sensor Model:   RU-1000-BF0.007",
        f"Serial Number:\t{serial}",
        "Data Format:    4      (Log Ohms/Kelvin)",
        f"SetPoint Limit: {setpoint_limit:.1f}      (Kelvin)",
        "Temperature coefficient:  1 (Negative)",
        f"Number of Breakpoints:   {n}",
        "",
        "No.   Units      Temperature (K)",
        "",
    ]
    for i, (lr, t) in enumerate(zip(logR_out, T_out), start=1):
        lines.append(f"{i}\t{lr:.5f}\t{t:g}")

    with open(filepath, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Written: {os.path.basename(filepath)}  ({n} breakpoints)")


# ─── model functions ─────────────────────────────────────────────────────────

def model_logpoly5(logT, c0, c1, c2, c3, c4, c5):
    return c0 + c1*logT + c2*logT**2 + c3*logT**3 + c4*logT**4 + c5*logT**5


def model_cubic(logT, A, B, C, D):
    return A + B*logT + C*logT**2 + D*logT**3


def fit_vrh_piecewise(T_cal, logR_cal, T_breaks=VRH_BREAKS):
    """
    Piecewise linear fit in Mott variable space: x = T^{-1/4} vs logR.
    Segments are defined by T_breaks (sorted ascending).
    Returns a callable predict(T_new) -> logR_new.
    """
    order = np.argsort(T_cal)
    T_s = T_cal[order]
    R_s = logR_cal[order]
    x_s = T_s ** (-0.25)

    # Build segment edges clipped to data range
    inner = [b for b in T_breaks if T_s[0] < b < T_s[-1]]
    edges = [T_s[0]] + inner + [T_s[-1]]

    segments = []
    for j in range(len(edges) - 1):
        lo, hi = edges[j], edges[j + 1]
        mask = (T_s >= lo) & (T_s <= hi)
        if mask.sum() < 2:
            continue
        coeffs = np.polyfit(x_s[mask], R_s[mask], 1)  # [slope, intercept]
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


# ─── main ────────────────────────────────────────────────────────────────────

sensors = ["R31279", "R31839"]

for serial in sensors:
    print(f"\n=== {serial} ===")

    raw_path = os.path.join(RAW_DIR, f"{serial}.340")
    T_cal, logR_cal = load_340(raw_path)

    # Append room-temperature anchor point if available for this sensor
    if serial in ROOM_TEMP_POINTS:
        T_rt, logR_rt = ROOM_TEMP_POINTS[serial]
        T_cal    = np.append(T_cal,    T_rt)
        logR_cal = np.append(logR_cal, logR_rt)
        print(f"  Added room-T point: {T_rt} K, logR={logR_rt:.5f}")

    # Sort ascending for fitting
    order = np.argsort(T_cal)
    T_cal    = T_cal[order]
    logR_cal = logR_cal[order]
    logT_cal = np.log10(T_cal)

    out_dir = os.path.join(BASE_DIR, serial)
    os.makedirs(out_dir, exist_ok=True)

    T_max_cal = T_cal.max()
    setpoint  = max(300.0, T_max_cal)

    # ── Model 1: log-polynomial degree-5 ─────────────────────────────────────
    p0 = np.zeros(6); p0[0] = np.mean(logR_cal)
    popt_lp, _ = curve_fit(model_logpoly5, logT_cal, logR_cal, p0=p0, maxfev=20000)
    logR_lp = model_logpoly5(logT_NEW, *popt_lp)
    rmse_lp = np.sqrt(np.mean((model_logpoly5(logT_cal, *popt_lp) - logR_cal)**2))
    write_340(
        os.path.join(out_dir, f"{serial}_fit_logpoly5.340"),
        serial, T_NEW.copy(), logR_lp.copy(), setpoint_limit=setpoint,
    )
    print(f"    logpoly5 RMSE = {rmse_lp:.5f}")

    # ── Model 2: piecewise Mott VRH ───────────────────────────────────────────
    vrh_predict = fit_vrh_piecewise(T_cal, logR_cal)
    logR_vrh = vrh_predict(T_NEW)
    logR_vrh_fit = vrh_predict(T_cal)
    rmse_vrh = np.sqrt(np.mean((logR_vrh_fit - logR_cal)**2))
    write_340(
        os.path.join(out_dir, f"{serial}_fit_Mott_VRH.340"),
        serial, T_NEW.copy(), logR_vrh.copy(), setpoint_limit=setpoint,
    )
    print(f"    Mott VRH (piecewise) RMSE = {rmse_vrh:.5f}")

    # ── Model 3: cubic log-polynomial ────────────────────────────────────────
    popt_c3, _ = curve_fit(model_cubic, logT_cal, logR_cal,
                           p0=[np.mean(logR_cal), -1.0, 0.1, 0.0], maxfev=20000)
    logR_c3 = model_cubic(logT_NEW, *popt_c3)
    rmse_c3 = np.sqrt(np.mean((model_cubic(logT_cal, *popt_c3) - logR_cal)**2))
    write_340(
        os.path.join(out_dir, f"{serial}_fit_cubic_logpoly.340"),
        serial, T_NEW.copy(), logR_c3.copy(), setpoint_limit=setpoint,
    )
    print(f"    cubic logpoly RMSE = {rmse_c3:.5f}")

print("\nDone.")
