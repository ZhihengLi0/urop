# Speaker Script / 演讲稿 — SNOLAB R4 Phonon Pulse Templates

约 9 分钟，11 页 + 1 页 backup（弱探测器 Z22 示例，不占正片时间）。每页先中文、后英文，内容一一对应，**英文可以直接照读**。
原则：稿子是说的话，不是幻灯片的复读——具体参数都在屏幕上，嘴里讲思路和为什么。
斜体是给自己的提示，不用念。

---

## Slide 1 — Title（约 30 秒）

**中文**：大家下午好。今天讲我为 SNOLAB Run 4 做的声子脉冲模板。简单说，就是给 13 个探测器的每个声子通道做出一个"标准脉冲形状"，给 optimal filter 用。我按实际做的顺序讲：事件怎么选的，波形怎么拟合和对齐的，两个质量 cut 是怎么从数据里定出来的，最后是交付的两族模板。

**English**: Good afternoon everyone. Today I'll talk about the phonon pulse templates I built for SNOLAB Run 4. In short: for each phonon channel of thirteen detectors, I build a standard pulse shape for the optimal filter to use. I'll go in the order I actually did the work: how the events were selected, how each trace is fitted and aligned, how the two quality cuts were derived from the data itself, and finally the two template families I delivered.

---

## Slide 2 — Table of Contents（约 15 秒）

**中文**：快速过一下路线图：数据集和选样、拟合与对齐、两道清洗 cut 和背后的核查、两族模板、交付与下一步；backup 里有弱探测器和每个 zip 的全套结果。

**English**: A quick roadmap: the dataset and selection, the fit and alignment, the two cleaning cuts and the checks behind them, the two template families, deliverables and future steps; the backups hold the weak detectors and the full results for every zip.

---

## Slide 3 — Ge activation dataset - R4（约 65 秒）

**中文**：先说事件从哪来。做模板需要一大批干净、彼此相同的脉冲。我用的是 Ge 活化 K 线：Cf 活化之后，每个探测器里都会持续出现 10.37 keV 的单能事件，这是现成的理想样本。屏幕上是 13 个探测器的 PTOFamps 谱。每格里的红线，是 Saab 教授的分析标出来的 K 线位置，我直接拿来用。我做的事情非常简单：以红线为中心开一个窗，上下各 1.35 倍——这个倍数是粗略目测定的，带点随意性，反正开得够宽就行——窗内的事件全要，不加任何别的条件。然后把每个选中事件所有通道的原始波形，原封不动存下来。大家看这些谱：安静的探测器比如 Z7，K 线峰和噪声峰分得很开；但不少噪声大的探测器，红线就插在噪声堆里——窗口一开，噪声肯定跟着进来。这是故意的：我宁愿先多收，也要让后面每一步筛选清清楚楚、随时可以回退——因为存的是原始数据，什么都没丢。

**English**: Let me start with where the events come from. To build a template, you need a large sample of clean, identical pulses. I use the germanium activation K-line: after the californium activation, every detector keeps producing mono-energetic events at 10.37 keV — a perfect, ready-made sample. What you see here are the PTOFamps spectra of all thirteen detectors. The red line in each panel is the K-line position marked by Professor Saab's analysis, and I simply take that as given. What I do is very simple: open a window around the red line, a factor of one point three five on each side — a rough, eyeballed choice; it just needs to be wide enough — keep everything inside, and apply no other condition. Then, for every selected event, I save the raw traces of all channels, completely untouched. Now look at the spectra: on a quiet detector like Z7, the K-line peak is well separated from the noise peak. But on the weaker detectors, the red line sits right inside the noise population — so the window will let noise in. And that's deliberate. I'd rather collect too much, and keep every later selection explicit and reversible — nothing is lost, because what I stored is raw.

---

## Slide 4 — Fit quality at a glance / data overview（约 40 秒）

**中文**：先看单个事件层面，拟合到底靠不靠谱。网格图里一行是一个事件、一列是一个通道，蓝色是滤波后的波形，红色是拟合。通过肉眼对比就能把两类分开：左边这批是噪声触发，右边是真正的 K 线事件。这一步我们还没有做任何 cut，也不下"哪个拟合成功哪个失败"的结论——一个事件也不一定在所有通道里都好或都坏。

**English**: First, a sanity check at the level of individual events. In these grids, each row is one event and each column is one channel — blue is the filtered trace, red is the fit. By visual comparison you can already tell the two kinds apart: the left block is noise triggers, the right block is true K-line events. No cut is applied at this stage, and we do not label individual fits as pass or fail here — an event is not necessarily good or bad in every channel at once.

---

## Slide 5 — Per-trace algorithm（约 80 秒）

**中文**：拿到原始波形后，每一条都过同样的五步。完整参数都在屏幕上，我挑重点讲。前三步是准备：低通滤波抹掉高频噪声，扣基线，按峰值归一。核心是第四步的拟合：一个双指数函数，一个指数管上升、一个管下降——这是声子脉冲的标准形状。重点在于，五个拟合参数里，连 pretrigger——脉冲的起始时刻——也是放开的。为什么？因为真实触发时刻每个事件都不一样。如果把它钉死，这个误差就会被转嫁到上升、下降时间上，把所有参数都带歪。拟合完，每条波形记两个质量指标：一个叫 fit_ok，检查参数物不物理——幅度得是正的，上升得比下降快；另一个叫 NRMSE，全称 Normalized Root-Mean-Square Error，归一化均方根误差——就是拟合残差除以脉冲峰值，衡量拟合得好不好。举个例子，NRMSE 等于 0.05，意思就是拟合偏差只有脉冲高度的 5%。注意，这一步只记录、不筛选。

**English**: Once I have the raw traces, every single one goes through the same five steps — the full parameters are on the slide, so let me just walk through the ideas. The first three steps are preparation: a low-pass filter to smooth away high-frequency noise, baseline subtraction, and normalization to the peak. The core is the fit: a two-exponential function — one exponential for the rise, one for the fall — which is the standard shape of a phonon pulse. And here's the important part: among the five fit parameters, even the pretrigger — the pulse start time — is left free. Why? Because the true trigger time is different for every event. If you pin it, that error gets pushed into the rise and fall times, and everything comes out biased. After the fit, each trace gets two quality checks. One is called fit_ok — a sanity check that the parameters are physical: positive amplitude, rise faster than fall. The other is the NRMSE — the normalized root-mean-square error — which is simply the fit residual divided by the pulse height, so it tells you how good the fit actually is. For example, an NRMSE of 0.05 means the fit misses the data by 5% of the pulse height. At this stage I only record these; I don't cut on them yet.

---

## Slide 6 — Alignment result（约 40 秒）

**中文**：这一页讲第五步——对齐。每一条实测波形，按它自己拟合出的 pretrigger 减去名义的 16050 平移——纯平移，波形本身没有任何再生成。图里那条竖虚线，就是所有波形对齐到的公共 pretrigger。对齐之后，把所有拟合曲线画在这个公共起点上，就是这张扇形图——这一页画的是这个通道**全部**拟合出来的事件，2008 条曲线，没有 fit_ok、没有 NRMSE、什么 cut 都没有，因为到这里我们还没有做任何筛选。可以看到占主体的快脉冲束，和散开的慢曲线；怎么定量把它们分开，是下一页的事。

**English**: This slide is step five — alignment. Each measured trace is shifted by its own fitted pretrigger minus 16050 — a pure translation, nothing about the waveform is regenerated. The dotted vertical line is the common pretrigger everything is aligned to. Once aligned, I draw all the fitted curves from that common starting point — this fan plot shows **every** fitted event on this channel, 2008 curves, with no fit_ok, no NRMSE, no cuts of any kind, because at this point nothing has been selected yet. You can see the dominant fast bundle and the stragglers spreading off it; separating them quantitatively is the next slide.

---


## Slide 7 — Quality cut 1: NRMSE ≤ 0.4（约 55 秒）

**中文**：现在讲第一个 cut 怎么定的。把所有物理拟合的 NRMSE 画成分布，每个探测器都是同一个样子：两个峰。左边的峰是拟合好的，典型值百分之五到百分之十；右边就是噪声。两峰之间有一个很深的谷，位置在 0.4 左右——阈值就取 0.4。我想强调：这个数不是调出来的，是分布自己长出来的。图里是 Z7 的 PBS1——全场用的就是这条通道——两个峰离得很远，谷一目了然。较弱的探测器——比如 Z22——是同样的双峰图景，只是噪声峰是主体，对它们来说这一刀就是把真脉冲从噪声堆里捞出来的那一刀。*（有人问弱探测器长什么样，再翻 backup 页。）*

**English**: Now, how the first cut was set. If you histogram the NRMSE of all physical fits, every detector shows the same picture: two populations. The left one is the good fits, typically five to ten percent. On the right it is noise. In between there's a deep valley, at about zero point four — and that's where I put the threshold. I want to stress: this number wasn't tuned, it's simply what the distribution itself shows. The plot is Z7 PBS1 — the same channel used throughout the talk — where the two populations are far apart and the valley is obvious. The weak detectors — Z22, for example — show the same bimodal picture with the noise peak dominating, and for them this cut is exactly what pulls the real pulses out of the noise.

---

## Slide 8 — Aligned curves before vs after the NRMSE cut（约 25 秒）

**中文**：定了 0.4 之后回头看扇形图：左边是全部物理拟合（画了 200 条抽样，慢曲线按真实占比出现）；右边是 cut 之后，只剩一束非常紧、非常一致的形状。正是这条紧致的束，让一个定义清楚、稳定的模板成为可能。

**English**: With the 0.4 threshold set, back to the fan: on the left all physical fits — a 200-curve sample, so the slow stragglers appear in proportion to their real share; on the right, after the cut, one very tight, consistent shape family remains. That tight family is what makes a well-defined, stable template possible.

---

## Slide 9 — The rejected population is noise（约 45 秒）

**中文**：定了 cut 还不够，得验证它切掉的确实是噪声、不是真脉冲。左边是被切掉的事件的**原始**波形——可以看到，里面就没有脉冲。但还是有一条很慢的曲线恰好凑在了它上面。右边换个角度看同一件事，这张图有三层：底下灰蓝色的是对齐后的实测波形，上面绿色是**通过** cut 的拟合曲线，红色是**被切掉**的；右上角标着两个群体各自的中位 NRMSE 和事件数。可以看到绿的又快又一致，聚成一束；红的四处发散，中位 NRMSE 是绿的四十倍。在 Z7 这条通道上，仅仅只有 3.8% 被切掉。结论很明确：这一刀移除的是噪声触发，不损失任何真实脉冲。PDS2 单独做不出可用的模板；这在分析/软件层面很难修，需要修的是噪声本身。临时方案：用 PDS1 的模板顶替 PDS2，交付的 ROOT 文件里已经这样替换。

**English**: Setting a cut isn't enough — I have to verify that what it removes really is noise, not real pulses. On the left are the **raw** traces of the rejected events. As you can see, there is simply no pulse there. But some slow curve still happened to converge on it. On the right, the same thing from another angle — this figure has three layers: the gray-blue underneath is the aligned measured traces, green on top is the fitted curves that **pass** the cut, and red is the ones **removed**; the top-right corner shows each population's median NRMSE and its event count. The green ones are fast and consistent, bundled together; the red ones scatter everywhere, with a median NRMSE about forty times higher. On this Z7 channel, only 3.8% of the events get cut. So the conclusion is clear: the cut removes noise triggers, and no real pulses are lost. PDS2 alone cannot make a useful template; this is hard to fix in analysis or software, the noise itself needs fixing. Temporary solution: use the PDS1 template in place of PDS2 - the substitution is applied in the delivered ROOT files.

---

## Slide 10 — Follow-up 1: the slow-fall tail（约 50 秒）

**中文**：第一条线索来自 cut 之后的扇形图：还剩一些"拖尾巴"的曲线，下降特别慢。我的办法是抽样验证：在通过 0.4 的事件里，挑下降时间超过 1.5 毫秒的，随机抽 10 个，把每个事件在全部 12 个通道里的原始波形和拟合画出来对比。结论有两层。第一层：**抽到的这些事件都是真脉冲**——所以保留，我没有为下降时间设任何 cut。第二层——我特别想强调这一点：**Z7 本身是最好的探测器，但它有一个坏通道，PDS2**。你看每一行是一个事件，除了 PDS2 那一列，其他每一列都是干干净净的快脉冲；唯独 PDS2 这一列，波形上叠着一个大幅度的低频晃动，拟合就去追那个晃动。这才给出了几毫秒的假"下降时间"。要说清楚的是：这个"慢"是 hardware 那边噪音大导致的——拟合显示出来的是一个很长的时间长度，但它真实反映的不是脉冲变慢，而是这条通道噪音太大的问题。也就是说，慢的不是事件，是 PDS2 这一个通道坏。右边这两张图也证明了这一点。它们的横轴一样，可以直接比：其中左边是正常通道 PAS1——几乎所有事件都集中在 0.25 毫秒附近，1 毫秒往后基本就没有了；右边是 PDS2——一条明显的宽尾一路拖到五六毫秒，中位数 0.51 毫秒，是正常通道的两倍。所以最夸张的拖尾不是真实的慢脉冲，而是单通道的低频伪影。Z7 整体是最好的探测器，但 PDS2 这一个通道确实坏了。

**English**: The first lead comes from the fan plot after the cut: some curves still have long tails — a very slow fall. My approach was to verify by sampling: among the events that pass the cut, take the ones with a fall time above one and a half milliseconds, randomly sample ten of them, and draw raw versus fit in every one of the twelve channels. The conclusion has two layers. First: **the sampled events are real pulses** — so they stay in, and I apply no fall-time cut at all. Second — and this is the point I really want to make: **Z7 is the best detector overall, but it has one bad channel, PDS2**. Each row is one event, and in every column except PDS2 you see a clean, fast pulse; only in the PDS2 column is there a large low-frequency swing riding on top of the trace, and the fit chases that swing. And that is what produces the fake fall times of several milliseconds. To be clear about what this means: the slowness comes from large noise on the hardware side — the fit displays it as a long time constant, but what it really reflects is not a slow pulse, it is how large the noise is in that channel. So it's not the event that's slow — it's that one channel, PDS2, that's misbehaving. The two plots on the right also prove this. They share the same axis, so you can compare them directly: the left one is a normal channel, PAS1 — almost every event sits in one narrow peak at about 0.25 milliseconds, and there's basically nothing past one millisecond; the right one is PDS2 — a broad tail that stretches all the way out to five or six milliseconds, with a median of 0.51 milliseconds, twice that of the normal channel. So the most extreme tails are not a truly slow pulse; they're a one-channel low-frequency artifact. Z7 is the best detector overall, and it still has one really bad channel in PDS2.

---

## Slide 11 — Template family 1: 2-exp weighted (1x1)（约 50 秒）

**中文**：现在到产出。第一族模板走解析路线：每个通道，把所有物理拟合的曲线放到同一个 pretrigger 位置，做加权平均——权重是 NRMSE 平方的倒数。这个设计的好处是：拟合差的事件权重自动变得极小，等于被压没了，但我不需要人为剔除任何事件。屏幕上蓝色的那**一束**是参与平均的拟合曲线——这是原料，不是模板；红色**那一条**才是它们加权平均之后的结果，也就是真正交付的 1x1 模板，这条线是直接从交付的 ROOT 文件里读回来画上去的。因为平均的对象是解析函数，做出来的模板天然光滑、完全没有噪声。这就是标准的单模板，1x1。每个通道一条，交付成峰值归一的 ROOT 直方图，另外还有把各通道求和得到的 PT、PS1、PS2 模板。

**English**: Now to the deliverables. The first template family takes the analytic route: for each channel, I put all the physical fitted curves at the same pretrigger and take a weighted average — the weight is one over NRMSE squared. The nice property of this design is that badly-fit events automatically get an extremely small weight, so they're effectively suppressed — but I never have to remove anything by hand. On the screen, the blue **bundle** is the fitted curves that go into the average — that's the input, not the template. The **single** red curve is the result of averaging them: the 1x1 template we actually deliver, read back from the delivered ROOT file and drawn on top. And because I'm averaging analytic functions, the resulting template is smooth and completely noise-free by construction. That's the standard single template — the one-by-one — delivered as a peak-normalized ROOT histogram per channel, plus the summed PT, PS1 and PS2 templates.

---

## Slide 12 — Template family 2: NxM PCA（约 55 秒）

**中文**：第二族模板是为了捕捉不同事件之间脉冲形状的变化。先看页面上方的两张图：左边是 NRMSE 加权平均——就是上一页交付的 1x1 模板；右边是对 PCA 输入的干净曲线做不加权的直接平均——这正是 nxm0。两条曲线几乎重合，虚线是对方，方便对比。下面进入正题。做法是对干净的拟合曲线做主成分分析，也就是 PCA——输入就是同时通过前面两刀的曲线：NRMSE ≤ 0.4，再加上升时间 ≤ 0.3 毫秒（这刀挡掉慢基线漂移）。直观理解：黑色的 nxm0 是平均形状；后面四条彩色的，是数据里最主要的四个"变形方向"——比如上升更慢一点、下降更快一点。真实脉冲就用这五条的线性组合去拟合。效果非常好：前两个成分就已经覆盖了 96 到 98% 的形状差异。也就是说，事件之间的形状差异，就明明白白地装进了这套模板里。最后一步，交付之前把五条模板统一归一到峰值为 1，方便对比和使用——这就是最终产物。

**English**: The second family is built to capture the variation in pulse shape across events. First, the two plots on top: on the left, the NRMSE-weighted mean — that is the 1x1 template delivered on the previous slide; on the right, the plain unweighted mean of the clean PCA input curves — and that is exactly nxm0. The two are almost identical; the dashed line in each panel is the other one, for comparison. Now the main part. I run a principal component analysis — PCA — on the curves that pass both cuts: NRMSE ≤ 0.4, plus rise time ≤ 0.3 milliseconds, which removes the slow baseline drift. The intuition: the black curve, nxm-zero, is the average shape; the four colored ones are the four main "directions of deformation" in the data — say, a slightly slower rise, or a faster fall. A real pulse is then fitted as a linear combination of these five. And it works remarkably well: the first two components already cover ninety-six to ninety-eight percent of the shape variation. So the shape variation is built right into the templates. As a final step before delivery, all five templates are normalized to unit peak, so they're easy to compare and use — and that is the final product.

---

## Slide 13 — Template file / Future steps（约 30 秒）

**中文**：两套模板都做好了，覆盖全部 13 个探测器：解析的 1x1 模板和 PCA 的 NxM 模板，官方 PulseTemplates 格式，放在 cdmsbats_config 的 feature branch 里，随时可以 merge。下一步：扩展到三指数、四指数拟合；把 NxM 处理链真正跑起来；其他探测器噪声更差、多加了几个 cut，细节都在 backup slides 里——如果大家有兴趣，我可以讲一讲 backup slides。

**English**: Both template sets are ready for all 13 detectors: the analytic 1x1 templates and the PCA NxM set, in the official PulseTemplates format, sitting in the cdmsbats_config feature branch and ready for merge. Next: extend to three- and four-exponential fits, exercise the NxM processing chain, and the other detectors — worse noise, a few more cuts, all in the backup slides. If anyone is interested, I am happy to walk through the backup slides.

---

## Backup — Weak detectors（仅备查，不占正片时间）

**中文**：弱探测器（Z1/Z4/Z6/Z18/Z19/Z22/Z24）的 K 线插在噪声堆里，窗口收进来的是噪声为主的混合体。NRMSE 分布同样双峰、但噪声峰是主体，同一条 0.4 的 cut 把真脉冲捞出来——Z22 PCS1：保留 7198、切掉 4788，约四成。保留束比安静探测器宽；红色里那些陡峭曲线是拟合抓到噪声尖刺，不是快脉冲被切掉。τ_rise ≤ 0.3 ms 在弱探测器上再切掉 NRMSE 之后余下的 55–74%（Z22 是 71%），主要是残余的慢基线漂移。

**English**: On the weak detectors (Z1/Z4/Z6/Z18/Z19/Z22/Z24) the K-line sits inside the noise population, so the window admits a noise-dominated mixture. The NRMSE distribution is still bimodal, only with the noise peak dominating, and the same 0.4 cut digs the real pulses out — on Z22 PCS1, 7198 kept and 4788 cut, about forty percent. The kept bundle is broader than on a quiet detector, and the steep red curves are fits latching onto sharp noise spikes, not fast pulses being cut. The rise-time ceiling then removes another 55–74% of what survived the NRMSE cut on the weak zips (71% on Z22) — residual slow baseline drift.

---

## Backup — τ_rise ≤ 0.3 ms 上限（PCA 输入用）（仅备查）

**中文**：慢基线漂移能骗过 NRMSE——一条慢 2-exp 贴住它，残差很小——看起来像慢上升。真快脉冲聚在 τ_rise ≈ 0.1 ms，漂移尾巴拖得远得多，所以 PCA 输入加了 0.3 ms 上限挡掉它。相对 NRMSE 那一步切掉：安静探测器几乎不切（Z7 1.6%，大头是坏通道 PDS2），弱探测器 55–74%（Z22 71%），全部合计 54%。代价是最慢的一小撮真脉冲也会被削掉——这个取舍记录在案、尚未定论。

**English**: A slow baseline drift can fool NRMSE — a slow 2-exp hugs it with a tiny residual — and looks like a slow rise. Real fast pulses cluster at τ_rise ≈ 0.1 ms while the drift tail stretches much further, so the PCA input gets a 0.3 ms ceiling to block it. Relative to the NRMSE step it removes almost nothing on quiet detectors (1.6% on Z7, mostly the bad channel PDS2) but 55–74% on the weak ones (71% on Z22), 54% pooled. The price is that the very slowest real pulses get trimmed too — a documented, still-open trade-off.

---

## Backup — τ_rise cut：好通道 vs 坏通道（Z7）（仅备查）

**English**: This is the τ_rise cut channel by channel on Z7. On the good channel PBS1 the fitted curves are already a tight, clean bundle, and adding the 0.3 ms ceiling changes essentially nothing — it removes about zero percent. On the bad channel PDS2 the fan is broad and messy, which by itself shows the channel is bad; there the ceiling trims the slow-rising curves, 1462 down to 1154, about 21%. So the cut is nearly free where the data is clean and does real work only where a channel is bad.

**中文**：这是 τ_rise 这刀在 Z7 上分通道看。好通道 PBS1 本来就是又紧又干净的一束，加上 0.3 ms 上限几乎没变——切了约 0%。坏通道 PDS2 的扇形又宽又乱，这本身就说明通道坏了；那刀在这里切掉了慢上升的曲线，1462 降到 1154，约 21%。所以这刀在干净数据上近乎免费，只在通道坏的地方才真干活。

---

## Backup — τ_rise 切掉的是什么：慢漂移（Z22）（仅备查）

**English**: What the rise-time cut actually removes. These are exactly the Z22 events that pass the NRMSE cut — median NRMSE below 0.4 — but are removed by the rise-time ceiling, median t_rise above 0.3 ms. In other words, the noise that 0.4 let through and 0.3 catches. Look at PCS1 and PDS1: their NRMSE is low, around 0.15, because a slow 2-exp hugs the trace with a tiny residual — but the raw trace is just a slow baseline drift, there is no clean fast pulse. The honest caveat: the same cut also trims a small number of real slow-rise pulses — the documented, still-open trade-off.

**中文**：这刀实际切掉的是什么。这些正是 Z22 上"通过了 NRMSE（中位 < 0.4）、却被上升时间上限（中位 t_rise > 0.3 ms）切掉"的事件——也就是 0.4 放过、0.3 才抓住的那批噪声。看 PCS1 和 PDS1：它们 NRMSE 很低、约 0.15，因为慢 2-exp 用极小残差贴住了波形——但原始波形就是一条慢基线漂移，没有干净的快脉冲。老实说的代价：这刀也会削掉一小撮真实的慢上升脉冲——就是那个记录在案、尚未定论的取舍。

---

## 可能被问的问题 / Likely questions（回答一两句即可）

**Q1 — 窗口的 1.35 倍是怎么定的？/ How was the 1.35 window factor chosen?**

**中文**：粗略目测定的，故意开得宽——选样阶段宁多勿漏，后面的筛选都是显式、可回退的。

**English**: It was a rough, eyeballed choice, deliberately wide — at the selection stage I'd rather over-collect, since every later cut is explicit and reversible.

**Q2 — 为什么拟合时连 pretrigger 也放开？/ Why is the pretrigger left free in the fit?**

**中文**：真实触发时刻逐事件抖动，拟合显示普遍比名义位置晚两百多个采样点；钉死它会把误差转嫁到上升、下降时间上。

**English**: The true trigger time jitters event by event — the fits sit about two hundred samples after the nominal position — and pinning it pushes that error into the rise and fall times.

**Q2b — fit_ok 为什么要求 rise 比 fall 快？/ Why does fit_ok require the rise to be faster than the fall?**

**中文**：这是物理性质决定的：上升时间由 L/R 决定，是读出电路的电学性质；下降时间由 C/G 决定，是探测器的热学性质。物理上电学的上升沿本来就比热学的衰减快，所以反过来的拟合不是物理脉冲。

**English**: It follows from the physics: the rise time is set by L/R, an electrical property of the readout circuit, while the fall time is set by C/G, a thermal property of the detector. Physically the electrical rise is faster than the thermal decay, so a fit with the opposite ordering is not a physical pulse.

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

**Q8 — 真正的慢脉冲留不留？/ Do the real slow pulses stay?**

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
