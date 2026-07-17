# Speaker Script / 演讲稿 — SNOLAB R4 Phonon Pulse Templates

约 9 分钟，11 页 + 1 页 backup（弱探测器 Z22 示例，不占正片时间）。每页先中文、后英文，内容一一对应，**英文可以直接照读**。
原则：稿子是说的话，不是幻灯片的复读——具体参数都在屏幕上，嘴里讲思路和为什么。
斜体是给自己的提示，不用念。

---

## Slide 1 — Title（约 30 秒）

**中文**：大家下午好。今天讲我为 SNOLAB Run 4 做的声子脉冲模板。简单说，就是给 13 个探测器的每个声子通道做出一个"标准脉冲形状"，给 optimal filter 用。我按实际做的顺序讲：事件怎么选的，波形怎么拟合和对齐的，两个质量 cut 是怎么从数据里定出来的，最后是交付的两族模板。

**English**: Good afternoon everyone. Today I'll talk about the phonon pulse templates I built for SNOLAB Run 4. In short: for each phonon channel of thirteen detectors, I build a standard pulse shape for the optimal filter to use. I'll go in the order I actually did the work: how the events were selected, how each trace is fitted and aligned, how the two quality cuts were derived from the data itself, and finally the two template families I delivered.

---

## Slide 2 — From the Ge-activation K-line to an event sample（约 65 秒）

**中文**：先说事件从哪来。做模板需要一大批干净、彼此相同的脉冲。我用的是 Ge 活化 K 线：Cf 活化之后，每个探测器里都会持续出现 10.37 keV 的单能事件，这是现成的理想样本。屏幕上是 13 个探测器的 PTOFamps 谱——可以把 PTOFamps 理解成官方处理给出的能量估计值。每格里的红线，是 Saab 教授的分析标出来的 K 线位置，我直接拿来用。我做的事情非常简单：以红线为中心开一个窗，上下各 1.35 倍——这个倍数是粗略目测定的，带点随意性，反正开得够宽就行——窗内的事件全要，不加任何别的条件。然后把每个选中事件所有通道的原始波形，原封不动存下来，一共约 120 GB。大家看这些谱：安静的探测器比如 Z7，K 线峰和噪声峰分得很开；但不少噪声大的探测器，红线就插在噪声堆里——窗口一开，噪声肯定跟着进来。这是故意的：我宁愿先多收，也要让后面每一步筛选清清楚楚、随时可以回退——因为存的是原始数据，什么都没丢。

**English**: Let me start with where the events come from. To build a template, you need a large sample of clean, identical pulses. I use the germanium activation K-line: after the californium activation, every detector keeps producing mono-energetic events at 10.37 keV — a perfect, ready-made sample. What you see here are the PTOFamps spectra of all thirteen detectors — you can think of PTOFamps as the energy estimate from the official processing. The red line in each panel is the K-line position marked by Professor Saab's analysis, and I simply take that as given. What I do is very simple: open a window around the red line, a factor of one point three five on each side — a rough, eyeballed choice; it just needs to be wide enough — keep everything inside, and apply no other condition. Then, for every selected event, I save the raw traces of all channels, completely untouched — about a hundred and twenty gigabytes in total. Now look at the spectra: on a quiet detector like Z7, the K-line peak is well separated from the noise peak. But on the weaker detectors, the red line sits right inside the noise population — so the window will let noise in. And that's deliberate. I'd rather collect too much, and keep every later selection explicit and reversible — nothing is lost, because what I stored is raw.

---

## Slide 3 — Fit quality at a glance / data overview（约 40 秒）

**中文**：先看单个事件层面，拟合到底靠不靠谱。网格图里一行是一个事件、一列是一个通道，蓝色是滤波后的波形，红色是拟合。规律非常清楚：左边这批是噪声触发，它在**所有**通道里同时拟合失败；右边是真正的 K 线事件，**所有**通道同时拟合得很好，残差只有百分之几。也就是说，事件干干净净地分成两类——要么全通道都好，要么全通道都坏。至于每一条波形具体怎么滤波、怎么拟合、怎么对齐，就是下一页的内容。

**English**: First, a sanity check at the level of individual events. In these grids, each row is one event and each column is one channel — blue is the filtered trace, red is the fit. The pattern is very clear. The left block is noise triggers: the fit fails in **every** channel at the same time. The right block is genuine K-line events: **every** channel fits well at the same time, with a residual of only a few percent. So the events split cleanly into two kinds — good in every channel, or bad in every channel. Exactly how each trace is filtered, fitted and aligned is the next slide.

---

## Slide 4 — Per-trace algorithm（约 80 秒）

**中文**：拿到原始波形后，每一条都过同样的五步。完整参数都在屏幕上，我挑重点讲。前三步是准备：低通滤波抹掉高频噪声，扣基线，按峰值归一。核心是第四步的拟合：一个双指数函数，一个指数管上升、一个管下降——这是声子脉冲的标准形状。重点在于，五个拟合参数里，连 pretrigger——脉冲的起始时刻——也是放开的。为什么？因为真实触发时刻每个事件都不一样——拟合结果显示，pretrigger 普遍比名义位置晚两百多个采样点。如果把它钉死，这个误差就会被转嫁到上升、下降时间上，把所有参数都带歪。拟合完，每条波形记两个质量指标：一个叫 fit_ok，检查参数物不物理——幅度得是正的，上升得比下降快；另一个叫 NRMSE，全称 Normalized Root-Mean-Square Error，归一化均方根误差——就是拟合残差除以脉冲峰值，衡量拟合得好不好；NRMSE 等于 0.05，意思就是拟合偏差只有脉冲高度的 5%。注意，这一步只记录、不筛选。第五步——对齐，以及对齐后的效果，下一页单独讲。

**English**: Once I have the raw traces, every single one goes through the same five steps — the full parameters are on the slide, so let me just walk through the ideas. The first three steps are preparation: a low-pass filter to smooth away high-frequency noise, baseline subtraction, and normalization to the peak. The core is the fit: a two-exponential function — one exponential for the rise, one for the fall — which is the standard shape of a phonon pulse. And here's the important part: among the five fit parameters, even the pretrigger — the pulse start time — is left free. Why? Because the true trigger time is different for every event — the fits tell us the pretrigger is typically more than two hundred samples later than the nominal position. If you pin it, that error gets pushed into the rise and fall times, and everything comes out biased. After the fit, each trace gets two quality numbers. One is called fit_ok — a sanity check that the parameters are physical: positive amplitude, rise faster than fall. The other is the NRMSE — the normalized root-mean-square error — which is simply the fit residual divided by the pulse height, so it tells you how good the fit actually is: an NRMSE of zero point zero five means the fit misses the data by five percent of the pulse height. At this stage I only record these; I don't cut on them yet. Step five — the alignment, and what it produces — gets its own slide next.

---

## Slide 5 — Alignment result（约 40 秒）

**中文**：这一页讲第五步——对齐。每一条实测波形，按它自己拟合出的 pretrigger 减去名义的 16050 平移——纯平移，波形本身没有任何再生成。图里那条竖虚线，就是所有波形对齐到的公共 pretrigger。对齐之后，把所有拟合曲线画在这个公共起点上，就是这两张扇形图。左边是全部物理拟合的曲线——可以看到主束旁边有一些明显散开、下降很慢的曲线；右边是用 NRMSE 筛过之后，只剩一束非常紧、非常一致的形状。正是把触发抖动对齐掉、再筛掉坏拟合之后，剩下这条紧致的束，我才能做出一个定义清楚、稳定的模板。至于 NRMSE 这个筛选阈值具体怎么定的，下一页讲。

**English**: This slide is step five — alignment. Each measured trace is shifted by its own fitted pretrigger minus 16050 — a pure translation, nothing about the waveform is regenerated. The dotted vertical line is the common pretrigger everything is aligned to. Once aligned, I draw all the fitted curves from that common starting point — these two fan plots. On the left, all the physical fits: you can see some clearly separated, slow-falling curves that spread off the main bundle. On the right, after selecting on NRMSE, only one very tight, consistent shape family remains. Alignment removes the jitter, the NRMSE cut removes the bad fits, and what's left is this tight bundle — tight enough to build a template from. Exactly how the NRMSE threshold is set is the next slide.

---

## Slide 6 — Quality cut 1: NRMSE ≤ 0.4（约 55 秒）

**中文**：现在讲第一个 cut 怎么定的。把所有物理拟合的 NRMSE 画成分布，每个探测器都是同一个样子：两个峰。左边的峰是拟合好的，典型值百分之五到百分之十；右边的峰在 1 到 2 附近，就是那些根本没有脉冲的噪声触发。两峰之间有一个很深的谷，位置在 0.4 左右——阈值就取 0.4。我想强调：这个数不是调出来的，是分布自己长出来的。图里是 Z7 的 PBS1——全场用的就是这条通道——两个峰离得很远，谷一目了然。较弱的探测器——比如 Z22——是同样的双峰图景，只是噪声峰是主体，对它们来说这一刀就是把真脉冲从噪声堆里捞出来的那一刀。*（有人问弱探测器长什么样，再翻 backup 页。）*

**English**: Now, how the first cut was set. If you histogram the NRMSE of all physical fits, every detector shows the same picture: two populations. The left one is the good fits, typically five to ten percent. The right one, around one or two, is the noise triggers — traces with no pulse in them at all. In between there's a deep valley, at about zero point four — and that's where I put the threshold. I want to stress: this number wasn't tuned, it's simply what the distribution itself shows. The plot is Z7 PBS1 — the same channel used throughout the talk — where the two populations are far apart and the valley is obvious. The weak detectors — Z22, for example — show the same bimodal picture with the noise peak dominating, and for them this cut is exactly what pulls the real pulses out of the noise.

---

## Slide 7 — The rejected population is noise（约 45 秒）

**中文**：定了 cut 还不够，得验证它切掉的确实是噪声、不是真脉冲。左边是被切掉的事件的**原始**波形——可以看到，里面就没有脉冲，纯粹是噪声，只不过一条很慢的曲线恰好凑在了它上面。右边换个角度看同一件事，这张图有三层：底下灰蓝色的是对齐后的实测波形，上面绿色是**通过** cut 的拟合曲线，红色是**被切掉**的；右上角标着两个群体各自的中位 NRMSE 和事件数。可以看到绿的又快又一致，聚成一束；红的四处发散，中位 NRMSE 是绿的四十倍——1.87 对 0.045。在 Z7 这条通道上，仅仅只有 3.8% 被切掉。结论很明确：这一刀移除的是噪声触发，不损失任何真实脉冲。

**English**: Setting a cut isn't enough — I have to verify that what it removes really is noise, not real pulses. On the left are the **raw** traces of the rejected events. As you can see, there is simply no pulse there — it's pure noise, on which some slow curve happened to converge. On the right, the same thing from another angle — this figure has three layers: the gray-blue underneath is the aligned measured traces, green on top is the fitted curves that **pass** the cut, and red is the ones **removed**; the top-right corner shows each population's median NRMSE and its event count. The green ones are fast and consistent, bundled together; the red ones scatter everywhere, with a median NRMSE about forty times higher — one point eight seven against zero point zero four five. On this Z7 channel, only three point eight percent of the events get cut. So the conclusion is clear: the cut removes noise triggers, and no real pulses are lost.

---

## Slide 8 — Follow-up 1: the slow-fall tail（约 50 秒）

**中文**：第一条线索来自 cut 之后的扇形图：还剩一些"拖尾巴"的曲线，下降特别慢。我的办法是抽样验证：在通过 0.4 的事件里，挑下降时间超过 1.5 毫秒的，随机抽 10 个，把每个事件在全部 12 个通道里的原始波形和拟合画出来对比。结论有两层。第一层：**抽到的这些事件都是真脉冲**——所以保留，我没有为下降时间设任何 cut。第二层，看左边这张图——我特别想强调这一点：**Z7 本身是最好的探测器，但它有一个坏通道，PDS2**。你看每一行是一个事件，除了 PDS2 那一列，其他每一列都是干干净净的快脉冲；唯独 PDS2 这一列，波形上叠着一个大幅度的低频晃动，拟合去追那个晃动，才给出了几毫秒的假"下降时间"。也就是说，慢的不是事件，是 PDS2 这一个通道坏。右边这两张图是同一件事的量化，横轴都是 0 到 20 毫秒，可以直接比：上面是正常通道 PAS1——几乎所有事件都集中在 0.25 毫秒附近，1 毫秒往后基本就没有了；下面是 PDS2——一条明显的宽尾一路拖到五六毫秒，中位数 0.51 毫秒，是正常通道的两倍。所以最夸张的拖尾不是真实的慢脉冲，而是单通道的低频伪影。Z7 整体是最好的探测器，但 PDS2 这一个通道确实坏了。

**English**: The first lead comes from the fan plot after the cut: some curves still have long tails — a very slow fall. My approach was to verify by sampling: among the events that pass the cut, take the ones with a fall time above one and a half milliseconds, randomly sample ten of them, and draw raw versus fit in every one of the twelve channels. The conclusion has two layers. First: **the sampled events are real pulses** — so they stay in, and I apply no fall-time cut at all. Second — and this is the point I really want to make with the left plot: **Z7 is the best detector overall, but it has one bad channel, PDS2**. Each row is one event, and in every column except PDS2 you see a clean, fast pulse; only in the PDS2 column is there a large low-frequency swing riding on top of the trace, and the fit chases that swing, which is what produces the fake fall times of several milliseconds. So it's not the event that's slow — it's that one channel, PDS2, that's misbehaving. The two plots on the right are the same story quantified, on the same zero-to-twenty-millisecond axis so you can compare directly: the top one is a normal channel, PAS1 — almost every event sits in one narrow peak at about 0.25 milliseconds, and there's basically nothing past one millisecond; the bottom one is PDS2 — a broad tail that stretches all the way out to five or six milliseconds, with a median of 0.51 milliseconds, twice that of the normal channel. So the most extreme tails are not a genuinely slow pulse; they're a one-channel low-frequency artifact. Z7 is the best detector overall, and it still has one genuinely bad channel in PDS2.

---

## Slide 9 — Template family 1: 2-exp weighted (1x1)（约 50 秒）

**中文**：现在到产出。第一族模板走解析路线：每个通道，把所有物理拟合的曲线放到同一个 pretrigger 位置，做加权平均——权重是 NRMSE 平方的倒数。这个设计的好处是：拟合差的事件权重自动变得极小，等于被压没了，但我不需要人为剔除任何事件。屏幕上就是参与平均的这束曲线。因为平均的对象是解析函数，做出来的模板天然光滑、完全没有噪声。这就是标准的单模板，1x1。每个通道一条，交付成峰值归一的 32768 点 ROOT 直方图，另外还有把各通道求和得到的 PT、PS1、PS2 模板。

**English**: Now to the deliverables. The first template family takes the analytic route: for each channel, I put all the physical fitted curves at the same pretrigger and take a weighted average — the weight is one over NRMSE squared. The nice property of this design is that badly-fit events automatically get an extremely small weight, so they're effectively suppressed — but I never have to remove anything by hand. What's on screen is the bundle of curves that goes into that average. And because I'm averaging analytic functions, the resulting template is smooth and completely noise-free by construction. That's the standard single template — the one-by-one — delivered as a peak-normalized 32768-bin ROOT histogram per channel, plus the summed PT, PS1 and PS2 templates.

---

## Slide 10 — Template family 2: NxM PCA（约 55 秒）

**中文**：第二族模板是为了捕捉不同事件之间脉冲形状的变化。做法是对干净的拟合曲线做主成分分析，也就是 PCA——输入就是同时通过前面两刀的曲线：NRMSE ≤ 0.4，再加上升时间 ≤ 0.3 毫秒（这刀挡掉慢基线漂移）。直观理解：黑色的 nxm0 是平均形状；后面四条彩色的，是数据里最主要的四个"变形方向"——比如上升更慢一点、下降更快一点。真实脉冲就用这五条的线性组合去拟合。效果非常好：前两个成分就已经覆盖了 96 到 98% 的形状差异。也就是说，事件之间的形状差异，就明明白白地装进了这套模板里。最后一步，交付之前把五条模板统一归一到峰值为 1，方便对比和使用——这就是最终产物。

**English**: The second family is built to capture the variation in pulse shape across events. I run a principal component analysis — PCA — on the curves that pass both cuts: NRMSE ≤ 0.4, plus rise time ≤ 0.3 milliseconds, which removes the slow baseline drift. The intuition: the black curve, nxm-zero, is the average shape; the four colored ones are the four main "directions of deformation" in the data — say, a slightly slower rise, or a faster fall. A real pulse is then fitted as a linear combination of these five. And it works remarkably well: the first two components already cover ninety-six to ninety-eight percent of the shape variation. So the shape variation is built right into the templates. As a final step before delivery, all five templates are normalized to unit peak, so they're easy to compare and use — and that is the final product.

---

## Slide 11 — Delivered, and what remains（约 30 秒）

**中文**：一句话总结：我为全部 13 个探测器做出了两族模板——1x1 和 NxM PCA，都按官方格式交付了。两个 cut 都是从数据里读出来、又回到原始波形验证过的。谢谢大家，欢迎提问。（如被问后续：下一步是对新模板跑一遍组里的验证流程。）

**English**: In one line: I built two template families for all thirteen detectors — the 1x1 and the NxM PCA — and delivered both in the official format. Both cuts were read off the data and verified in the raw traces. Thank you — happy to take questions. (If asked about next steps: run the group's validation procedure on the new templates.)

---

## Backup — Weak detectors（仅备查，不占正片时间）

**中文**：弱探测器（Z1/Z4/Z6/Z18/Z19/Z22/Z24）的 K 线插在噪声堆里，窗口收进来的是噪声为主的混合体。NRMSE 分布同样双峰、但噪声峰是主体，同一条 0.4 的 cut 把真脉冲捞出来——Z22 PCS1：保留 7198、切掉 4788，约四成。保留束比安静探测器宽；红色里那些陡峭曲线是拟合抓到噪声尖刺，不是快脉冲被切掉。τ_rise ≤ 0.3 ms 在弱探测器上再切掉 NRMSE 之后余下的 55–74%（Z22 是 71%），主要是残余的慢基线漂移。

**English**: On the weak detectors (Z1/Z4/Z6/Z18/Z19/Z22/Z24) the K-line sits inside the noise population, so the window admits a noise-dominated mixture. The NRMSE distribution is still bimodal, only with the noise peak dominating, and the same 0.4 cut digs the real pulses out — on Z22 PCS1, 7198 kept and 4788 cut, about forty percent. The kept bundle is broader than on a quiet detector, and the steep red curves are fits latching onto sharp noise spikes, not fast pulses being cut. The rise-time ceiling then removes another 55–74% of what survived the NRMSE cut on the weak zips (71% on Z22) — residual slow baseline drift.

---

## Backup — τ_rise ≤ 0.3 ms 上限（PCA 输入用）（仅备查）

**中文**：慢基线漂移能骗过 NRMSE——一条慢 2-exp 贴住它，残差很小——看起来像慢上升。真快脉冲聚在 τ_rise ≈ 0.1 ms，漂移尾巴拖得远得多，所以 PCA 输入加了 0.3 ms 上限挡掉它。相对 NRMSE 那一步切掉：安静探测器几乎不切（Z7 1.6%，大头是坏通道 PDS2），弱探测器 55–74%（Z22 71%），全部合计 54%。代价是最慢的一小撮真脉冲也会被削掉——这个取舍记录在案、尚未定论。

**English**: A slow baseline drift can fool NRMSE — a slow 2-exp hugs it with a tiny residual — and looks like a slow rise. Real fast pulses cluster at τ_rise ≈ 0.1 ms while the drift tail stretches much further, so the PCA input gets a 0.3 ms ceiling to block it. Relative to the NRMSE step it removes almost nothing on quiet detectors (1.6% on Z7, mostly the bad channel PDS2) but 55–74% on the weak ones (71% on Z22), 54% pooled. The price is that the very slowest genuine pulses get trimmed too — a documented, still-open trade-off.

---

## 可能被问的问题 / Likely questions（回答一两句即可）

**Q1 — 窗口的 1.35 倍是怎么定的？/ How was the 1.35 window factor chosen?**

**中文**：粗略目测定的，故意开得宽——选样阶段宁多勿漏，后面的筛选都是显式、可回退的。

**English**: It was a rough, eyeballed choice, deliberately wide — at the selection stage I'd rather over-collect, since every later cut is explicit and reversible.

**Q2 — 为什么拟合时连 pretrigger 也放开？/ Why is the pretrigger left free in the fit?**

**中文**：真实触发时刻逐事件抖动，拟合显示普遍比名义位置晚两百多个采样点；钉死它会把误差转嫁到上升、下降时间上。

**English**: The true trigger time jitters event by event — the fits sit about two hundred samples after the nominal position — and pinning it pushes that error into the rise and fall times.

**Q3 — 为什么用双指数模型？/ Why the two-exponential model?**

**中文**：一个指数管上升、一个管下降，是声子脉冲的标准形状；好事件的 NRMSE 只有百分之几，说明模型够用。

**English**: One exponential for the rise and one for the fall is the standard phonon pulse shape, and good events fit at the few-percent level — the model is sufficient.

**Q4 — 0.4 这个阈值敏感吗？/ Is the 0.4 threshold sensitive?**

**中文**：不敏感——它取在双峰分布的谷底，谷里本来就没多少事件；交互 notebook 改任意阈值几秒就能重跑。

**English**: No — it sits in the valley of the bimodal distribution, where there are few events by construction, and an interactive notebook re-runs any threshold within seconds.

**Q5 — 为什么不用实测波形的平均做模板？/ Why not average the measured traces?**

**中文**：解析拟合曲线本身没有噪声，加权平均出来的模板天然光滑；NRMSE 权重让拟合差的事件自动降权。

**English**: The analytic fitted curves carry no noise, so their weighted mean is smooth by construction, and the NRMSE weight down-weights badly-fit events automatically.

**Q6 — 两族模板的 cut 为什么不一样？/ Why do the two families apply cuts differently?**

**中文**：1x1 靠权重（NRMSE 0.05 和 2 的权重差四个数量级，噪声自动压没）；PCA 对离群点敏感，一条噪声曲线就能污染主成分，所以 NxM 的输入必须硬切干净。

**English**: The 1x1 relies on weighting — NRMSE 0.05 versus 2 differ by four orders of magnitude in weight, so noise is suppressed automatically — while PCA is outlier-sensitive, so the NxM input must be hard-cut clean.

**Q7 — τ_rise ≤ 0.3 ms 相对上一步切掉多少？/ How much does the rise-time ceiling remove, after the NRMSE cut?**

**中文**：安静探测器几乎不切——Z7 只有 1.6%，大头还是坏通道 PDS2（21%）；弱探测器切 55–74%（Z22 是 71%），切掉的是残余慢漂移。

**English**: Almost nothing on the quiet detectors — 1.6% on Z7, mostly the bad channel PDS2 at 21% — versus 55–74% on the weak ones (71% on Z22), and what it removes is residual slow drift.

**Q8 — 真正的慢脉冲留不留？/ Do the genuine slow pulses stay?**

**中文**：这是记录在案的待定事项：目前 PCA 输入应用了 τ_rise cut，要不要放开这个取舍，正想和大家讨论。

**English**: That's the documented open item — the PCA input currently applies the rise-time cut, and whether to relax that trade-off is exactly what I'd like to discuss.

**Q9 — Z7 的坏通道 PDS2 怎么处理的？/ What about the bad channel PDS2 on Z7?**

**中文**：没有剔除——每个通道都用自己的拟合出自己的模板；PDS2 的低频晃动主要抬高拟合的下降时间，NRMSE 权重会自动压低受影响最重的事件。

**English**: It's not excluded — every channel gets its own template from its own fits; the low-frequency swing mainly inflates fitted fall times, and the NRMSE weighting automatically suppresses the worst-affected events.

**Q10 — 下一步是什么？/ What's next?**

**中文**：对新模板跑一遍组里的模板验证流程，再定慢脉冲那个取舍。

**English**: Run the group's template-validation procedure on the new templates, then settle the slow-pulse trade-off.

---

## 术语自查表（只给自己，不进 PPT）

> 过一遍下面每一行；哪一条还觉得说不清楚，提前告诉我，我把它从幻灯片里去掉或换个说法。

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
| pretrigger / onset 16050 | 波形里名义的触发位置（第 16050 个采样点）；我把它当自由参数拟合 |
| NRMSE | 拟合残差的 RMS ÷ 拟合脉冲峰值；无量纲的"拟合好坏"指标 |
| fit_ok | 物理性检查：幅度为正且 τ_rise < τ_fall |
| 亚采样插值对齐 | 平移量不是整数个采样点时用线性插值（np.interp）实现的平移 |
| PCA | 主成分分析：把一堆曲线分解成"均值 + 按方差大小排序的正交变化方向" |
| explained variance | 每个主成分解释的形状方差占比；PC1+PC2 = 96–98% |
| TH1D | ROOT 软件的一维直方图对象；模板的交付格式（32768 个 bin） |
| cdmsbats / PulseTemplates | 官方处理软件 / 它读取模板的配置目录和文件命名规范 |
| PT / PS1 / PS2 | 求和模板：全部通道之和、S1 面之和、S2 面之和（各自峰值归一） |
