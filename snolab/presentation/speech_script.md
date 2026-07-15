# Speaker Script / 演讲稿 — SNOLAB R4 Phonon Pulse Templates

约 10 分钟，13 页。每页先中文、后英文，内容一一对应，**英文可以直接照读**。
原则：稿子是说的话，不是幻灯片的复读——具体参数都在屏幕上，嘴里讲思路和为什么。
斜体是给自己的提示，不用念。

---

## Slide 1 — Title（约 30 秒）

**中文**：大家下午好。今天讲我为 SNOLAB Run 4 做的声子脉冲模板。简单说，就是给 13 个探测器的每个声子通道做出一个"标准脉冲形状"，给 optimal filter 用。我按实际做的顺序讲：事件怎么选的，波形怎么拟合和对齐的，两个质量 cut 是怎么从数据里定出来的，最后是交付的两族模板。

**English**: Good afternoon everyone. Today I'll talk about the phonon pulse templates I built for SNOLAB Run 4. In short: for each phonon channel of thirteen detectors, we build a standard pulse shape for the optimal filter to use. I'll go in the order we actually did the work: how the events were selected, how each trace is fitted and aligned, how the two quality cuts were derived from the data itself, and finally the two template families we delivered.

---

## Slide 2 — From the Ge-activation K-line to an event sample（约 65 秒）

**中文**：先说事件从哪来。做模板需要一大批干净、彼此相同的脉冲。我们用的是 Ge 活化 K 线：Cf 活化之后，每个探测器里都会持续出现 10.37 keV 的单能事件，这是现成的理想样本。屏幕上是 13 个探测器的 PTOFamps 谱——可以把 PTOFamps 理解成官方处理链给出的能量代理量。每格里的红线，是 Saab 教授的分析标出来的 K 线位置，我们直接拿来用。我们做的事情非常简单：以红线为中心开一个窗，上下各 1.35 倍——这个倍数是粗略目测定的，带点随意性，反正开得够宽就行——窗内的事件全要，不加任何别的条件。然后把每个选中事件所有通道的原始波形，原封不动存下来，一共约 120 GB。大家看这些谱：安静的探测器比如 Z7，K 线峰和噪声峰分得很开；但不少噪声大的探测器，红线就插在噪声堆里——窗口一开，噪声肯定跟着进来。这是故意的：我们宁愿先多收，也要让后面每一步筛选清清楚楚、随时可以回退——因为存的是原始数据，什么都没丢。

**English**: Let me start with where the events come from. To build a template, you need a large sample of clean, identical pulses. We use the germanium activation K-line: after the californium activation, every detector keeps producing mono-energetic events at 10.37 keV — a perfect, ready-made sample. What you see here are the PTOFamps spectra of all thirteen detectors — you can think of PTOFamps as the energy estimate from the official processing. The red line in each panel is the K-line position marked by Professor Saab's analysis, and we simply take that as given. What we do is very simple: open a window around the red line, a factor of one point three five on each side — a rough, somewhat arbitrary, eyeballed choice; it just needs to be wide enough — keep everything inside, and apply no other condition. Then, for every selected event, we save the raw traces of all channels, completely untouched — about a hundred and twenty gigabytes in total. Now look at the spectra: on a quiet detector like Z7, the K-line peak is well separated from the noise peak. But on the weaker detectors, the red line sits right inside the noise population — so the window will let noise in. And that's deliberate. We'd rather collect too much, and keep every later selection explicit and reversible — nothing is lost, because what we stored is raw.

---

## Slide 3 — Per-trace algorithm（约 80 秒）

**中文**：拿到原始波形后，每一条都过同样的五步。完整参数都在屏幕上，我挑重点讲。前三步是准备：低通滤波抹掉高频噪声，扣基线，按峰值归一。核心是第四步的拟合：一个双指数函数，一个指数管上升、一个管下降——这是声子脉冲的标准形状。重点在于，五个拟合参数里，连 pretrigger——脉冲的起始时刻——也是放开的。为什么？因为真实触发时刻每个事件都不一样——拟合结果显示，pretrigger 普遍比名义位置晚两百多个采样点。如果把它钉死，这个误差就会被转嫁到上升、下降时间上，把所有参数都带歪。拟合完，每条波形记两个质量指标：一个叫 fit_ok，检查参数物不物理——幅度得是正的，上升得比下降快；另一个叫 NRMSE，全称 Normalized Root-Mean-Square Error，归一化均方根误差——就是拟合残差除以脉冲峰值，衡量拟合得好不好；NRMSE 等于 0.05，意思就是拟合偏差只有脉冲高度的 5%。注意，这一步只记录、不筛选。最后一步，把实测波形按拟合出的 pretrigger 平移对齐——只是平移，波形本身一点没动。下面两张图就是拟合的产出：所有拟合曲线画在同一个 pretrigger 位置上。左边是全部曲线，主束旁边有些散开的；右边是用 NRMSE 筛过之后，只剩一束非常一致的形状。这个筛选标准怎么定的，接下来讲。

**English**: Once we have the raw traces, every single one goes through the same five steps — the full parameters are on the slide, so let me just walk through the ideas. The first three steps are preparation: a low-pass filter to smooth away high-frequency noise, baseline subtraction, and normalization to the peak. The core is the fit: a two-exponential function — one exponential for the rise, one for the fall — which is the standard shape of a phonon pulse. And here's the important part: among the five fit parameters, even the pretrigger — the pulse start time — is left free. Why? Because the true trigger time is different for every event — the fits tell us the pretrigger is typically more than two hundred samples later than the nominal position. If you pin it, that error gets pushed into the rise and fall times, and everything comes out biased. After the fit, each trace gets two quality numbers. One is called fit_ok — a sanity check that the parameters are physical: positive amplitude, rise faster than fall. The other is the NRMSE — the normalized root-mean-square error — which is simply the fit residual divided by the pulse height, so it tells you how good the fit actually is: an NRMSE of zero point zero five means the fit misses the data by five percent of the pulse height. At this stage we only record these; we don't cut on them yet. The last step: shift the measured trace by the fitted pretrigger, so all pulses line up — a pure shift, the waveform itself is untouched. The two plots at the bottom show what the fit gives us: all the fitted curves drawn from the same starting point. On the left, everything — you can see stragglers spreading away from the main bundle. On the right, after selecting on NRMSE, one tight, consistent shape remains. Where that selection comes from is what I'll show next.

---

## Slide 4 — Fit quality at a glance（约 40 秒）

**中文**：先看单个事件层面，拟合到底靠不靠谱。网格图里一行是一个事件、一列是一个通道，蓝色是滤波后的波形，红色是拟合。规律非常清楚：左边这批是噪声触发，它在**所有**通道里同时拟合失败；右边是真正的 K 线事件，**所有**通道同时拟合得很好，NRMSE 只有百分之几。也就是说，"拟合好坏"这个指标真的能把两类事件分开——这给了我们用 NRMSE 做筛选的底气。

**English**: First, a sanity check at the level of individual events. In these grids, each row is one event and each column is one channel — blue is the filtered trace, red is the fit. The pattern is very clear. The left block is noise triggers: the fit fails in **every** channel at the same time. The right block is genuine K-line events: **every** channel fits well at the same time, with NRMSE at the level of a few percent. So "how well the fit went" genuinely separates the two kinds of events — and that's what gives us the confidence to select on NRMSE.

---

## Slide 6 — Quality cut 1: NRMSE ≤ 0.4（约 55 秒）

**中文**：现在讲第一个 cut 怎么定的。把所有物理拟合的 NRMSE 画成分布，每个探测器都是同一个样子：两个峰。左边的峰是拟合好的，典型值百分之五到百分之十；右边的峰在 1 到 2 附近，就是那些根本没有脉冲的噪声触发。两峰之间有一个很深的谷，位置在 0.4 左右——阈值就取 0.4。我想强调：这个数不是调出来的，是分布自己长出来的。上图是安静的 Z7，两个峰离得很远；下图是噪声大的探测器 Z22，噪声峰是主体——对这些探测器来说，这一刀就是把真脉冲从噪声堆里捞出来的那一刀。

**English**: Now, how the first cut was set. If you histogram the NRMSE of all physical fits, every detector shows the same picture: two populations. The left one is the good fits, typically five to ten percent. The right one, around one or two, is the noise triggers — traces with no pulse in them at all. In between there's a deep valley, at about zero point four — and that's where we put the threshold. I want to stress: this number wasn't tuned, it's simply what the distribution itself shows. The top plot is quiet Z7, where the two populations are far apart. The bottom is Z22, a noisy detector, where noise dominates — and for those detectors, this cut is exactly what pulls the real pulses out of the noise.

---

## Slide 7 — The rejected population is noise（约 45 秒）

**中文**：定了 cut 还不够，得验证它切掉的确实是垃圾。左边是被切掉的事件的**原始**波形——可以看到，里面就没有脉冲，纯粹是噪声，只不过一条很慢的曲线恰好凑在了它上面。右边换个角度看同一件事，这张图有三层：底下灰蓝色的是对齐后的实测波形，上面绿色是**通过** cut 的拟合曲线，红色是**被切掉**的；右上角标着两个群体各自的中位 NRMSE 和事件数。可以看到绿的又快又一致，聚成一束；红的四处发散，中位 NRMSE 差不多是绿的三倍——在 Z22 这个通道上，被切掉的有四千八百多个，占了四成。结论很干净：这一刀切掉的是噪声，没有伤到物理。

**English**: Setting a cut isn't enough — we have to verify that what it removes really is junk. On the left are the **raw** traces of the rejected events. As you can see, there is simply no pulse there — it's pure noise, on which some slow curve happened to converge. On the right, the same thing from another angle — this figure has three layers: the gray-blue underneath is the aligned measured traces, green on top is the fitted curves that **pass** the cut, and red is the ones **removed**; the top-right corner shows each population's median NRMSE and its event count. The green ones are fast and consistent, bundled together; the red ones scatter everywhere, with a median NRMSE about three times higher — and on this Z22 channel, over four thousand eight hundred events are removed, about forty percent. So the conclusion is clean: this cut removes noise, and it doesn't touch the physics.

---

## Slide 8 — Follow-up 1: the slow-fall tail（约 50 秒）

**中文**：第一条线索来自 cut 之后的扇形图：还剩一些"拖尾巴"的曲线，下降特别慢。我们的办法是抽样验证：在通过 0.4 的事件里，挑下降时间超过 1.5 毫秒的，随机抽 10 个，把每个事件在全部 12 个通道里的原始波形和拟合画出来对比。结论有两层。第一层：**抽到的这些事件都是真脉冲**——所以保留，我们没有为下降时间设任何 cut。第二层，看左边这张图——我特别想强调这一点：**Z7 本身是我们最好的探测器，但它有一个坏通道，PDS2**。你看每一行是一个事件，除了 PDS2 那一列，其他每一列都是干干净净的快脉冲；唯独 PDS2 这一列，波形上叠着一个大幅度的低频晃动，拟合去追那个晃动，才给出了几毫秒的假"下降时间"。也就是说，慢的不是事件，是 PDS2 这一个通道坏。右边这两张图是同一件事的量化，横轴都是 0 到 20 毫秒，可以直接比：上面是正常通道 PAS1——所有事件挤在 0.25 毫秒一根窄峰里，1 毫秒之后什么都没有；下面是 PDS2——一条明显的宽尾一路拖到五六毫秒，中位数 0.51 毫秒，是正常通道的两倍。所以最夸张的拖尾不是慢物理，是单通道的低频伪影，而且这个探测器好不好、跟这一个通道坏不坏是两回事。

**English**: The first lead comes from the fan plot after the cut: some curves still have long tails — a very slow fall. Our approach was to verify by sampling: among the events that pass the cut, take the ones with a fall time above one and a half milliseconds, randomly sample ten of them, and draw raw versus fit in every one of the twelve channels. The conclusion has two layers. First: **the sampled events are real pulses** — so they stay in, and we apply no fall-time cut at all. Second — and this is the point I really want to make with the left plot: **Z7 is our best detector overall, but it has one bad channel, PDS2**. Each row is one event, and in every column except PDS2 you see a clean, fast pulse; only in the PDS2 column is there a large low-frequency swing riding on top of the trace, and the fit chases that swing, which is what produces the fake fall times of several milliseconds. So it's not the event that's slow — it's that one channel, PDS2, that's misbehaving. The two plots on the right are the same story quantified, on the same zero-to-twenty-millisecond axis so you can compare directly: the top one is a normal channel, PAS1 — everything piled into a narrow spike at 0.25 milliseconds, nothing beyond one; the bottom one is PDS2 — a clear broad tail stretching out to five or six milliseconds, with a median of 0.51 milliseconds, twice that of the normal channel. So the most extreme tails are not slow physics; they're a one-channel low-frequency artifact — and a detector being good overall and one of its channels being bad are two separate things.

---

## Slide 9 — Follow-up 2: genuine slow-rise pulses / echo-trigger（约 60 秒）

**中文**：第二条线索是慢上升。挑选的做法说一下：对每个事件，它所有拟合正常的通道各给出一个 NRMSE 和一个上升时间，我们**跨通道取中位数**——注意是中位数、不是平均数，这样哪怕某一个通道抽风，也带不偏对整个事件的判断。一个事件如果**中位 NRMSE 达标、同时中位上升时间超过 0.2 毫秒**，就入选；按存储顺序取前几个，不做任何人工挑选，画出原始波形来看。这次结论正相反：这些是**真脉冲**。pretrigger 对得齐，峰值来得晚，而且所有通道一致——它们就是所谓的 echo-trigger——主脉冲后面一道更慢的"回声"。所以慢上升不能一刀切掉：里面有真物理，可能与事件在晶体里的位置有关，这一点还没有定论。而这种真实的形状变化，恰恰是多模板 NxM 方法要捕捉的东西。

**English**: The second lead is the slow rise. Let me explain how these events are selected. For each event, every channel with a valid fit contributes one NRMSE and one rise time, and we take the **median across channels** — the median, not the mean, so even if one channel misbehaves, it cannot bias the decision for the whole event. An event qualifies when its **median NRMSE passes the cut and its median rise time is above zero point two milliseconds**; we take the first few in storage order, with no hand-picking, and draw their raw traces. This time the conclusion is the opposite: these are **real pulses**. The pretrigger lines up, the peak comes late, and it's consistent across all channels — they are the echo-trigger population — a genuine second, slower pulse shape. So the slow rise cannot simply be cut away: there's real physics in it, possibly related to where in the crystal the event happens — that's not settled yet. And this kind of genuine shape variation is exactly what the multi-template NxM method is built to capture.

---

## Slide 10 — τ_rise ≤ 0.3 ms ceiling（约 50 秒）

**中文**：但慢上升这边还有一个搅局者。在窗口比较吵的探测器上，缓慢的基线漂移也会被拟合成"慢上升"，而且残差很小，NRMSE 抓不到它。看上升时间的分布：真脉冲集中在 0.1 毫秒附近，非常窄；漂移的尾巴拖得远得多。所以做模板输入时我们设了一条上限：上升时间不超过 0.3 毫秒。这样漂移被挡住，绝大多数真脉冲——包括一部分 echo-trigger 事件——留了下来，代价只有百分之二到五的信号。但要坦白：最慢的那一小撮**真**脉冲也被削掉了。这个取舍记录在案、还没最终拍板，待会儿想听听大家的意见。

**English**: But on the slow-rise side there's also a troublemaker. On detectors with a noisy window, a slow baseline drift also gets fitted as a "slow rise," with a tiny residual — NRMSE can't catch it. Look at the rise-time distribution: real pulses cluster near zero point one milliseconds, very narrow, while the drift tail stretches much further. So for the template input we set a ceiling: rise time no more than zero point three milliseconds. That blocks the drift and keeps the vast majority of real pulses — including part of the echo-trigger population — at a cost of only a few percent of the signal. But to be upfront: the very slowest **genuine** pulses get trimmed too. That trade-off is documented and not final — I'd like to hear your thoughts on it later.

---

## Slide 11 — Template family 1: 2-exp weighted (1x1)（约 45 秒）

**中文**：现在到产出。第一族模板走解析路线：每个通道，把所有物理拟合的曲线放到同一个 pretrigger 位置，做加权平均——权重是 NRMSE 平方的倒数。这个设计的好处是：拟合差的事件权重自动变得极小，等于被压没了，但我们不需要人为剔除任何事件。屏幕上就是参与平均的这束曲线。因为平均的对象是解析函数，做出来的模板天然光滑、完全没有噪声。这就是标准的单模板，1x1。

**English**: Now to the deliverables. The first template family takes the analytic route: for each channel, we put all the physical fitted curves at the same pretrigger and take a weighted average — the weight is one over NRMSE squared. The nice property of this design is that badly-fit events automatically get a vanishingly small weight, so they're effectively suppressed — but we never have to remove anything by hand. What's on screen is the bundle of curves that goes into that average. And because we're averaging analytic functions, the resulting template is smooth and completely noise-free by construction. That's the standard single template — the one-by-one.

---

## Slide 12 — Template family 2: NxM PCA（约 50 秒）

**中文**：第二族模板就是为刚才那种形状变化准备的。做法是对通过全部筛选的拟合曲线做主成分分析，PCA。直观理解：黑色的 nxm0 是平均形状；后面四条彩色的，是数据里最主要的四个"变形方向"——比如上升更慢一点、下降更快一点。真实脉冲就用这五条的线性组合去拟合。效果非常好：前两个成分就已经覆盖了 96 到 98% 的形状差异。也就是说，那群慢脉冲不再是麻烦——它们被显式地表示进了模板空间里。最后一步，交付之前把五条模板统一归一到峰值为 1，方便对比和使用——这就是最终产物。

**English**: The second family is built precisely for the shape variation we just saw. We run a principal component analysis — PCA — on the fitted curves that pass all the selections. The intuition: the black curve, nxm-zero, is the average shape; the four colored ones are the four main "directions of deformation" in the data — say, a slightly slower rise, or a faster fall. A real pulse is then fitted as a linear combination of these five. And it works remarkably well: the first two components already cover ninety-six to ninety-eight percent of the shape variation. So the slow population is no longer a problem — it's explicitly represented inside the template space. As a final step before delivery, all five templates are normalized to unit peak, so they're easy to compare and use — and that is the final product.

---

## Slide 13 — Delivered, and what remains（约 45 秒）

**中文**：总结一下。两族模板已经为全部 13 个探测器交付，用的是官方 cdmsbats 的标准格式，处理链可以直接读。整个分析每一步都可追溯：原始缓存、每个拟合的检查点、所有诊断图，全部有版本记录，每张图上都印着自己的完整处理过程。两个 cut 都是从数据分布里读出来、又回到原始波形里验证过的。还剩两件事：一是慢脉冲那个取舍需要拍板，想听听大家的意见；二是对新模板跑一遍组里的模板验证流程。谢谢大家，欢迎提问。

**English**: To wrap up. Both template families are delivered for all thirteen detectors, in the official cdmsbats format, ready for the processing chain to read. Every step of the analysis is traceable — from the raw cache, to the per-fit checkpoints, to all the diagnostic figures: everything is under version control, and every figure carries its full processing history printed on it. Both cuts were read off the data, and then verified back in the raw traces. Two things remain: first, the slow-pulse trade-off needs a decision — I'd like to hear your thoughts on that. And second, running the group's template-validation procedure on the new templates. Thank you — I'm happy to take questions.

---

*备用问答提示 / Q&A hints*

- **为什么不用实测波形的平均做模板？/ Why not average the measured traces?** 解析拟合曲线本身没有噪声，加权平均出来的模板天然光滑；NRMSE 权重让拟合差的事件自动降权。对齐叠加图上实测均值（红）和加权拟合均值（橙）可以互相对照。 / The analytic fitted curves carry no noise, so their weighted mean is smooth by construction; the NRMSE weight down-weights badly-fit events automatically. The overlays show the measured mean (red) and the weighted fitted mean (orange) side by side for comparison.
- **0.4 怎么定的，敏感吗？/ How was 0.4 chosen — is it sensitive?** 取在双峰分布的谷底，谷里本来就没多少事件——这正是选谷底的理由。还有交互 notebook，改阈值几秒内能重跑所有探测器。 / It sits in the valley of the bimodal distribution, where there are few events by construction — that's exactly why the valley was chosen. An interactive notebook re-runs any threshold within seconds.
- **两族模板的 cut 为什么不一样？/ Why do the two families apply cuts differently?** 1x1 不硬切，靠权重：好拟合 NRMSE≈0.05 权重 400，噪声 NRMSE≈2 权重 0.25，差四个数量级，噪声自动压没，不需要人为定一刀。PCA 对离群点敏感——一条噪声曲线就能污染主成分方向——所以 NxM 的输入必须硬切干净（fit_ok + NRMSE ≤ 0.4 + τ_rise ≤ 0.3 ms）。 / The 1x1 uses weighting instead of a hard cut: a good fit at NRMSE 0.05 gets weight 400, a noise trigger at 2 gets 0.25 — four orders of magnitude apart, so noise is automatically suppressed without choosing a threshold. PCA is sensitive to outliers — one noise curve can contaminate the components — so the NxM input must be hard-cut clean.
- **慢脉冲群体到底留不留？/ Keep the slow pulses or not?** 这是明确记录在案的待定事项。目前 PCA 的输入应用了 τ_rise cut；这个取舍要不要放开，正是想和大家讨论决定的。 / This is the documented open item. The PCA input currently applies the rise-time cut; whether to relax that trade-off is exactly what we'd like to discuss and decide.

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
| Butterworth 低通 | 一种平滑滤波器；100 kHz 截止把高频噪声滤掉；"4 阶"指截止后压制的陡峭程度 |
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
