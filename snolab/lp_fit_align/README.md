# lp_fit_align — 100 kHz Low-Pass + free-pretrigger fit + shift align

Pipeline on the raw PTOF-selected event cache (`raw_without_filter`, schema
`raw_ptof_selected_event_v1`, no processing at all in the cache itself):

```
raw MIDAS trace
  → 100 kHz 4th-order Butterworth low-pass (scipy sosfilt, steady-state init)
  → baseline subtract (median of samples 2000–12000)
  → normalize by GLOBAL trace peak (no peak-window restriction)
  → 2-exp fit  y = A(e^(−t/τ_fall) − e^(−t/τ_rise)),
    ALL 5 params free incl. pretrigger (bounds 16050±3000, maxfev=10000)
  → fit_ok := amp>0 and 0<t_rise<t_fall
  → NRMSE := RMS(fit residual)/fitted pulse peak — RECORDED ONLY, no cut
  → align := shift the MEASURED LP trace by (fitted pretrigger − 16050)
```

The fit is FREE (pretrigger is a fit parameter); pinning to 16050 happens only
at the align/display stage — never inside the fit.

## Layout

```
scripts/                 pipeline + plotting code (in git)
results/plots/<type>/    one sub-dir per figure type, all zips together
results/stats/           per-zip JSON summaries (in git)
run/checkpoints/zip{N}/  per-series fit-parameter pkl (index-aligned with the
                         raw cache's event_numbers_ch; analyses never refit)
run/logs/                SLURM logs
```

## Figure types (`results/plots/`)

| sub-dir | 中文说明 | what it shows |
|---|---|---|
| `aligned_overlay/` | 平移对齐后的**实测**波形叠加 + 均值（统一起点 16050） | shift-aligned measured LP traces (blue, ≤200/chan) + mean of all fit_ok events (red) |
| `fitted_curves_overlay/` | 拟合光滑曲线扇形图：形状参数代回解析式，起点统一 16050、峰高归一 | smooth fitted 2-exp curves at common pretrigger, peak-normalized — shape distribution only |
| `raw_vs_fit_examples/` | 每 zip 6 例：未滤波 raw（灰）+ LP（蓝）+ 拟合（红）——看噪声相对主脉冲的大小 | best-NRMSE example per channel; noise-vs-pulse visual check |
| `fit_examples/` | 每通道前 3 个 fit_ok 事件的 LP vs 拟合——检查拟合质量（不挑好的，如实展示） | fit-quality check, examples NOT quality-selected |
| `nrmse/` | NRMSE 分布（对数轴）：双峰 = 好拟合 vs 噪声触发，谷 = cut 阈值候选 | log-binned NRMSE distribution of fit_ok events |
| `pretrigger/` | 拟合出的自由 pretrigger 分布（真实触发点，参考 16050） | fitted free-pretrigger distribution |
| `time_constants/` | 拟合 t_rise / t_fall 分布 | fitted rise/fall time distributions |

Every PNG carries the full processing chain + a one-line figure description
stamped at the top, so each file is self-documenting.

## Run

```bash
bash scripts/submit_lp_fit_align.sh <zip...>       # SLURM, one job per zip
# checkpoints make reruns cheap: fits are never redone, only plots regenerate
singularity exec -B "$HOME,/projects/standard/yanliusp/shared/" $SIF \
    python3 scripts/plot_fitted_curves_overlay.py --det 7 [--nrmse-max 0.4]
singularity exec -B "$HOME,/projects/standard/yanliusp/shared/" $SIF \
    python3 scripts/plot_raw_vs_fit_examples.py --det 7
```
