# LED Calibration & Glitch Event Analysis Pipeline

SuperCDMS CUTE R37 run (`23231213_192731`) 的 LED 标定数据分析，包含脉冲模板生成、glitch 事件识别和机器学习探索。

---

## 数据来源

- **实验**：SuperCDMS CUTE，R37 run
- **数据路径**（服务器）：`/projects/standard/yanliusp/shared/data/CDMS/CUTE/R37/Raw/23231213_192731/`
- **文件格式**：MIDAS `.mid.gz`，共 12 个文件
- **探测器**：Z1、Z2、Z3（T3Z3），每个探测器 11 个 phonon 通道（T3Z3 无 PAS1）
- **采样率**：625,000 Hz（每个 event 32768 个采样点，约 52ms）

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `LED data_march 6th.ipynb` | 最早的探索过程，逐步建立脉冲筛选与对齐方法 |
| `LED data.ipynb` | 完整清洁 pipeline，包含模板生成、glitch 识别、指数拟合 |
| `ML.ipynb` | 机器学习探索：分类器、glitch 检测器、时间常数回归 |
| `template_dict.pkl` | 各 (Z, channel) 的平均脉冲模板 |
| `glitch_event_dict.pkl` | 各 (Z, channel) 的 glitch 事件索引 |
| `good_event_dict.pkl` | 各 (Z, channel) 的好事件索引 |

---

## 研究过程（`LED data_march 6th.ipynb`）

### 第一步：读取数据

用 `rawio.RawDataReader` 读取单个 `.mid.gz` 文件，提取 Z3 PBS1 通道的 event 波形。每个 event 是一段 ADC 时间序列。

### 第二步：第一次可视化（从 22ms 开始扫描）

- 用振幅阈值（`max - min > 1000`）初步筛掉无脉冲事件
- baseline 取前 5000 个点的均值，减去后归一化到峰值 = 1
- 从 22ms 开始扫描，找到信号上升超过 0.2 的位置，将该位置对齐到 25.3ms

发现问题：target 设到 22ms 后部分事件（如 event 12）没有对齐。

### 第三步：改进（从 0ms 扫描 + 加入 baseline 约束）

- 改为从 0ms 开始扫描（覆盖所有可能的 pulse 时间）
- 加入 `abs(baseline) < 33000` 过滤 baseline 偏移过大的事件（如 event 12 的 baseline ~33200）
- 对所有 Z1/Z2/Z3 × 11 通道做循环，批量出图

### 第四步：发现 glitch 事件

观察到部分事件在脉冲上升前（约 24.9–25.25ms 窗口内）有一个负方向的 dip（下沉），这是 glitch 特征。

**Glitch 判定条件**：对齐后，在 [24.9, 25.25] ms 窗口内，归一化信号的最小值 `< -0.05`

在 F0012（31 个事件）中发现的 glitch 分布：
- Z3 PFS1、PBS1、PDS1、PES1、PFS2、PBS2、PES2、PDS2：event 12
- Z3 PCS1、PBS1：event 18
- Z1 PDS2：event 29

### 第五步：构建 glitch 字典

建立嵌套字典 `glitch_event_dic[Z][channel] = [event indices]`，保存为 `.npy` 文件。

---

## 完整 Pipeline（`LED data.ipynb`）

### 数据加载

读取全部 12 个 `.mid.gz` 文件，合并为 `all_events`（约 629–775 个 events），用 pickle 缓存加速重复运行。

### Helper 函数

**`find_rise(y_norm, x0_ms)`**
从 0ms 开始每隔 0.05ms 扫描，找到信号在 0.05ms 内上升超过 0.2 的位置，返回上升时刻和索引。

**`preprocess_event(y_raw)`**
1. 减去前 5000 点 baseline
2. 检查 baseline 偏移（`abs(baseline) < 33100`）
3. 计算 peak，要求 peak > 0
4. 自动选 quiet region 估计噪声 std（pulse 早 → 取末尾；pulse 晚 → 取前段）
5. SNR 检查（`peak / noise_std > 5`）
6. 归一化到 peak = 1

**`is_glitch(x_aligned, y_norm, noise_std_norm)`**
对齐后在 [24.9, 25.25] ms 窗口内取最小值，若 `< -5σ`（sigma 倍数可调）则判定为 glitch。

### Step 2 & 3：模板生成 + glitch/good 字典

对每个 (Z, channel) 的所有 events：
1. `preprocess_event` → 筛掉无脉冲或 baseline 异常事件
2. `align_event` → 时间轴对齐到 25.3ms
3. `is_glitch` → 分流到 glitch / good
4. `roll_to_align` → 在样本维度上 roll，对齐到同一 grid
5. 对所有 good events 取平均 → **脉冲模板**

结果保存为 `template_dict.pkl`、`glitch_event_dict.pkl`、`good_event_dict.pkl`。

### Step 4：指数拟合

对每个模板，从样本 14000 开始拟合，先尝试三指数模型，失败则退化到双指数：

```
双指数：-(amp1·exp(-t/t1) - amp1·exp(-t/t2)) + baseline
三指数：-((amp1+amp2)·exp(-t/t1) - amp1·exp(-t/t2) - amp2·exp(-t/t3)) + baseline
```

提取各通道的 rise time constant（t1）和 decay time constants（t2、t3），以 3×11 网格图展示，并输出汇总表格。

### 诊断分析

- **SNR 分布**：中位数约 130，说明信号质量良好（min ~16，max ~1482）
- **Pre-pulse dip 分布**：大部分 events 的 dip 在 −2~0σ，glitch 事件的 dip 可低至 −49σ，两者分布明显分离，5% 分位点约 −3.4σ

---

## 机器学习探索（`ML.ipynb`）

在 `LED data.ipynb` 相同数据上构建三个模型，使用 9 个统计特征（振幅、baseline、峰值、SNR、pre_min、rise time、half decay、tail mean、is_rise）。

### Model 1：事件质量分类（3类）

- **任务**：将每个 (Z, channel, event) 分为 `good` / `no_pulse` / `glitch`
- **算法**：Random Forest（平衡类权重）
- **结果**：5-fold CV F1-macro = 0.91 ± 0.13，训练集准确率 100%
- **数据分布**：20757 个样本，其中 no_pulse 19849、good 895、glitch 13

### Model 2：Glitch 检测器（二分类）

- **任务**：在有脉冲的 events 中区分 good vs glitch（908 个样本，895 good / 13 glitch）
- **算法**：Random Forest + MLP 对比
- **结果**：RF 在测试集 glitch recall = 100%；MLP recall = 67%
- **关键发现**：`pre_min`（脉冲前下沉深度）是最具判别力的特征，与手动阈值方法一致

### Model 3：衰减时间常数回归

- **任务**：从对齐波形预测 decay time constant t2
- **目标**：用 5%–90% 峰值区间做 log-linear 拟合得到 t2（比 half-decay 点更鲁棒）
- **算法**：Random Forest Regressor + MLP Regressor
- **输入**：同样的 9 个统计特征
- **局限**：labeled 数据少（~13 个 glitch events），泛化能力有限

---

## 未来计划

- **更多数据**：扩展到其他 series/run，增加 glitch 样本数量，提升 ML 模型泛化能力
- **PyTorch 1D-CNN**：用对齐后的完整波形（而非统计特征）训练 Model 3，直接从波形预测 t2
- **跨通道分析**：研究同一 glitch event 在不同通道和探测器上的分布规律（是否同时触发？能量如何分布？）
- **自动化 pipeline**：将整个 template 生成和 glitch 识别流程打包，支持新 run 数据的批量处理
