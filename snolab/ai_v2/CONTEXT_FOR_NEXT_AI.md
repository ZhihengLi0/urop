# Context for Next AI — ai_v2

**Last updated: 2026-06-30（第五次 AI，v2 脚本创建）**
**Status: v2 脚本已写好，尚未提交运行。**

---

## 0. 这个 folder 是什么

`ai_v2/` 是在 `ai根据原始数据特征的分析/`（v1）基础上按老师 feedback 修改的第二版。
v1 的完整背景和历史见：`../ai根据原始数据特征的分析/CONTEXT_FOR_NEXT_AI.md`

---

## 1. 老师 Feedback（2026-06-30）及对应处理

老师共提出 8 个问题，逐一对应如下：

---

### 问题 1：zip7 不需要改动

**处理：已解决。**
`submit_v2.sh` 的 ZIPS 列表不包含 zip7，提交时自动跳过。
zip7 的 v1 结果（`../ai根据原始数据特征的分析/run/`）直接使用。

---

### 问题 2：fit_ok + NRMSE 两步过滤比例不合理，说明 fit 本身有问题

**处理：部分解决，根因未动。**

v2 删掉了 NRMSE cut，只保留 fit_ok。但 fit_ok 本身的低通过率（zip1 只有 55%，zip7 有 95%）是 pkl 生成那一步（`read_zip_all_series.py`）的问题，不在 v2 范围内。

**待办：** 需要单独诊断 fit 失败根因：
- 看 zip1 的 `fail_reasons` 分布（是 "unphysical" 还是 "maxfev exceeded"）
- 抽几个 fit 失败的 event 画 raw trace，看 pulse 形状是否特殊
- 如果根因找到了，需要修改 pkl 生成脚本并重新生成 pkl（工作量大）

**已知数据（zip9 为例）：**
- fit_ok fail reasons: 主要是 "unphysical"（t_rise > t_fall），少量 maxfev exceeded
- zip1 fit_ok 只有 45–57%，zip7 有 94–96%，差异极大

---

### 问题 3：noise p75 无用，删掉

**处理：已解决。**
v2 完全删除 Pass 1（noise 收集）和 Pass 2 里的 noise 判断。
筛选只剩 fit_ok=True 一个门。

**原因回顾：** p75 是从被筛选的同一批 candidates 里算的，循环定义，永远淘汰固定 25%，无物理依据。

---

### 问题 4：筛选逻辑应为 PTOFamps → 100kHz LP → fit_ok → ana_traces → NxM

**处理：已解决。**
v2 的流程完全对应：
- PTOFamps 窗口选 events：pkl 生成时已完成
- 100kHz LP 滤波：pkl 生成时已完成
- fit_ok=True：v2 Pass 2 唯一的筛选条件
- ana_traces：直接使用 pkl 里的，pretrigger 固定在 16050，peak=1

---

### 问题 5：要 plot 出来 analytical plot 关于振幅的

**处理：已有。**
`aligned_overlay.png` 画的就是所有选中 ana_traces 的叠加（蓝色细线）+ mean（红线），展示 analytical traces 的形状和振幅分布。

**待确认：** 如果老师指的是振幅 vs 时间散点或者按振幅分组的图，需要进一步问清楚。

---

### 问题 6：NxM 要参考老师 notebook（first/notebooks/NxM_cedar.ipynb），做出来应该像心跳

**处理：已解决（待跑完验证）。**

**老师的算法（NxM_cedar.ipynb）：**
1. 对每个 event 做 2-exp fit，pretrigger 作为**自由参数**
2. 归一化对齐：amp=canonical，baseline=0，pretrigger=16050
3. `PCA(n_components=50, svd_solver='full').fit(dataset_array)`
4. **templates = PCA components 本身**（`PCtot[0], PCtot[1], ...`）
5. 验证：对每个 event 做 `minimize(chi_squared, [amp_a, amp_b, amp_c], templates)`

**v1 vs v2 的本质区别：**
- v1：`templates[i] = mean ± scale × component`（non-negative，看起来像 pulse）
- v2：`templates[i] = pca.components_[i]`（有正有负，像心跳/EKG）

PCA components 是正交 basis vectors，PC1 是主要形状，PC2+ 是振荡形的残差（导数结构），"像心跳"就是这个原因。optimal filter 用 `sum_i amp_i × PC_i` 线性组合拟合每个 event，组合结果才是物理 pulse，单个 component 本身不需要是物理的。

**跑完后验证：** 看 `zip{N}_nxm_specific.png`，PC1 应该是 pulse 形状，PC2–4 应该是有正有负的振荡结构。

---

### 问题 7：zip7 NxM 模板比 overlay 的 traces 慢，是不是代码问题

**处理：可能改善，待跑完验证。**

v1 的两个可能原因：
1. **noise p75 偏向淘汰快脉冲**：快脉冲的 pretrigger noise/peak 比值大，更容易被 p75 cut → v2 删掉 p75 后 bias 消失
2. **mean ± component + non-negative clip 引入偏慢 bias**：clip 负值会把上升沿截断，使 mean 往慢的方向偏 → v2 改成 PCA components 后这个问题消失

**待办：** 单独提交 zip7 跑 v2，对比新旧 `aligned_overlay.png` 和 `nxm_specific.png`，看 nxm0（mean）是否还是比 overlay traces 慢。

---

### 问题 8：t_rise 和 t_fall 各有两段，rise 前段对应 fall 后段吗，是同一批 events？

**处理：已增加工具，待跑完看图。**

v2 新增了第四张图：`zip{N}_trise_vs_tfall.png`，2D scatter（x=t_rise, y=t_fall），每个点是一个 event。

**如何看图：**
- 如果 scatter 里有两个 cluster（一个在左下/右上角，一个在右下/左上角）→ 两段对应不同群体
- 如果 scatter 呈对角线分布（rise 大则 fall 也大）→ 双峰是同一批 events 的相关特征
- 如果两个方向独立分散 → 双峰是两个独立物理群体

**物理预期：** 表面事件 t_rise 快且 t_fall 快，体内事件 t_rise 慢且 t_fall 慢，因此预计 scatter 里有一个对角线结构，两段分别对应表面 vs 体内事件。但需要图来确认。

---

## 2. v2 改动总结

| 改动 | v1 | v2 |
|------|----|----|
| noise p75 | 有 | **删除** |
| NRMSE cut | nrmse <= 0.15 | **删除** |
| 筛选条件 | fit_ok + nrmse + noise | **fit_ok only** |
| NxM templates | mean ± scale × PC（non-negative）| **PCA components 直接输出（可为负）** |
| 新增图 | 无 | **t_rise vs t_fall 2D scatter** |
| zip7 | 重跑 | **跳过** |

---

## 3. 文件结构

```
ai_v2/
├── CONTEXT_FOR_NEXT_AI.md         ← 本文件
├── scripts/
│   ├── template_from_pkl_v2.py    ← 主脚本
│   └── submit_v2.sh               ← 提交脚本（跳过 zip7）
└── run/
    ├── plots/                     ← PNG 输出（待生成）
    ├── root_files/                ← ROOT 输出（待生成）
    ├── stats/                     ← JSON 时间常数（待生成）
    └── logs/                      ← Slurm 日志（待生成）
```

---

## 4. 下一步

### 立即可做：
1. 先单独提交 zip7 验证 NxM 心跳形状和模板偏慢问题是否改善：
   ```bash
   cd ~/urop/snolab/ai_v2
   singularity exec --bind /projects $MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif \
       python3 scripts/template_from_pkl_v2.py --det 7
   # 或用 sbatch 提交单个 zip7
   ```
2. 确认 NxM 图像是否像心跳（PC1 是 pulse 形状，PC2–4 是振荡）
3. 确认 zip7 nxm0 是否还是比 overlay 慢
4. 确认 t_rise vs t_fall scatter 是否显示两个独立 cluster

### 根因诊断（较大工作量，需要先问老师优先级）：
- 排查 fit_ok 低通过率（zip1/zip4/zip6/zip22）的根因
- 可能需要修改 `read_zip_all_series.py` 里的 fit 参数初值或边界条件

---

## 5. 参考

- v1 脚本：`../ai根据原始数据特征的分析/scripts/template_from_pkl.py`
- 老师 NxM notebook：`../first/notebooks/NxM_cedar.ipynb`
- v1 完整背景：`../ai根据原始数据特征的分析/CONTEXT_FOR_NEXT_AI.md`
- singularity 环境：`$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif`
- 需要 `--bind /projects` 才能在 singularity 内访问 pkl
