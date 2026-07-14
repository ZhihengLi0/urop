# Speaker Script / 演讲稿 — SNOLAB R4 Phonon Pulse Templates

约 10 分钟，13 页。每页先中文、后英文，内容一一对应。括号里是建议用时。
斜体是给自己的提示，不用念。

---

## Slide 1 — Title（约 30 秒）

**中文**：大家好。今天我汇报为 SuperCDMS SNOLAB Run 4 制作声子脉冲模板的工作。内容按分析的先后顺序展开：怎样用 Ge 活化 K 线选出事件样本，逐波形的拟合与对齐算法，每一个质量 cut 是怎样从数据里读出来的，最后是我们为全部 13 个探测器交付的两族模板。

**English**: Good afternoon. Today I'll present our work building phonon pulse templates for SuperCDMS SNOLAB Run 4. I'll follow the order of the analysis itself: how we selected the event sample on the Ge-activation K-line, the per-trace fit-and-align algorithm, how each quality cut was read off the data, and finally the two template families we delivered for all 13 detectors.

---

## Slide 2 — From the Ge-activation K-line to an event sample（约 60 秒）

**中文**：一切从 Ge 活化数据开始。Cf 活化之后，每个锗探测器里都会出现 10.37 keV 的 K 壳层活化线。页面上是全部 13 个探测器的 PTOFamps 谱，来自运行值班的分析；**每格里的红竖线就是值班分析标出的 K 线位置**——这条线怎么拟合出来的是值班分析的工作，我们直接取用它的结果。我们的事件选择只有一条：以红线为中心开一个窗口，位置上下各 1.35 倍，不加任何其他 cut。对每个选中的事件，我们把所有声子通道**完全未处理**的原始 MIDAS 波形连同事件元数据缓存到磁盘，13 个探测器、每个 27 到 30 个 series，约 120 GB。从这些谱上已经能看出问题所在：安静的探测器（比如 Z7）K 线峰和噪声峰分得开，而弱探测器上 K 线紧挨着甚至混进噪声触发群，窗口不可避免会带进噪声。这是有意的设计——因为缓存的是原始数据，之后的每一刀都是显式的、可回退的。

**English**: Everything starts from the Ge activation data. After Cf activation, every Ge detector shows the 10.37 keV K-shell activation line. On this slide you see the PTOFamps spectra of all 13 detectors, from the ops-shift study; **the red vertical line in each panel is the K-line position marked by that study** — how that line was fitted is the ops study's work, and we simply take its result. Our event selection is exactly one condition: a window around the red line, a factor of 1.35 both ways, and nothing else. For every selected event we cache the **fully unprocessed** raw MIDAS traces of all phonon channels, plus the event metadata — 13 detectors, 27 to 30 series each, about 120 gigabytes. You can already see the problem on these spectra: on quiet detectors like Z7 the K-line peak is well separated from the noise peak, while on the weak detectors the K-line sits right next to — or inside — the noise-trigger population, so the window unavoidably admits noise. That is intentional: because the cache is raw, every later cut stays explicit and reversible.

---

## Slide 3 — Per-trace algorithm（约 75 秒）

**中文**：接下来是逐波形的算法，共五步。第一步，100 kHz 四阶 Butterworth 低通，用稳态初始条件，避免滤波器启动瞬态污染后面的峰值搜索。第二步，取 2000 到 12000 样本的中位数作基线并扣除，再用整条波形的全局峰值做归一。第三步是核心：双指数拟合，上升指数减下降指数的形式，**五个参数全部自由，包括脉冲起点 t₀**。第四步，每个拟合记录两个质量量：fit_ok 是物理性检查——幅度为正、上升快于下降；NRMSE 是拟合残差的均方根除以拟合峰值——这一步只记录，不做 cut。第五步，把**实测**波形按"拟合起点减 16050"平移对齐，亚采样插值，纯平移，不做任何解析重构。这里最重要的决定是起点自由：真实触发时刻逐事件变化，拟合出的起点集中在名义值之后约 230 个样本处；如果把起点钉死，其他所有参数都会被扭曲。页面底部两张扇形图就是拟合这一步的输出：把每个事件的拟合曲线画在统一起点、峰值归一。**左图是全部物理拟合、不加任何 cut**——能看到主束旁边散开的慢成分；**右图是 NRMSE ≤ 0.4 之后**——只剩一个紧致的形状家族。这个 cut 是怎么定的，就是接下来几页的内容。

**English**: Next, the per-trace algorithm — five steps. First, a 100-kilohertz fourth-order Butterworth low-pass with steady-state initial conditions, so no filter start-up transient corrupts the later peak search. Second, the baseline — the median of samples 2000 to 12000 — is subtracted, and the trace is normalized by its global peak. Third, the core step: a two-exponential fit, a falling exponential minus a rising one, with **all five parameters free, including the pulse onset t-zero**. Fourth, each fit gets two quality numbers: fit_ok is a physicality check — positive amplitude, rise faster than fall — and NRMSE is the RMS of the fit residual divided by the fitted peak; at this stage it is only recorded, never cut on. Fifth, the **measured** trace is aligned by shifting it by the fitted onset minus 16050, with sub-sample interpolation — a pure translation, no analytic re-generation. The most important decision here is the free onset: real trigger times vary event by event, and the fitted onsets cluster about 230 samples after the nominal value; pinning the onset would distort every other parameter. The two fan plots at the bottom show the output of the fit step: every fitted curve drawn at the common onset, peak-normalized. **The left one is all physical fits, no cut** — you can see slow components spreading off the main bundle. **The right one is after NRMSE ≤ 0.4** — a single tight shape family remains. Where that cut comes from is the next part of the talk.

---

## Slide 4 — Fit quality at a glance（约 45 秒）

**中文**：怎么检查拟合质量？我们用"事件×通道"网格图：一行一个事件，一列一个通道，每格里蓝色是低通后的波形、红色是拟合，右上角标着该格的 NRMSE。规律一眼可见：真正的 K 线事件在所有通道里同时拟合得很好；而噪声触发——比如最上面两行——在所有通道里同时失败。另外，我们所有的图都在页眉里印着完整的处理链，每张图都是自说明的。

**English**: How do we check fit quality? With event-by-channel grids: one row per event, one column per channel; in each panel the blue curve is the low-passed trace, red is the fit, and the panel's NRMSE is stamped in the corner. The pattern is immediate: a genuine K-line event fits well in all channels simultaneously, while a noise trigger — like the top two rows here — fails everywhere at once. And note that every figure we produce carries its full processing chain in the header, so each plot is self-documenting.

---

## Slide 5 — Alignment result（约 45 秒）

**中文**：对齐之后的效果。把所有 fit_ok 事件的实测波形平移到公共起点再叠加——蓝色是波形本身，红色是逐点平均，橙色是拟合曲线的 NRMSE 加权平均，权重是 1 除以 NRMSE 平方，拟合差的事件权重小。这是 Z7 的 PBS1 和 PCS1 两个通道，左边全窗口，右边峰区放大。安静探测器上波形束非常紧，模板的输入是良定义的。请注意 PCS1 放大图里主束旁边那条淡淡的、错位的小束——先记住它，几页之后会回来讲。

**English**: This is what alignment gives us. All fit_ok measured traces are shifted to the common onset and overlaid — blue is the traces themselves, red the point-by-point mean, and orange the NRMSE-weighted mean of the fitted curves, with weight one over NRMSE squared so badly-fit events count less. These are channels PBS1 and PCS1 of Z7, full window on the left, peak zoom on the right. On quiet detectors the bundle is very tight — the template input is well defined. Please notice the faint, displaced bundle next to the main one in the PCS1 zoom — keep it in mind, we'll come back to it in a few slides.

---

## Slide 6 — Quality cut 1: NRMSE ≤ 0.4（约 55 秒）

**中文**：第一个质量 cut。所有物理拟合的 NRMSE 分布在每个探测器上都是双峰的：好拟合群体的中位数在 0.05 到 0.1，噪声触发群体在 1 到 2，中间在 0.4 到 0.5 附近有一个谷。我们把 cut 放在谷底，取 0.4——这个数是从分布本身读出来的，不是对着模板调出来的。上图是安静的 Z7，两个群体干净分开；下图是弱探测器 Z22，噪声群体占主导——在 Z1、Z4、Z6、Z18、Z19、Z22、Z24 这些弱探测器上，PTOF 窗口放进来的是噪声主导的混合体，正是这个 cut 把真实脉冲从里面挖出来。

**English**: The first quality cut. The NRMSE distribution of physical fits is bimodal on every detector: a good-fit population with median around 0.05 to 0.1, a noise-trigger population around 1 to 2, and a valley near 0.4 to 0.5 between them. We place the cut in the valley, at 0.4 — the number is read off the distribution itself, not tuned against the templates. The top plot is quiet Z7, with the two populations cleanly separated; the bottom is weak Z22, where the noise population dominates. On the weak detectors — Z1, Z4, Z6, Z18, Z19, Z22, Z24 — the PTOF window admits a noise-dominated mixture, and this cut is what digs the real pulses out of it.

---

## Slide 7 — The rejected population is noise（约 50 秒）

**中文**：在相信这个 cut 之前，我们检查了它扔掉的是什么。左边是 Z22 上被 NRMSE 拒掉的事件的原始波形网格：完全没有脉冲，就是噪声触发，只不过一条很慢的双指数恰好收敛到了它上面。右边是"扇形-cut"视图：在对齐的实测数据上，绿色是通过 cut 的拟合曲线，红色是被拒的，每个通道标着两个群体各自的 NRMSE 中位数。绿色群体是快而一致的物理脉冲形状，红色群体弥散、中位 NRMSE 高约三倍。结论：这个 cut 移除的是噪声，不是物理。

**English**: Before trusting the cut, we checked what it actually throws away. On the left, event grids of the NRMSE-rejected population on Z22, drawn in the raw traces: there is no pulse at all — these are noise triggers on which a slow two-exponential happened to converge. On the right, the fan-cut view: on top of the aligned data, green shows the fitted curves that pass, red the ones cut away, with each population's median NRMSE stamped per channel. The green population is the fast, consistent physical pulse shape; the red one is spread out with a median NRMSE about three times higher. Conclusion: the cut removes noise, not physics.

---

## Slide 8 — Quality cut 2: τ_rise ≤ 0.3 ms（约 55 秒）

**中文**：第二个 cut 针对一种能骗过 NRMSE 的情况：在窗口较吵的探测器上，平滑的慢基线漂移可以被一条很慢的双指数贴住，残差很小，于是通过了 NRMSE。但看上升时间分布：快脉冲群体在 0.1 毫秒附近，90 分位数约 0.15 毫秒，与漂移的长尾干净地分开，所以我们加一条上限：τ_rise 不超过 0.3 毫秒。在安静探测器上代价约为 2% 到 5% 的信号。有一个已记录在案的权衡：这条上限同时会削掉一小群**真实的**慢上升脉冲——这个最终决定还没有拍板，下一页就讲这群事件。

**English**: The second cut targets something that can fool NRMSE: on detectors with a noisy window, a smooth, slow baseline drift can be hugged by a very slow two-exponential with a tiny residual, so it passes the NRMSE cut. But look at the rise-time distribution: the fast-pulse population sits near 0.1 milliseconds, with its 90th percentile around 0.15 — cleanly separated from the drift tail. So we add a ceiling: tau-rise no larger than 0.3 milliseconds. On quiet detectors the cost is about 2 to 5 percent of the signal. There is one documented trade-off: the same ceiling also trims a small population of **genuine** slow-rise pulses. That final decision is still open — and that population is the next slide.

---

## Slide 9 — A genuine slow-pulse population（约 50 秒）

**中文**：这就是刚才在对齐叠加图里看到的那条"重影"。选择条件是：拟合良好——跨通道中位 NRMSE 不超过 0.4——但同时很慢，中位上升时间大于 0.2 毫秒。看原始波形：这些是真实的脉冲，不是噪声；起点对齐了，峰值却来得晚。这是真实的脉冲形状变化——一个候选解释是与表面/体事件位置有关，但还没有定论。单一模板只能表示一种脉冲形状；要在拟合里表示这种形状变化，就需要多模板的 NxM 方法——这正是我们做第二族模板的动机。

**English**: This is the "shadow" we saw in the aligned overlay. The selection is: well fit — median NRMSE across channels at or below 0.4 — but slow, with median rise time above 0.2 milliseconds. Look at the raw traces: these are real pulses, not noise; the onset is aligned, but the peak comes late. This is genuine pulse-shape variation — one candidate explanation is a surface-versus-bulk event-location effect, but that is not settled. A single template can only represent one pulse shape; representing shape variation like this in the fit takes the multi-template NxM method — which is exactly what motivates our second template family.

---

## Slide 10 — Side finding: Z7 PDS2（约 35 秒）

*（时间紧可以跳过这页，只说一句"我们还排除了一个单通道伪影"。）*

**中文**：一个顺带的发现。Z7 的 PDS2 通道的下降时间分布比其他通道宽得多，中位 0.51 毫秒，而其他通道约 0.25。把这些"慢下降"事件在全部 12 个通道里展开看：同一批事件在其他 11 个通道里都是正常的快脉冲。所以长下降不是慢物理，而是 PDS2 单通道的低频扰动，不影响形状结论。

**English**: One side finding. On Z7, channel PDS2 has a much broader fall-time distribution than every other channel — median 0.51 milliseconds versus about 0.25 elsewhere. Drawing those "slow-fall" events across all 12 channels shows the same events are perfectly normal fast pulses in the other eleven. So the long fall is not slow physics — it's a PDS2-only low-frequency disturbance, and it does not contaminate the shape conclusions.

---

## Slide 11 — Template family 1: 2-exp weighted (1x1)（约 50 秒）

**中文**：第一族模板：解析双指数加权模板。对每个通道，把**所有** fit_ok 的拟合曲线放到公共起点，做加权平均，权重还是 1 除以 NRMSE 平方——拟合差的事件权重低，但从不被人为剔除。图里是施加了 NRMSE 和上升时间两个 cut 之后的扇形图（cut 前后的对比在第 3 页已经看过）：只剩一个紧致的形状家族——它们的加权平均就是 1x1 模板。因为模板由解析曲线构成，天然光滑、无噪声，以峰值归一的 32768-bin ROOT TH1D 交付。

**English**: The first template family: the analytic two-exponential weighted template. For each channel we take **all** fit_ok fitted curves at the common onset and average them, again with weight one over NRMSE squared — badly-fit events count less but are never excluded by hand. The figure shows the fan of fitted curves after both the NRMSE and rise-time cuts (the before/after comparison was on slide 3): a single tight shape family — and its weighted mean is the 1x1 template. Because it is built from analytic curves it is smooth and noise-free by construction, delivered as peak-normalized 32768-bin ROOT TH1D histograms.

---

## Slide 12 — Template family 2: NxM PCA（约 55 秒）

**中文**：第二族模板：NxM PCA 模板，专门捕捉刚才那种形状变化。输入是通过全部三个条件——fit_ok、NRMSE ≤ 0.4、τ_rise ≤ 0.3 ms——的拟合曲线，放在公共起点、峰值归一，在脉冲附近 15550 到 24050 的窗口里做 PCA，每通道最多 3000 条、固定随机种子抽样。nxm0 是平均形状，nxm1 到 nxm4 是前四个主成分——它们是振荡的基矢量，可以取负值，optimal filter 把真实脉冲拟合成它们的线性组合。关键数字：在所有探测器上，前两个主成分就已经解释了 96% 到 98% 的形状方差。交付时五个模板全部峰值归一。

**English**: The second family: the NxM PCA templates, built to capture exactly the shape variation we just saw. The input is the fitted curves passing all three conditions — fit_ok, NRMSE at or below 0.4, tau-rise at or below 0.3 milliseconds — at the common onset, peak-normalized, with the PCA done in a window around the pulse, samples 15550 to 24050, at most 3000 curves per channel with a seeded random subsample. nxm0 is the mean shape; nxm1 through nxm4 are the first four principal components — oscillating basis vectors that can go negative, and the optimal filter fits a real pulse as a linear combination of them. The key number: on every detector, the first two components already capture 96 to 98 percent of the shape variance. All five are delivered peak-normalized.

---

## Slide 13 — Delivered, and what remains（约 45 秒）

**中文**：总结。两族模板已经为全部 13 个探测器交付，采用 cdmsbats 官方 PulseTemplates 格式：每个 zip 一个目录，里面是各通道的 1x1 模板、nxm0 到 nxm4，以及求和的 PT、PS1、PS2。整条链路可追溯：原始缓存、按 series 的拟合检查点都以 EventNumber 索引，11 类诊断图乘 13 个探测器全部入版本库、每张自说明。两个 cut 都是从数据里读出的，并在原始波形里验证过。剩下两件事：一是 τ_rise 上限与真实慢脉冲群体之间的最终取舍；二是对新模板运行组里已有的模板验证方法。谢谢大家，欢迎提问。

**English**: To summarize. Both template families are delivered for all 13 detectors in the official cdmsbats PulseTemplates format: one directory per zip, containing each channel's 1x1 template, nxm0 through nxm4, and the summed PT, PS1 and PS2 templates. The whole chain is traceable: the raw cache and the per-series fit checkpoints are indexed by EventNumber, and all 11 figure types times 13 detectors are versioned and self-documenting. Both cuts were read off the data and verified in the raw traces. Two things remain: the final call on the rise-time ceiling versus the genuine slow-pulse population, and running the group's existing template-validation method on the new templates. Thank you — I'm happy to take questions.

---

*备用问答提示 / Q&A hints*

- **为什么不用实测波形的平均做模板？/ Why not average the measured traces?** 解析拟合曲线本身没有噪声，加权平均出来的模板天然光滑；NRMSE 权重让拟合差的事件自动降权。在对齐叠加图上可以同时画出实测均值（红）和加权拟合均值（橙）互相对照。 / The analytic fitted curves carry no noise, so their weighted mean is smooth by construction, and the NRMSE weight automatically down-weights badly-fit events. The aligned-overlay figures show the measured mean (red) and the weighted fitted mean (orange) side by side for comparison.
- **0.4 这个阈值怎么定的，敏感吗？/ How was 0.4 chosen — is it sensitive?** 阈值取在 NRMSE 双峰分布的谷底，谷里本来就没有多少事件——这正是把 cut 放在谷底的理由。我们还有交互 notebook，可以改阈值几秒内重跑所有探测器的通过率和扇形图。 / The cut sits in the valley of the bimodal NRMSE distribution, where there are few events by construction — that is exactly why the valley was chosen. An interactive notebook re-runs pass rates and fan plots for any threshold within seconds.
- **慢脉冲群体到底留不留？/ Keep the slow pulses or not?** 这是明确记录在案的待定事项。目前 PCA 的输入应用了 τ_rise cut；这个取舍要不要放开，正是接下来要和大家讨论决定的。 / This is the documented open item. The PCA input currently applies the rise-time cut; whether to relax that trade-off is exactly what we want to discuss and decide next.

---

## 术语自查表（只给自己，不进 PPT）

> 过一遍下面每一行；哪一条还觉得说不清楚，提前告诉我，我们把它从幻灯片里去掉或换个说法。

| 术语 | 一句话解释 |
|---|---|
| zip / Z7 | 一个探测器（一块 Ge 晶体）；Run 4 一共 13 个，Z7 是最安静的一个 |
| 声子通道 PAS1…PES2 | 每个探测器的声子读出通道，S1/S2 是晶体的两个面；Z7 的 PFS2 坏了所以只有 11 个 |
| series | 一段连续采数（约 1–2 小时），文件按 series 组织；每个探测器 27–30 个 |
| MIDAS raw | DAQ 写出的原始波形数据格式，完全未经处理 |
| PTOFamps | 官方处理链里"总声子 optimal filter 幅度"，可当作能量的代理量 |
| K 线 | Cf 活化后 Ge 探测器出现的 10.37 keV K 壳层活化线，当单能参考源用 |
| optimal filter (OF) | 用"模板形状 + 噪声谱"对脉冲做加权拟合来估计幅度的标准方法 |
| 1x1 / NxM | 1x1 = 每通道一个模板；NxM = 每通道多个模板（均值 + 主成分），能拟合形状变化 |
| Butterworth 低通 | 一种平滑滤波器；100 kHz 截止把高频噪声滤掉；"4 阶"指滚降的陡峭程度 |
| steady-state init | 滤波器初始条件取稳态值，避免波形开头出现人为的启动瞬态 |
| 2-exp 模型 | 上升一个指数、下降一个指数：y = A(e^(−t/τ_fall) − e^(−t/τ_rise))；5 个自由参数 |
| pretrigger / onset 16050 | 波形里名义的触发位置（第 16050 个采样点）；我们把它当自由参数拟合 |
| NRMSE | 拟合残差的 RMS ÷ 拟合脉冲峰值；无量纲的"拟合好坏"指标 |
| fit_ok | 物理性检查：幅度为正且 τ_rise < τ_fall |
| 亚采样插值对齐 | 平移量不是整数个采样点时用线性插值（np.interp）实现的平移 |
| PCA | 主成分分析：把一堆曲线分解成"均值 + 按方差大小排序的正交变化方向" |
| explained variance | 每个主成分解释的形状方差占比；PC1+PC2 = 96–98% |
| TH1D | ROOT 软件的一维直方图对象；模板的交付格式（32768 个 bin） |
| cdmsbats / PulseTemplates | 官方处理软件 / 它读取模板的配置目录和文件命名规范 |
| PT / PS1 / PS2 | 求和模板：全部通道之和、S1 面之和、S2 面之和（各自峰值归一） |
