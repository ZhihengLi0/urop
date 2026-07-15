#!/usr/bin/env python3
"""Render the 2-exp model equation as clean math typography (matplotlib mathtext)
for slide 3, so it doesn't read like source code."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
NAVY = "#1F3864"
GRAY = "#555555"

fig = plt.figure(figsize=(9.2, 1.35))
fig.patch.set_alpha(0.0)
eq = (r"$y(t)=A\left[\,e^{-(t-t_0)/\tau_{\mathrm{fall}}}"
      r"-e^{-(t-t_0)/\tau_{\mathrm{rise}}}\,\right]+b$")
fig.text(0.5, 0.66, eq, ha="center", va="center", fontsize=27, color=NAVY)
fig.text(0.5, 0.16,
         r"$t_0=\mathrm{pretrigger}$, free within $16050\pm3000$ samples"
         r"$\quad$($\tau_{\mathrm{rise}},\,\tau_{\mathrm{fall}}$: rise / fall time)",
         ha="center", va="center", fontsize=15, color=GRAY)
fig.savefig(os.path.join(OUT, "formula_2exp.png"), dpi=220,
            bbox_inches="tight", transparent=True)
print("saved formula_2exp.png")
