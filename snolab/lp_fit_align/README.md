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
notebooks/               interactive NRMSE-cut exploration (in git)
results/plots/<type>/    one sub-dir per figure type, all zips together
results/stats/           per-zip JSON summaries (in git)
results/root_files/      final templates, one TH1D per channel, 32768 bins:
                         Templates_SNOLAB_R4_zip{N}_2expfit_weighted.root —
                         NRMSE-weighted mean of all fit_ok fitted 2-exp curves
                         (the orange curve of aligned_overlay);
                         Templates_SNOLAB_R4_zip{N}_nxm_pca.root — PCA
                         templates nxm0 (mean) + nxm1..4 (components), all
                         peak-normalized to 1
run/checkpoints/zip{N}/  per-series fit-parameter pkl (index-aligned with the
                         raw cache's event_numbers_ch; analyses never refit)
run/logs/                SLURM logs
```

## Figure types (`results/plots/`)

| sub-dir | 中文说明 | what it shows |
|---|---|---|
| `aligned_overlay/` | 平移对齐的**实测**波形（蓝）+ 实测均值（红）+ 拟合曲线的 NRMSE 加权均值（橙，w=1/max(NRMSE,0.01)²） | aligned measured traces (blue) + measured mean (red) + NRMSE-weighted mean of fitted curves (orange) |
| `fitted_curves_overlay/` | 拟合光滑曲线扇形图：形状参数代回解析式，起点统一 16050、峰高归一 | smooth fitted 2-exp curves at common pretrigger, peak-normalized — shape distribution only |
| `raw_vs_fit_examples/` | 事件网格：前 15 个选中 event × 12 通道，每格 raw（灰）+ LP（蓝）+ 拟合（红），与 fit_examples 同一批 event | event grid (same 15 events as fit_examples), raw vs LP vs fit per panel |
| `fit_examples/` | 事件网格：前 15 个选中 event × 12 通道，每格 LP vs 拟合 + NRMSE——同一事件跨通道一致性一眼可见 | event grid: one row per event, one column per channel, LP vs fit with per-panel NRMSE |
| `overlay_fan_cut/` | 三合一：对齐实测（灰蓝）+ 通过 NRMSE cut 的拟合曲线（绿）+ 被筛掉的（红），右上角标两群 NRMSE 中位数 | measured traces + fitted curves split by the NRMSE cut, per-population median NRMSE stamped |
| `nrmse/` | NRMSE 分布（对数轴 log-log）：双峰 = 好拟合 vs 噪声触发，谷 = cut 阈值候选 | log-binned NRMSE distribution of fit_ok events |
| `pretrigger/` | 拟合出的自由 pretrigger 分布（真实触发点，参考 16050） | fitted free-pretrigger distribution |
| `time_constants/` | 拟合 t_rise / t_fall 分布 | fitted rise/fall time distributions |
| `slow_rise_events/` | NRMSE 被拒群体的事件网格（跨通道中位 NRMSE>0.4）——raw 显示为噪声触发 | event grid of the NRMSE-rejected population; raw traces show noise triggers |
| `shadow_events/` | 重影群体：拟合良好且慢上升（中位 NRMSE≤0.4 且中位 t_rise>0.2ms）——真实慢脉冲 | well-fit slow-rise events (the faint displaced bundle in aligned overlays) |
| `slow_fall_events/` | 慢下降研究（Z7/PDS2）：长 t_fall 事件全通道展开——证明是 PDS2 单通道低频伪影 | long-t_fall study: real pulses in 11 channels, PDS2-only artifact |
| `pca_templates/` | 最终 NxM PCA 模板 nxm0–4（峰值归一化）+ 各 PC 方差占比 | final NxM PCA templates with explained-variance ratios |

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
