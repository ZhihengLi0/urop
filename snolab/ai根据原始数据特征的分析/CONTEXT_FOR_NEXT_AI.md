# Context for Next AI — ai根据原始数据特征的分析

**Last updated: 2026-06-30（第五次 AI 更新）**
**Status: 第四次提交结果已分析完毕，老师 feedback 已记录，下一步需要修改 pipeline。**

---

## 0. 项目整体背景

这是整个 `~/urop/snolab/` 项目的一部分。**最终目标**：为 CDMS SNOLAB Run 4 的 13 个探测器的 12 个声子通道各生成一个高质量 phonon pulse template，写入 ROOT TH1D 直方图，供 CDMS optimal filter 使用。

### snolab/ 目录结构

| 目录 | 内容 |
|------|------|
| `debug/` | 扫描所有 zip 的事件统计（已完成） |
| `raw_without_filter/` | 已完成的 126G pkl 缓存（见下） |
| `first/` → `ten/` | 历次模板生成迭代（v1-v10） |
| `more_data_analysis_next/` | v11 iteration |
| `ai根据原始数据特征的分析/` | **当前重点**：从 pkl 直接生成模板 |

---

## 1. 关键数据源：126G pkl 缓存

```
/projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache/
├── zip{N}_series/
│   └── {series_timestamp}.pkl
```

**pkl 的生成流程（read_zip_all_series.py）：**
1. 从 processed ROOT 读 PTOFamps，选取落在各 zip 物理窗口内的 phonon events
2. 从原始 MIDAS 读波形，减基线，100kHz LP 滤波，减 pretrigger 基线
3. 对每个 event/channel 做 2-exp 拟合（pretrigger **固定**在 sample 16050）
4. 存储：`raw_traces`（滤波归一化），`ana_traces`（解析拟合 trace，对齐到 16050），`fit_ok_mask`，`fit_params`（t_rise, t_fall, nrmse）

**每个 pkl 内容：**
```python
{
  "raw_traces":    {chan: [array(32768,) float32, ...]},  # LP 滤波+归一化，未对齐
  "ana_traces":    {chan: [array(32768,) float32 or None, ...]},  # 2-exp 解析 trace，对齐到 16050
  "fit_ok_mask":   {chan: [bool, ...]},
  "fit_params_ch": {chan: [{"t_rise": float, "t_fall": float, "nrmse": float} or None, ...]},
  "fail_reasons":  {chan: {reason_str: count}},
}
```

---

## 2. 当前脚本（第四次提交，已完成）

**脚本：`scripts/template_from_pkl.py`**

流程：
1. Pass 1：收集 fit_ok=True + nrmse<=0.15 的 events，计算 pretrigger noise p75 阈值
2. Pass 2：筛选 fit_ok + nrmse + noise<=p75 的 ana_traces
3. 对每个 channel 做 mean + centered PCA → nxm0（mean）+ nxm1-4（mean ± scale × PC）
4. 输出 agnostic/specific ROOT 文件、stats JSON、诊断图

**输出：全部 13 个 zip 成功完成**，结果在 `run/` 下。

---

## 3. 第四次结果分析（2026-06-30 完成）

### 各 zip 质量分层

| 档次 | Zip | 说明 |
|------|-----|------|
| 好 | zip7 | 1000+ events/channel，对齐紧，老师确认无需改动 |
| 好 | zip13, zip15 | 大部分 channel 良好 |
| 中 | zip9, zip10, zip16 | 可用，t_fall 散布较大 |
| 差 | zip4, zip6, zip22 | Events 数量太少（<50/channel），模板不可靠 |
| 混合 | zip1, zip18, zip19, zip24 | 部分 channel 好，部分 channel events 极少 |

### 关键发现：各阶段过滤损失（zip9 代表）

| 阶段 | 条件 | 典型通过率 |
|------|------|-----------|
| PTOFamps | phonon 物理窗口 | ~99% |
| fit_ok | 2-exp 收敛且物理 | 85–96%（zip7）/ 45–57%（zip1） |
| NRMSE ≤ 0.15 | 拟合残差质量 | 3–88%（channel 差异极大） |
| noise ≤ p75 | pretrigger 噪声 | 永远 75%（by definition） |

**zip9 PAS1 只有 15% 通过 NRMSE** 的原因：PAS1 的 NRMSE 整体分布右移（中位数 0.192 vs PES1 的 0.115），是该 channel 电子学噪声更高或 pulse shape 有额外声子分量导致的系统性偏差，不是个别 outlier。

### t_fall 双峰分布

多数 zip 的 Side 1 channel 存在 t_fall 双峰（快 ~0.2–0.5ms，慢 ~1–8ms），是晶体表面 vs 体内事件的真实物理差异。这导致 nxm0（mean）不代表任何真实群体，nxm1 主要描述快/慢两个 population 的差异。

**待搞清楚的问题（老师指出）**：
- t_rise 和 t_fall 分布各自有两段，rise 的前段是否对应 fall 的后段？是否是同一批 events？需要做 2D scatter plot（t_rise vs t_fall）确认是否相关联。

---

## 4. 老师 Feedback（2026-06-30）★ 重要 ★

### 4.1 zip7 不需要改动
zip7 的结果老师认为没有问题，不需要再重跑。

### 4.2 fit_ok + NRMSE 过滤有问题
fit_ok 和 NRMSE 两步过滤掉的比例对部分 zip 不合理（如 zip1 的 fit_ok 只有 55%，NRMSE 只有 3–12%），说明 **fit 本身这一步有问题**，不只是阈值的问题。下一步需要排查 fit 失败的根因（参数初值？边界条件？模型不够用？）。

### 4.3 删除 noise p75 过滤
**noise p75 这个 cut 不需要**，只是让 events 减少，没有实际筛选意义（循环定义，永远淘汰固定比例）。下一步脚本里去掉这一步。

### 4.4 正确的筛选逻辑（老师版本）
```
PTOFamps 窗口选 events
→ 100kHz LP 滤波
→ 2-exp fit（fit_ok 即可，不需要 NRMSE 阈值作为额外 cut）
→ 用 analytical traces 做 amplitude 相关的 plot
→ 在此基础上做 NxM
```

### 4.5 NxM 算法需要修改（最重要）
当前脚本的 NxM 算法（mean ± scale × PCA component）**和老师的不一样**。

**老师的 NxM 算法（参考 `first/notebooks/NxM_cedar.ipynb`）：**

1. 对每个 event 做 2-exp fit，pretrigger 作为**自由参数**（不固定）
2. 归一化对齐：将所有 fit 结果统一设置 amp=canonical，baseline=0，pretrigger=16050，生成解析 trace
3. 对这些解析 traces 做 PCA（`PCA(n_components=50).fit(dataset_array)`）
4. **Templates 就是 PCA 的 components 本身**（不是 mean ± component），即 `PCtot[0], PCtot[1], PCtot[2], ...`
5. 用这些 templates 做 chi-squared 最小化拟合每个 event：`model = amp_a × PC0 + amp_b × PC1 + amp_c × PC2 + ...`

**关键区别：**
- 老师的模板 = PCA components（看起来像心跳图/EKG，有正有负的振荡形状）
- 当前脚本的模板 = mean ± 1σ × PC（始终是 non-negative 的 pulse 形状）

老师说结果应该"像心跳"——这就是 PCA components 的自然形状（指数函数的主成分有振荡结构）。

**notebook 关键代码路径：**
```
first/notebooks/NxM_cedar.ipynb
- 事件选取：PTOFamps>2e-6 && PTOFamps<5e-6
- fit: two_exp_fit（pretrigger 是自由参数）
- PCA: PCA(50, svd_solver='full').fit(dataset_array)
- templates: PCtot[0..4]（components 本身）
- 验证：chi_squared minimization 对每个 event 做 amp_a×T_a + amp_b×T_b + amp_c×T_c 拟合
```

### 4.6 zip7 NxM 图的问题
老师说 zip7 的 NxM 图显示模板比 overlay 图里的 traces 慢，不理解原因，怀疑是代码问题。需要排查：current nxm0（mean template）的 decay 是否系统性地比实际 traces 慢？可能是 p75 noise cut 偏向保留慢脉冲导致的，或者 PCA 方向选择（non-negative 约束）引入了偏差。

---

## 5. 下一步任务（按优先级）

### Task 1：搞清楚 t_rise/t_fall 双峰是否对应同一批 events
做 2D scatter plot：每个 channel 以 t_rise 为 x 轴、t_fall 为 y 轴，看是否有两个 cluster，以及 rise 慢的 event 是否对应 fall 慢的 event。

### Task 2：修改 NxM 算法，对齐老师 notebook
- Templates = PCA components themselves（不是 mean ± component）
- 需要验证输出"看起来像心跳"
- 参考 `first/notebooks/NxM_cedar.ipynb` 的完整逻辑

### Task 3：去掉 noise p75 cut，重新跑（除 zip7 外所有 zip）
修改 `template_from_pkl.py`：删除 Pass 1 和 Pass 2 里的 noise 相关代码。

### Task 4：排查 fit_ok/NRMSE 过低的根因
对 zip1/zip4/zip6/zip22 的 fit 失败事件做诊断：
- 看 fail_reasons 的分布
- 随机抽取几个 fit 失败的 event，plot raw trace，看 pulse 形状是否异常
- 检查参数初值和边界条件是否合适

### Task 5：针对 zip7 NxM 模板偏慢问题
对比 zip7 的 nxm0 和所有 selected traces 的 mean，确认是否一致。如果不一致，找出是哪一步引入了偏差（noise cut？PCA 方向选择？）。

---

## 6. 文件结构

```
ai根据原始数据特征的分析/
├── CONTEXT_FOR_NEXT_AI.md         ← 本文件
├── scripts/
│   ├── template_from_pkl.py       ← 当前主脚本（需修改）
│   ├── submit_from_pkl.sh         ← 提交脚本
│   ├── per_event_analysis.py      ← 旧脚本（已废弃）
│   └── submit_analysis.sh         ← 旧提交脚本（已废弃）
└── run/
    ├── plots/                     ← 13个zip的诊断图（已完成）
    ├── root_files/                ← ROOT 模板输出（已完成，但算法需修改）
    ├── stats/                     ← JSON 时间常数（已完成）
    ├── logs/                      ← Slurm 日志
    └── stage2_cache/              ← 旧脚本缓存（忽略）
```

---

## 6.5 第五次 AI 的分析思路（给下一个 AI 参考）

### 关于去掉 noise p75

p75 是从被过滤的同一批 candidates 里算出来的阈值，永远淘汰固定 25%，是循环定义，没有物理依据。去掉之后唯一影响是每个 channel 多保留约 33% 的 events，fit quality 由 fit_ok 控制已经足够。改动很小：删除 Pass 1 的全部 noise 收集逻辑，Pass 2 里去掉 noise 这一行判断，其他不变。

### 关于 NxM 算法的本质区别

**当前做法**：mean ± scale × PCA_component，生成的 nxm1–4 强制 non-negative，看起来像 pulse 形状。

**老师做法**：PCA components 本身就是 templates（PC0, PC1, PC2, ...），不做 mean ± 运算。

区别的根本在于：老师的 PC0 是数据最主要的变化方向，形状接近平均 pulse。PC1、PC2、PC3 是正交残差方向，形状有正有负，类似 pulse 的导数或振荡，"像心跳"就是这个原因。这些 components 本身不是物理 pulse，而是 basis vectors。optimal filter 用 `amp_a × PC0 + amp_b × PC1 + ...` 的线性组合拟合真实 event，组合结果才是物理的。

当前脚本做 mean ± component + non-negative clip 是为了让每个 template 本身看起来是物理的 pulse，但这样破坏了 PCA 的正交基结构，也引入了 clip 导致的偏差。老师的方式保留完整正交基，更数学上正确。

**改动思路**：把 `build_nxm()` 里 mean ± 的部分改成直接输出 `pca.components_[0..4]`，不做 non-negative 约束，不做 peak 归一化。

### 关于 fit_ok/NRMSE 过低的根因诊断

老师说 fit 这一步本身有问题，不只是阈值问题。关键现象：
- zip7 的 fit_ok 通过率 94–96%（正常）
- zip1 的 fit_ok 只有 45–57%（有近一半 events 直接 fit 失败）
- zip9 PAS1 的 NRMSE 通过率只有 15%（fit 收敛了但残差大）

这是两个不同的问题：
1. fit 直接失败（fit_ok=False）→ 看 fail_reasons（是 "unphysical" 还是 "maxfev exceeded"），如果主要是 "unphysical"（t_rise > t_fall），说明参数初值或边界条件设置有问题，导致 fit 落到非物理解
2. fit 收敛但 NRMSE 高（如 PAS1）→ 说明 pulse shape 本身偏离双指数模型，可能该 channel 有额外噪声或多个声子分量

**在改代码之前，应该先对 zip1 的 fit 失败 events 做诊断图，看实际 raw trace 长什么样，再决定是调参数还是换模型。**

### 关于 zip7 NxM 模板比 overlay 慢的问题

可能原因：
1. noise p75 cut 偏向淘汰快脉冲（快脉冲的 noise/peak 比值相对大，更容易被 cut）→ 去掉 p75 后观察是否改善
2. 当前 PCA 方向选择时强制 non-negative + clip → 改成直接用 PCA components 后观察
3. mean trace 本身没有问题，但 nxm1–4 的生成方式引入了偏慢的 bias

去掉 noise cut + 修改 NxM 算法之后重跑 zip7，对比新旧结果确认。

---

## 7. 注意事项

- singularity 环境：`$MSIPROJECT/shared/singularity_images/cdmsfull_V07-02-00.sif`
- 需要 `--bind /projects` 才能在 singularity 内访问 pkl 路径
- pkl 用 protocol 5，需要 Python 3.9+（singularity 里有）
- ROOT (PyROOT) 在 singularity 里有，系统外没有
- zip7 已确认 OK，重跑时可以跳过 zip7
