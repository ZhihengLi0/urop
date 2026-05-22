"""
Generate extrapolated .340 calibration files using three fitting models,
and move original files into a 原始数据/ subdirectory.
"""

import numpy as np
import os
import shutil
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings("ignore")

# ─── load ────────────────────────────────────────────────────────────────────

def load_340(filepath):
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


# ─── models ──────────────────────────────────────────────────────────────────

def model_logpoly5(logT, c0, c1, c2, c3, c4, c5):
    return c0 + c1*logT + c2*logT**2 + c3*logT**3 + c4*logT**4 + c5*logT**5

def model_vrh(T, A, B):
    return A + B * T**(-0.25)

def model_cubic(logT, A, B, C, D):
    return A + B*logT + C*logT**2 + D*logT**3


# ─── write .340 ──────────────────────────────────────────────────────────────

def write_340(filepath, serial, model_label, T_points, logR_points):
    """
    Write a Lake Shore .340 format file (Data Format 4: Log Ohms / Kelvin).
    T_points must be sorted high → low (matching original convention).
    """
    # sort high → low temperature
    order = np.argsort(T_points)[::-1]
    T_out    = T_points[order]
    logR_out = logR_points[order]

    n = len(T_out)
    T_max = T_out[0]

    lines = []
    lines.append(f"Sensor Model:   RU-1000-BF0.007")
    lines.append(f"Serial Number:\t{serial}")
    lines.append(f"Data Format:    4      (Log Ohms/Kelvin)")
    lines.append(f"SetPoint Limit: {T_max:.1f}      (Kelvin)")
    lines.append(f"Temperature coefficient:  1 (Negative)")
    lines.append(f"Number of Breakpoints:   {n}")
    lines.append("")
    lines.append("No.   Units      Temperature (K)")
    lines.append("")

    for i, (lr, t) in enumerate(zip(logR_out, T_out), start=1):
        lines.append(f"{i}\t{lr:.5f}\t{t:g}")

    with open(filepath, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  Written: {os.path.basename(filepath)}  ({n} breakpoints)")


# ─── main ─────────────────────────────────────────────────────────────────────

base_dir = "/users/9/li004628/urop/RuOx"

sensors = {
    "R31279": os.path.join(base_dir, "R31279.340"),
    "R31839": os.path.join(base_dir, "R31839.340"),
}

# extrapolation range: 0.003 K → 300 K, 400 points in log space
T_new    = np.logspace(np.log10(0.003), np.log10(300), 400)
logT_new = np.log10(T_new)

for serial, filepath in sensors.items():
    print(f"\n=== {serial} ===")
    T_cal, logR_cal = load_340(filepath)
    logT_cal = np.log10(T_cal)

    # ── fit 1: log-poly degree 5 ─────────────────────────────────────────────
    p0 = np.zeros(6); p0[0] = np.mean(logR_cal)
    popt_lp, _ = curve_fit(model_logpoly5, logT_cal, logR_cal, p0=p0, maxfev=20000)
    logR_lp = model_logpoly5(logT_new, *popt_lp)
    write_340(
        os.path.join(base_dir, f"{serial}_fit_logpoly5.340"),
        serial, "Log-polynomial degree-5",
        T_new.copy(), logR_lp.copy(),
    )

    # ── fit 2: Mott variable-range hopping ───────────────────────────────────
    popt_vrh, _ = curve_fit(model_vrh, T_cal, logR_cal,
                            p0=[np.min(logR_cal), 0.5], maxfev=20000)
    logR_vrh = model_vrh(T_new, *popt_vrh)
    write_340(
        os.path.join(base_dir, f"{serial}_fit_Mott_VRH.340"),
        serial, "Mott variable-range hopping (logR = A + B*T^-0.25)",
        T_new.copy(), logR_vrh.copy(),
    )

    # ── fit 3: cubic log-polynomial ──────────────────────────────────────────
    popt_c3, _ = curve_fit(model_cubic, logT_cal, logR_cal,
                           p0=[np.mean(logR_cal), -1.0, 0.1, 0.0], maxfev=20000)
    logR_c3 = model_cubic(logT_new, *popt_c3)
    write_340(
        os.path.join(base_dir, f"{serial}_fit_cubic_logpoly.340"),
        serial, "Cubic log-polynomial (degree-3)",
        T_new.copy(), logR_c3.copy(),
    )

# ─── move originals into 原始数据/ ──────────────────────────────────────────

raw_dir = os.path.join(base_dir, "原始数据")
os.makedirs(raw_dir, exist_ok=True)

for serial, filepath in sensors.items():
    dest = os.path.join(raw_dir, os.path.basename(filepath))
    shutil.move(filepath, dest)
    print(f"\nMoved {os.path.basename(filepath)} → 原始数据/")

print("\nDone.")
