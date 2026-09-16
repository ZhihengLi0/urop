# Speaker Script / 演讲稿 — Z7 Phonon Collection Efficiency

约 13 分钟，12 页正片 + 6 页 backup。每页先中文、后英文，内容一一对应，**英文可以直接照读**。
稿子是说的话，不是幻灯片的复读：数字都在屏幕上，嘴里讲思路。斜体是给自己的提示，不用念。**加粗的英文**是指着屏幕说的那几句。

整条逻辑就一句话：**一个脉冲怎么读成能量，然后把这个读法用到所有通道、所有事件。**
时间分配（秒）：1 题目 20 · 2 问题 55 · 3 公式来历 75 · 4 公式 45 · 5 主图总览 50 · 6 峰高 95 · 7 功率和面积 85 · 8 拟合不积 raw 80 · 9 其他通道 55 · 10 所有事件 65 · 11 求和 95 · 12 总结 45 → 约 765 秒。

---

## Slide 1 — Title（约 20 秒）

**中文**：大家好。今天讲 Z7 的声子收集效率：一个 10.37 keV 的事件打进晶体，最后有多少能量真的到了 TES 里。答案是 32%，正负 1。我的讲法是先盯着一个脉冲，把它怎么读成能量讲清楚，再把同样的读法推到整个探测器。

**English**: Hi everyone. Today is about the phonon collection efficiency of Z7: when a 10.37 keV event happens in the crystal, how much of that energy actually ends up in the TESs. The answer is 32 percent, plus or minus one. The way I'll do it is to stay with one single pulse first and make clear how it is read as an energy, and then apply the same reading to the whole detector.

---

## Slide 2 — The question（约 55 秒）

**中文**：先把问题定义好。对于在 0 伏下工作的探测器，也就是没有 NTL 放大的情况，收集效率就是 TES 吸收的能量除以事件放进晶体的 10.37 keV。这里的能量是所有通道加起来的总和。强调 0 伏，是因为加了偏压以后，电子空穴在电场里漂移会额外产生声子，这就是 NTL 效应，那时候晶体里的总能量就不止 10.37 keV 了。屏幕上这条链就是全部流程：晶体里的能量，声子到达 TES 薄膜，我们记录到电流脉冲 δI，把它换算成功率的变化 δP，δP 积分得到一个通道的能量，所有通道加起来，最后除以 10.37 keV。样本是 SNOLAB R4 里 Z7 的 Ge 活化 K 线事件，30 个 series，2207 个事件，每个事件 11 个通道。Z7 是最安静的探测器，K 线峰和噪声分得很开，所以这批事件能量完全一样、又干净。

**English**: First the definition. **For a detector operated at zero volts, so with no NTL amplification, the collection efficiency is the energy absorbed by the TESs divided by the 10.37 keV the event put into the crystal,** where the energy is summed over all channels. The zero volts matters: with a bias, the electrons and holes drifting in the field make extra phonons, that is the NTL effect, and then the crystal holds more than 10.37 keV. **The chain on the screen is the whole procedure:** energy in the crystal, phonons reach the TES films, we record a current pulse delta I, we convert it into a change of power, delta P, the integral of delta P is the energy in one channel, we add up all the channels, and divide by 10.37 keV. The sample is the germanium-activation K-line events on Z7 from SNOLAB R4: thirty series, 2207 events, eleven channels each. Z7 is the quietest detector and its K line is well separated from the noise, so these events are clean and all have the same energy.

---

## Slide 3 — Where the formula comes from（约 75 秒）

*老师要求把公式讲明白，这一页慢慢讲，左边电路右边五步。*

**中文**：先说这个公式是怎么来的。左边是电路：一个电压源、固定的负载电阻 R_L、线圈 L，和 TES 串成一个回路。R_L 是 Rp 加 Rsh，是定值；唯一会变的是 TES 的电阻，事件一来薄膜被加热，它就升高。电阻升高，回路里的电流就下降，这个下降量就是我们记录的 δI。关键在于：电流下降以后，TES 上的焦耳热 I 乘 V_TES 也跟着下降，而下降掉的这部分，正好就是事件送进来的功率。这叫负电热反馈 —— 薄膜是用自己的焦耳热给事件"付账"的。右边是五步。第一步，薄膜的热流方程：热容乘温度变化率，等于事件功率加焦耳热减去流向热浴的功率。第二步，脉冲结束以后薄膜回到原来的工作点，所以热容那一项整脉冲积下来是零，于是事件能量就等于负的焦耳功率变化的积分。第三步，用回路写出 TES 上的电压和它的焦耳功率。第四步，把电流写成 I₀ 加 δI 代进去展开，得到三项。第五步，整脉冲积分：电感那一项在两个端点上相互抵消，电压源用工作点表示成 I₀ 乘 R_L 加 R₀，剩下的就是那个公式 —— 一个线性项加一个二次项，系数只含 I₀、R₀、R_L。有两项我们没有算进去：流向热浴的泄漏和电感的边界项，它们需要 dI/dV 给出的 G 和 L，这些 series 上没有 dI/dV 数据。

**English**: Let me show where the formula comes from. **On the left is the circuit:** a voltage source, the fixed load resistance R_L, the coil, and the TES, all in one loop. R_L is R p plus R shunt and it is a constant; the only thing that changes is the resistance of the TES, which rises when an event heats the film. **When the resistance rises, the current in the loop falls, and that fall is the delta I we record.** And here is the key point: once the current falls, the Joule heating on the TES, I times V TES, falls as well — and the part that disappears is exactly the power the event delivered. That is negative electro-thermal feedback: the film pays for the event out of its own Joule heating. **On the right are the five steps.** One, the heat flow in the film: heat capacity times the rate of temperature change equals the event power plus the Joule heating minus the power flowing to the bath. Two, after the pulse the film comes back to the same operating point, so the heat capacity term integrates to zero over the whole pulse, and the event energy is then minus the integrated change of the Joule power. Three, the loop gives the voltage on the TES and its Joule power. Four, write the current as I zero plus delta I and expand; you get three terms. Five, integrate over the pulse: the inductor term cancels between the two ends, the source voltage is I zero times R L plus R zero, and what is left is the formula — one linear term and one quadratic term, with coefficients made only of I zero, R zero and R L. Two things are not included: the leak to the bath and the inductor end terms. Both need G and L from a dI/dV measurement, and these series have none.

---

## Slide 4 — The formula, and the two numbers it needs（约 45 秒）

**中文**：换算公式就这一行。δP 是电流变了 δI 之后焦耳热的变化量，写出来是一个线性项加一个二次项，这就是上一页推导的结果，也是 CDMS 收集效率文档里的 method 1。两个系数都来自这个通道的偏置点：I0、R0 和负载电阻。以 PBS1 为例，线性项系数是 0.45 微伏，二次项系数是 0.0385 欧姆。第二行是能量：拟合出双指数以后，δP 的积分有解析式，能量就是幅度 A 和两个时间常数的一个公式，代进去就行。这一点后面会反复用到。

**English**: The conversion is this one line. **Delta P is the change in Joule heating when the current moves by delta I, and it comes out as a linear term plus a quadratic term** — the result of the previous slide, and Method 1 of the CDMS collection-efficiency note. Both coefficients come from the bias point of that channel: I zero, R zero and the load resistance. **For PBS1 the linear coefficient is 0.45 microvolts and the quadratic one is 0.0385 ohms.** The second line is the energy: once the two-exponential is fitted, the integral of delta P has a closed form, so the energy is just a formula in the amplitude A and the two time constants. We will lean on that repeatedly.

---

## Slide 5 — Example: one pulse（约 50 秒）

**中文**：下面用一个例子。一个通道 PBS1，一个事件 30646，只放大脉冲附近 1.3 毫秒。副标题加粗的那句就是这页的意思：同一条波形，可以读成 ADC 计数，读成电流，读成功率。上半部分是脉冲本身，有三条纵轴：左边是减掉基线的 ADC 计数，也就是仪器直接记下来的数；右边第一条是微安，1 个 ADC 等于 0.318 纳安；右边第二条是飞瓦，用刚才的公式换算的。下半部分是对应的功率。先回答一个问题：双指数拟合是在哪条曲线上做的？是在 100 kHz 低通之后的波形上，也就是蓝线，不是原始采样点。原始采样点只是画出来对照。下面两页分别把上下两部分讲清楚。

**English**: Now an example. One channel, PBS1, one event, 30646, zoomed in on 1.3 milliseconds around the pulse. **The bold part of the subtitle is the point of this slide: the same trace, read as ADC counts, as current, and as power.** The top panel is the pulse itself, with three vertical axes: on the left ADC counts above the baseline, which is what the instrument records; on the first right axis microamps, one ADC being 0.318 nanoamps; on the second right axis femtowatts, from the formula. The bottom panel is the power. **One question first: which curve is the two-exponential fitted to? The 100 kilohertz low-passed trace, the blue one, not the raw samples.** The raw samples are only drawn for comparison. The next two slides go through the two panels.

---

## Slide 6 — The height（约 100 秒）

*主图，讲慢一点。*

**中文**：先看上半部分，问题是脉冲的高度该怎么取。图里的东西：灰点是原始采样点，每 1.6 微秒一个。蓝线是 100 kHz 低通以后的波形，拟合看到的就是它。绿线是 20 kHz 低通，官方 Eabs 用的预滤波。红线是双指数拟合，上升 136 微秒，下降 213 微秒。红线周围的粉色带是拟合上下各一个 σ 的噪声，σ 是 89 个 ADC，从触发前的基线测出来的。黄色竖带是脉冲的平顶，有 98 个采样点都在峰高的 10% 以内。现在看右上角的表，四种取峰高的方法：原始数据的最大值 885，100 kHz 滤波以后的最大值 786，20 kHz 滤波以后 737，拟合的峰值 717。原始最大值比拟合高 23%。为什么？平顶上这 98 个点的真实高度差不多，你去取最大值，其实是在挑噪声往上跳得最多的那一个，所以必然偏高，跟脉冲本身没关系。滤波越强，偏得越少，但滤波也会把峰削掉一点。拟合用的是上升沿、平顶、下降沿全部的点，噪声被平均掉了，所以峰高只能从拟合来，不能从数据的最大值来。后面所有的能量都是这么算的。

**English**: The top panel first, and the question is how to take the height of the pulse. What is in the plot: **the grey dots are the raw samples, one every 1.6 microseconds. Blue is the trace after a 100 kilohertz low pass, and that is what the fit sees. Green is a 20 kilohertz low pass, the prefilter the official Eabs uses. Red is the two-exponential fit,** rise 136 microseconds, fall 213. **The pink band around it is the fit plus or minus one sigma of noise,** sigma being 89 ADC, measured on the baseline before the trigger. **The yellow band is the flat top of the pulse: 98 samples sit within 10 percent of the peak.** Now the table in the top right corner, four ways of taking the height: **the largest raw sample, 885; the maximum after the 100 kilohertz filter, 786; after the 20 kilohertz filter, 737; and the fit, 717. The raw maximum is 23 percent high.** Why? Those 98 samples on the top all have nearly the same true height. When you take the maximum, you are really picking the one that caught the biggest upward noise, so it is biased high no matter what, and that has nothing to do with the pulse. More filtering, less bias, but filtering also shaves the peak a bit. The fit uses every sample of the rise, the top and the decay, the noise averages out, so the height has to come from the fit and not from the largest sample. Every energy from here on is done that way.

---

## Slide 7 — The power pulse, and its area（约 85 秒）

**中文**：下半部分。红线是把拟合出来的电流代进公式得到的功率，两项加在一起。蓝色虚线只画线性项，几乎就是整条红线。紫色点线只画二次项，放大了 20 倍才看得见。峰值 104.6 飞瓦，其中 102.6 是线性项，2.0 是二次项，二次项占峰值的 1.9%，占能量的 1.3%。所以功率脉冲的形状和电流脉冲基本一样，只是换了单位，这就是为什么上一页的三条轴能这样并排。粉色的面积就是这个通道吸收的能量，305 电子伏，其中 99% 落在这 1.3 毫秒里。灰点和绿线是把同样的公式用在原始点和 20 kHz 波形上，只做对照，可以看到它们围着红线上下乱跳，那是噪声。最下面一行是这个通道的偏置点参数，就是定出两个系数的那些数。

**English**: The bottom panel. **The red curve is the fitted current put through the formula, the two terms added. The blue dashed line is the linear term alone, and it is almost the whole red curve. The purple dotted line is the quadratic term alone, drawn twenty times larger so you can see it.** The peak is 104.6 femtowatts: 102.6 from the linear term, 2.0 from the quadratic one. So the quadratic term is 1.9 percent of the peak and 1.3 percent of the energy. The power pulse has the same shape as the current pulse, only in a different unit, and that is why the three axes on the previous slide can sit side by side. **The shaded area is the energy this channel absorbed: 305 electron volts, and 99 percent of it lies inside these 1.3 milliseconds.** The grey dots and the green curve are the same formula applied to the raw samples and to the 20 kilohertz trace, for comparison only; you can see them jumping around the red curve, and that is noise. The bottom line lists the bias point of this channel, the numbers that fix the two coefficients.

---

## Slide 8 — Why the fitted pulse is integrated, and not the data（约 80 秒）

**中文**：有人会问，既然公式对任何电流都能用，为什么不直接对原始数据积分。这页就是答案。上面一排是这两个事件的原始电流本身：灰色是原始采样，蓝色是 20 kHz 低通，红色是拟合的脉冲，纵轴放大到基线附近正负 60 纳安，所以脉冲本身冲出了图的上边。黑线是基线，绿色虚线是脉冲之后电流的平均值。左边这个事件，脉冲之后电流基本回到基线，只偏了 0.1 纳安；右边这个事件，脉冲之后电流整体比基线低了 6 纳安。下面一排是对应的累计能量，横轴对齐。红线是积分拟合脉冲：触发前是 0，1 毫秒之内升上去，之后保持水平，终点正好等于绿色虚线的公式值。灰线是积分原始波形。左边原始和拟合只差 11 电子伏；右边那 6 纳安的偏移，单个点看完全埋在 28 纳安的噪声里，但换成功率是负 2.8 飞瓦，24 毫秒积下来就是负 420 电子伏，所以原始积分最后掉到负 169，而拟合给的是 277。所以能量必须从拟合来：没有最大值的噪声偏差，也不受基线漂移影响。

**English**: One might ask: the formula works for any current, so why not integrate the raw data directly? This slide is the answer. **The top row is the raw current of these two events: grey the raw samples, blue a 20 kilohertz low pass, red the fitted pulse, zoomed to plus or minus 60 nanoamps around the baseline, so the pulse itself runs off the top. The black line is the baseline, and the dashed green line is the mean current after the pulse.** On the left, after the pulse the current comes back to its baseline, off by only 0.1 nanoamps. **On the right, after the pulse the current sits 6 nanoamps below its baseline.** **The bottom row is the accumulated energy, on the same time axis.** Red is the integral of the fitted pulse: zero before, up within one millisecond, then flat, and it ends exactly on the formula value in green. Grey is the integral of the raw trace. On the left the two differ by 11 electron volts. On the right, that 6 nanoamp offset is buried in 28 nanoamps of noise on any single sample, but as power it is minus 2.8 femtowatts, and over 24 milliseconds that is minus 420 electron volts. **So the raw integral ends at minus 169, while the fit gives 277.** The energy has to come from the fit: no noise bias from the maximum, and no baseline drift.

---

## Slide 9 — The same event in its other channels（约 55 秒）

**中文**：一个通道讲完了，现在把同一个事件的 11 个通道都这样算，这里放四个。各通道拿到的份额差别很大：PES1 是 489 电子伏，PES2 只有 195，说明这个事件发生的位置更靠近 PES1 那一边。11 个通道加起来是 3419 电子伏，占 10.37 keV 的 33%。作为核对，把官方窗口直接用在原始波形上，加起来是 3397，两者只差 0.6%。右下角的 PDS2：5 毫秒之后波形有一个缓慢的大起伏，这是这个通道的低频伪影，它的拟合残差是别的通道的三倍，后面求和的时候它会是误差的来源。

**English**: One channel is done; now the same reading for all eleven channels of the same event, four of them shown here. **The shares differ a lot: PES1 gets 489 electron volts, PES2 only 195,** so this event happened closer to the PES1 side. **Summed over the eleven channels: 3419 electron volts, 33 percent of 10.37 keV.** As a check, the official window applied to the raw traces gives 3397; the two agree to 0.6 percent. **PDS2 in the bottom right: after 5 milliseconds there is a slow, large swing.** That is a low-frequency artefact of that channel; its fit residual is three times the others, and in the sum it becomes the source of the uncertainty.

---

## Slide 10 — Now every event: one channel（约 65 秒）

**中文**：从一个事件走到所有事件。还是 PBS1，1917 个事件，每个事件一个拟合、一个积分、一个能量。横轴是能量，每格 10 电子伏，纵轴是事件数。红色是从拟合来的，灰色轮廓是官方窗口在原始波形上算的，两者峰位只差 0.2%。峰在 285 电子伏，宽度 42，也就是 15%。注意，这是一条能量固定的谱线，但分布有 15% 宽。而且分布明显往右拖，一直到 600 电子伏，那些是发生在 PBS1 附近的事件。所以单通道的宽度主要是事件位置，不是噪声，单次拟合的噪声只有几个百分点。虚线是只对中间主体做的高斯拟合，所以 μ 是峰的位置，不是平均值，这一点下一页要用。

**English**: From one event to all of them. **Still PBS1, 1917 events, one fit, one integral, one energy per event. Energy on the horizontal axis, ten electron volts per bin, number of events on the vertical. Red is from the fit, the grey outline is the official window on the raw trace, and the two peaks agree to 0.2 percent. The peak is at 285 electron volts and the width is 42, that is 15 percent.** Keep in mind this is a line whose energy is fixed, and still the distribution is 15 percent wide. **And it clearly leans to the right, all the way out to 600 electron volts:** those are events that happened close to PBS1. So the width of one channel is mostly event position, not noise; the noise of one fit is a few percent. The dashed curve is a Gaussian fitted to the core only, so mu is the position of the peak and not the mean, and that matters on the next slide.

---

## Slide 11 — Summed over the channels: 32 ± 1 %（约 95 秒）

**中文**：结果。每个事件把通道加起来，下横轴是加起来的能量，上横轴是同一个数换算成 10.37 keV 的百分比。灰色是 10 个通道的和，1827 个事件，峰在 3162 电子伏，也就是 30.5%，宽度 7.5%。注意宽度：单通道是 15% 而且右偏，加起来以后变成对称的 7.5%，因为位置效应在求和时抵消掉了。顺便说一句，这里必须逐事件相加，不能把各通道的峰相加，右偏分布的峰在平均值左边，加峰会低 21%。为什么是 10 个通道不是 11 个？就是 PDS2，那个低频起伏让它只有 42% 的事件能拟合上。绿色是 11 个通道全加、但只用 PDS2 也拟合成功的那 797 个事件，峰在 3263。问题是这个子样本有偏：这些事件在另外 10 个通道里的和比全体低 4.8%，所以 PDS2 的份额只能给一个范围。算下来完整的效率在 31.5% 到 32.9% 之间，写成 32 正负 1。要把这个范围收窄，办法是把 PDS2 修到能拟合，不是加统计量。最右边的红线是 10.37 keV，大约三分之二的能量根本没有到 TES。

**English**: The result. The channels are summed event by event. **The bottom axis is the summed energy; the top axis is the same number as a fraction of 10.37 keV. Grey is the sum over ten channels, 1827 events: the peak is at 3162 electron volts, which is 30.5 percent, and the width is 7.5 percent.** Note the width: one channel was 15 percent and lopsided; summed, the distribution is symmetric and 7.5 percent wide, because the position effect cancels in the sum. By the way, this has to be done event by event; you cannot add the peaks of the channels, because the peak of a lopsided distribution sits left of its mean, and adding the peaks comes out 21 percent low. Why ten channels and not eleven? That is PDS2: the slow swing means only 42 percent of its events can be fitted. **Green is all eleven channels, but only for the 797 events where PDS2 also fits, with the peak at 3263.** The problem is that this subsample is biased: on these events the sum of the other ten channels is 4.8 percent lower than for all events, so PDS2's share can only be bracketed. **That puts the full efficiency between 31.5 and 32.9 percent, which I write as 32 plus or minus 1.** The way to shrink that bracket is to make PDS2 fittable, not to add statistics. **The red line on the far right is 10.37 keV:** about two thirds of the energy never reaches the TESs.

---

## Slide 12 — Summary, and what is still open（约 45 秒）

**中文**：总结。电流脉冲用 TES 方程换成功率，功率的面积是能量，二次项只有 2%。能量从拟合脉冲来、从负无穷积到正无穷：没有最大值的噪声偏差，没有漂移。单通道 15% 宽、右偏，是位置效应；10 个通道加起来是对称的 7.5%。Z7 吸收了 10.37 keV 事件的 32 正负 1%。CDMS 的文档在 R37 的 CUTE tower 上报的是 26% 到 41%，我们落在里面。还没落实的：目前只有 Z7；Z7 这些 series 的 HV 偏压还没确认，全按 0 伏算；没有 dI/dV，方程里的电感项是丢掉的；PDS2 就是那正负 1；还有 12.5% 的事件在任何通道都拟合不上，没进直方图。谢谢大家。

**English**: To sum up. A current pulse becomes a power pulse through the TES equations, the area under the power is the energy, and the quadratic term is 2 percent. The energy comes from the fitted pulse, integrated from minus to plus infinity: no noise bias from the maximum, no drift. One channel is 15 percent wide and lopsided, which is position; ten channels summed are symmetric and 7.5 percent wide. **Z7 absorbs 32 plus or minus 1 percent of a 10.37 keV event in its TESs. The CDMS note on the R37 CUTE tower reports 26 to 41 percent, and we sit inside that.** Still open: this is Z7 only; the HV bias of Z7 in these series is not established, so everything assumes zero volts; there is no dI-dV, so the inductor term of the equations is dropped; PDS2 is the plus or minus one; and 12.5 percent of the events fit in no channel and are not in the histograms. Thank you.

---

## Backup（仅备查，不占正片时间）

**B1 事件谱**：Z7 的 PTOFamps 谱，紫色是我们自己从 Prompt 处理重做的、没加 cut，黑色是运行记录里的图，红线是 K 线，2 乘 10 的负 6 安。
**B1 The events**: the PTOFamps spectrum of Z7; purple is our own rebuild from the Prompt processing with no cut, black the ops-note histogram, the red line the K line at 2 times ten to the minus six amps.

**B2 公式的三个版本和官方 Eabs**：δP = I₀(R_L − R₀)·δI + c₂·R_L·(δI)²，二次项系数 2 是 method 1，1 是精确小信号解，负 1 是 method 2；相对精确解，method 1 高 0.58%，method 2 低 1.15%。官方 Eabs 我们复现到 0.2%：触发在第 16383 点，基线是 93 到 15758 点的平均，20 kHz 五阶 Butterworth，窗口触发前 0.5 毫秒到后 1 毫秒。
**B2 Formula versions and the official Eabs**: in delta P = I zero (R L minus R zero) delta I plus c two R L delta I squared, 2 is Method 1, 1 the exact small-signal result, minus 1 Method 2; relative to exact, Method 1 is 0.58 percent high and Method 2 1.15 percent low. The official Eabs is reproduced to 0.2 percent: trigger at bin 16383, baseline the mean of bins 93 to 15758, a 5-pole 20 kilohertz Butterworth, window minus 0.5 to plus 1 millisecond.

**B3–B6**：完整原图：15 个事件的电流功率图和累计能量图，全通道图，11 个通道的能量分布（每个都右偏，PDS2 标了不进求和）。
**B3–B6**: the full figures: the 15-event current-and-power and cumulative-energy grids, the all-channel grid, and the energy distribution of all eleven channels (every one right-skewed; PDS2 marked as left out).

---

## 可能被问的问题 / Likely questions（回答一两句即可）

**Q1. 蓝线上那些规律的小波纹是什么？/ What is the regular ripple on the blue curve?**
中文：是一条 66 kHz 的噪声谱线，比周围频段高约 700 倍，150 个事件平均也一样。100 kHz 的低通挡不住它，20 kHz 的能滤掉。
English: It is a noise line at 66 kilohertz, about 700 times above the neighbouring band, and it is there in the average of 150 events too. The 100 kilohertz low pass lets it through; the 20 kilohertz one removes it.

**Q2. 为什么脉冲在时间 0 之前就开始了？/ Why does the pulse start before time zero?**
中文：时间 0 是波形里固定的触发位置，第 16383 个点。拟合出来的起点在触发前 0.175 毫秒。这个偏移的来源我没有再往下查。
English: Time zero is the fixed trigger position in the trace, sample 16383. The fitted pulse starts 0.175 milliseconds before it. I have not chased down where that offset comes from.

**Q3. 原始最大值偏高 23% 是普遍的吗？/ Is the 23 % bias of the raw maximum general?**
中文：这个数只是这一个事件的。大约 100 个独立噪声点里的最大值平均在 2.5σ 左右；这里是 1.88σ，因为相邻点有相关，平顶上的点也比峰略低。没有对所有事件做统计。
English: That number is for this one event. Among about a hundred independent noise samples the maximum averages around 2.5 sigma; here it is 1.88 sigma, because neighbouring samples are correlated and the flat-top samples sit slightly below the peak. I have not done the statistics over all events.

**Q4. 为什么不用官方的 Eabs 就好？/ Why not just use the official Eabs?**
中文：官方 Eabs 我们复现到了 0.2%，峰位也和拟合法一致。但它对原始波形积分，依赖窗口和基线；拟合法没有噪声偏差、没有漂移、没有窗口，而且给出的是解析式。两者互相验证。
English: We reproduce the official Eabs to 0.2 percent, and its peak agrees with the fit method. But it integrates the raw trace, so it depends on the window and the baseline; the fit method has no noise bias, no drift and no window, and gives a closed form. The two check each other.

**Q5. PDS2 到底怎么了？/ What is wrong with PDS2?**
中文：它有一个低频的大起伏，5 毫秒之后波形整体鼓起来，双指数拟合的残差就超了。原因没查清，做模板的时候也见过。
English: It carries a slow, large low-frequency swing after about 5 milliseconds, and that pushes the two-exponential residual over the cut. The cause is not established; it showed up in the template work too.

**Q6. 为什么高斯峰不能相加？/ Why can't the Gaussian peaks be added?**
中文：每个通道的分布都右偏，峰在平均值左边。事件能量的和等于各通道平均值的和，不等于各通道峰的和，加峰会低 21%。
English: Every channel's distribution is skewed to the right, so the peak sits left of the mean. The sum of the event energies equals the sum of the channel means, not the sum of the channel peaks; adding the peaks comes out 21 percent low.

**Q7. 拟合失败的 12.5% 事件呢？/ What about the 12.5 % of events that fit nowhere?**
中文：还没查。如果它们的能量分布不一样，效率会有偏差。在待办里。
English: Not checked yet. If their energy distribution is different, the efficiency would be biased. It is on the to-do list.

**Q8. Luke 声子会怎么改结果？/ How would Luke phonons change the result?**
中文：如果有偏压，晶体里的总能量是 10.37 keV 加上 Luke 的贡献，分母变大，效率变小。Z7 这些 series 的偏压还没确认，所以按 0 伏算。
English: With a bias, the total energy in the crystal is 10.37 keV plus the Luke contribution, so the denominator grows and the efficiency drops. The bias of Z7 in these series is not established, so everything assumes zero volts.

**Q9. 公式里的电感项呢？/ What about the inductor term?**
中文：完整方程里有一项和电感、loop gain 有关，是个快而小的修正。MSI 上没有这些 series 的 dI/dV 数据，所以拿不到 L 和 loop gain，这一项是丢掉的，没法检查。
English: The full equations have a term with the inductance and the loop gain, a fast and small correction. There is no dI-dV data for these series on MSI, so L and the loop gain are not available; that term is dropped and could not be checked.

---

## 术语自查表（只给自己，不进 PPT）

- δI：脉冲带来的电流变化，减掉基线之后的量。
- I₀：TES 的工作电流；R₀：工作点电阻；R_L = R_p + R_sh：负载电阻。
- 线性项 I₀(R_L−R₀)·δI：焦耳热对电流的一阶变化；二次项 2R_L·(δI)²：二阶。
- 闭式 / closed form：能量直接用 A、τ_f、τ_r 代公式，不做数值积分。
- NRMSE：拟合残差除以峰高，≤ 0.2 才保留，正常 0.03–0.07。
- 核心通道 / core channels：拟合成功率 ≥ 90% 的 10 个通道，不含 PDS2。
- 高斯峰 μ：只对主体拟合，是峰位不是平均值。
