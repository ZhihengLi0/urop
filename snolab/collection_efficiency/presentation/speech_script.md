# Speaker Script / 演讲稿 — Z7 Phonon Collection Efficiency

约 13 分钟，14 页正片 + 8 页 backup。每页先中文、后英文，内容一一对应，**英文可以直接照读**。
原则：稿子是说的话，不是幻灯片的复读。具体数字都在屏幕上，嘴里讲思路和为什么。
斜体是给自己的提示，不用念。**加粗的英文**是指着屏幕说的那几句。

时间分配（秒）：1 题目 25 · 2 问题 60 · 3 数据 45 · 4 公式 60 · 5 峰高 110 · 6 功率 75 · 7 拟合 50 · 8 积分 60 · 9 全通道 50 · 10 单通道分布 55 · 11 各通道 55 · 12 求和 80 · 13 对照和局限 50 · 14 总结 30 → 约 805 秒。超时就把第 13 页压缩成两句。

---

## Slide 1 — Title（约 25 秒）

**中文**：大家好。今天讲的是 Z7 的声子收集效率：一个 10.37 keV 的 K 线事件打进晶体，最后有多少能量真的到了 TES 里。这个数我们得到的是 32%，正负 1。我按做的顺序讲：为什么波形本身不能直接给出能量，怎么把电流换成功率，怎么积分，最后怎么从一个通道走到整个探测器。

**English**: Hi everyone. Today's topic is the phonon collection efficiency of Z7: when a 10.37 keV K-line event happens in the crystal, how much of that energy actually ends up in the TESs. The number we get is 32 percent, plus or minus one. I'll go in the order I did the work: why the trace by itself does not give you an energy, how the current is turned into power, how that is integrated, and how we go from one channel to the whole detector.

---

## Slide 2 — The question（约 60 秒）

**中文**：先把问题说清楚。收集效率就是 TES 薄膜里收到的能量，除以事件放进晶体的 10.37 keV。我们记录下来的波形，纵轴是电流：声子把薄膜加热，TES 的电流就变化了一点，这个变化就是 δI。这里有一个很容易踩的坑：电流曲线下面的面积是电荷，不是能量，它没法跟 10.37 keV 比。所以必须先用 TES 的方程把电流脉冲换成功率脉冲，功率曲线下面的面积才是能量。屏幕上这条链就是整个流程：晶体里的能量，声子到薄膜，电流脉冲，功率脉冲，能量，最后除以 10.37 keV。今天所有的东西都是一个探测器，Z7，它是最安静的那个；事件就是 Ge 活化的 K 线事件。

**English**: Let me first state the question. Collection efficiency is the energy that ends up in the TES films, divided by the 10.37 keV the event put into the crystal. What we record is a current: phonons heat the film, the TES current changes a little, and that change is delta I. And here is the trap: **the area under the current trace is a charge, not an energy.** You cannot compare it with 10.37 keV. So the current pulse has to be turned into a power pulse first, using the TES equations, and the area under the power pulse is the energy. **The chain on the screen is the whole procedure:** energy in the crystal, phonons to the film, current pulse, power pulse, energy, and then divide by 10.37 keV. Everything today is one detector, Z7, the quietest one, and the events are the K-line events of the germanium activation.

---

## Slide 3 — The events（约 45 秒）

**中文**：事件从哪来。Cf 活化之后，每个探测器都持续产生 10.37 keV 的单能事件。屏幕上是 Z7 的 PTOFamps 谱，紫色是我们自己从 Prompt 处理重做的、没加任何 cut，黑色是运行记录里的那张图，红线是 K 线的位置。在 Z7 上 K 线峰和噪声峰分得很开，所以这是一批干净的、能量完全一样的事件。一共 30 个 series，2207 个 K 线事件，每个事件每个声子通道的原始波形都存下来了，Z7 有 11 个通道读出。另外每个通道的偏置点，I0、R0、Rp、Rsh，都是从处理文件的 detectorConfig 里读出来的实测值。样本跟做脉冲模板时是同一批，没有另外挑。

**English**: Where the events come from. After the californium activation, every detector keeps producing mono-energetic 10.37 keV events. **On the screen is the PTOFamps spectrum of Z7: purple is our own rebuild from the Prompt processing with no cut, black is the histogram from the ops note, and the red line is the K line.** On Z7 the K-line peak is well separated from the noise peak, so this is a clean sample of events with exactly the same energy. Thirty series, 2207 K-line events, and for each one the raw trace of every phonon channel is saved; Z7 has eleven channels read out. The bias point of each channel, I zero, R zero, R p and R shunt, is read from the detectorConfig in the processing files, so those are measured values. It is the same sample as the pulse-template work; nothing new was selected.

---

## Slide 4 — From current to power（约 60 秒）

**中文**：这页是公式。薄膜吸收的功率，就是电流变化 δI 之后焦耳热的变化量，写出来是两项：一个线性项，一个二次项。这是 Irwin 和 Hilton 的小信号结果，也是 CDMS 收集效率文档里的 method 1。两个系数全部来自这个通道实测的偏置点，没有任何拟合或调参。以 PBS1 为例，线性项系数是 4.5 乘 10 的负 7 伏，二次项系数是 0.0385 欧姆。第二行是关键：如果脉冲是双指数的形状，这个积分有解析式，直接用拟合出来的 A、τ_f、τ_r 就能算出能量，不需要选积分窗口。还有一点，波形的单位是 ADC 计数，31 亿 4 千万个 ADC 等于 1 安培，也就是 1 个 ADC 是 0.318 纳安。我们只用减掉基线以后的部分。顺便说一句，这个公式有三个版本，二次项前面的系数分别是 2、1、负 1，它们算出来的能量差不到 1.2%，所以选哪个不是主要误差，backup 里有细节。

**English**: This slide is the formula. **The power the film absorbs is the change in Joule heating when the current moves by delta I, and it comes out as two terms: a linear one and a quadratic one.** This is the small-signal result of Irwin and Hilton, and it is Method 1 of the CDMS collection-efficiency note. Both coefficients come from the measured bias point of that channel; nothing is fitted or tuned. For PBS1 the linear coefficient is 4.5 times ten to the minus seven volts, and the quadratic one is 0.0385 ohms. **The second line is the important one: if the pulse has a two-exponential shape, the integral has a closed form.** You take the fitted A, tau f and tau r and get the energy directly, with no integration window to choose. One more thing: the trace is in ADC counts, about 3.1 billion ADC per ampere, so one ADC is 0.318 nanoamps, and only the part above the baseline is used. And in case anyone asks: there are three versions of this formula, with 2, 1 or minus 1 in front of the quadratic term; they differ by less than 1.2 percent in energy, so the choice is not the main uncertainty. Details are in the backup.

---

## Slide 5 — One pulse read three ways: the height（约 110 秒）

*这是主图，讲慢一点。*

**中文**：这张图是今天的主图，一个通道、一个事件，只放大脉冲附近。同一条曲线有三条纵轴：左边是减掉基线的 ADC，右边第一条是微安，右边第二条是飞瓦。也就是说，同一个脉冲可以同时读成 ADC、电流和功率，中间只是乘了已知的系数。图里的东西：灰点是原始采样点，每 1.6 微秒一个；蓝线是 100 kHz 低通，是拟合实际看到的数据；绿线是 20 kHz 低通，是官方 Eabs 用的预滤波；红线是双指数拟合，上升 136 微秒，下降 213 微秒；红线周围的粉色带是拟合上下各一个 σ 的噪声，σ 是 89 个 ADC。黄色竖带是脉冲的平顶，有 98 个采样点都在峰高的 10% 以内。现在看右上角的表，这是这页要说的事。四种取峰高的方法：原始最大值 885，100 kHz 滤波后的最大值 786，20 kHz 滤波后 737，拟合峰值 717。原始最大值比拟合高 23%。为什么？平顶上 98 个点的真实高度差不多，你取最大值，等于在挑噪声往上跳得最多的那一个，它必然偏高。滤波越强，偏高越少，但滤波本身也会把峰削掉一点。拟合用的是上升沿、平顶、下降沿的所有点，噪声被平均掉了，所以峰高要从拟合来，不能从数据的最大值来。这一点对后面所有的能量都成立。

**English**: This is the main figure of the talk: one channel, one event, zoomed in on the peak. **The same curve has three vertical axes: ADC above baseline on the left, microamps on the first right axis, and femtowatts on the second.** So one pulse can be read as ADC, as current and as power at the same time; in between there are only known factors. What is in the plot: **the grey dots are the raw samples, one every 1.6 microseconds. Blue is a 100 kilohertz low pass, which is what the fit actually sees. Green is a 20 kilohertz low pass, the prefilter the official Eabs uses. Red is the two-exponential fit,** rise 136 microseconds, fall 213, **and the pink band around it is the fit plus or minus one sigma of noise,** sigma being 89 ADC. **The yellow band is the flat top of the pulse: 98 samples sit within 10 percent of the peak.** Now the table in the top right corner, which is the point of this slide. Four ways of taking the pulse height: **the largest raw sample, 885; the 100 kilohertz maximum, 786; the 20 kilohertz maximum, 737; and the fit, 717. The raw maximum is 23 percent high.** Why? On the flat top, 98 samples have nearly the same true height. If you take the maximum, you are picking whichever one caught the biggest upward noise, so it is always biased high. More filtering means less bias, but filtering also shaves the peak a little. The fit uses every sample of the rise, the top and the decay, and the noise averages out. So the pulse height has to come from the fit, not from the largest sample, and that holds for every energy on the following slides.

---

## Slide 6 — The power, and its area（约 75 秒）

**中文**：同一个事件，下半部分。红线是把拟合出来的电流代进公式得到的功率，两项加在一起。蓝色虚线只画线性项，几乎就是整条红线。紫色点线只画二次项，放大了 20 倍才看得见。峰值 104.6 飞瓦，其中 102.6 是线性项，2.0 是二次项，二次项占峰值功率的 1.9%，占能量的 1.3%。所以功率脉冲的形状跟电流脉冲基本一样，只是换了单位。粉色面积就是这个通道吸收的能量，305 电子伏，其中 99% 落在这 1.3 毫秒的窗口里。灰点和绿线是把同样的公式用在原始点和 20 kHz 波形上，只做对照。最下面一行是这个通道的偏置点参数，就是定出两个系数的那些数。

**English**: Same event, lower panel. **The red curve is the fitted current put through the formula, the two terms added. The blue dashed line is the linear term alone, and it is almost the whole red curve. The purple dotted line is the quadratic term alone, drawn twenty times larger so you can see it at all.** The peak is 104.6 femtowatts: 102.6 from the linear term, 2.0 from the quadratic one. So the quadratic term is 1.9 percent of the peak power and 1.3 percent of the energy, and the power pulse has the same shape as the current pulse, only in a different unit. **The shaded area is the energy this channel absorbed: 305 electron volts, and 99 percent of it lies inside this 1.3 millisecond window.** The grey dots and the green curve are the same formula applied to the raw samples and to the 20 kilohertz trace, for comparison only. The bottom line lists the bias point of this channel, the numbers that fix the two coefficients.

---

## Slide 7 — Every event: fit the current, convert to power（约 50 秒）

**中文**：每个事件都是同样的处理。每条波形直接在电流单位里拟合双指数，脉冲的起点是放开的，可以在触发前后 4.8 毫秒里自己找。左轴是拟合出来的电流，深蓝虚线；右轴是它对应的功率，红线；灰色是原始波形，只作参考。两条线完全重合，因为二次项只有 2%，右轴其实就是左轴乘上 4.5 乘 10 的负 7 伏。黄色竖带是官方 Eabs 的积分窗口，拟合本身不需要窗口。拟合的残差超过脉冲高度的 20% 就丢掉，正常的拟合残差在 3% 到 7%。这是同一个通道的两个事件，能量一个 305，一个 448；15 个例子的范围是 198 到 448 电子伏。

**English**: Every event gets the same treatment. Each trace is fitted with a two-exponential directly in current units, and the pulse start is free: it can sit anywhere within 4.8 milliseconds of the trigger. **The left axis is the fitted current, the navy dashed line; the right axis is the power it implies, the red line; grey is the raw trace, for reference only.** The two curves lie on top of each other because the quadratic term is only 2 percent; the right axis is really the left axis times 4.5 times ten to the minus seven volts. **The yellow band is the official Eabs window;** the fit itself needs no window. A fit is dropped if its residual is more than 20 percent of the pulse height; normal fits sit at 3 to 7 percent. These are two events in the same channel, 305 and 448 electron volts; over the 15 examples the energies run from 198 to 448.

---

## Slide 8 — Why the fit is integrated, not the raw trace（约 60 秒）

**中文**：这页解释为什么积分的是拟合曲线，不是原始数据。纵轴是累计能量，从波形开头一路积到时间 t；横轴是整条波形，52 毫秒，触发在 26 毫秒那条点线。红线是积分拟合脉冲：触发前是 0，脉冲一来，1 毫秒之内升上去，之后保持水平，终点正好等于绿色虚线，也就是公式算出来的解析值。所以能量跟积到哪里没有关系。灰线是积分原始波形，它一直在漂。原因很简单：基线只要偏 1 纳安，15 毫秒积下来就是 42 电子伏。右边这个事件，拟合给 277 电子伏，原始波形积到最后是负 169。这就是为什么能量要从拟合参数 A、τ_r、τ_f 代公式算，而不是对数据做数值积分。

**English**: This slide is why we integrate the fit and not the data. **The vertical axis is the accumulated energy, integrated from the start of the trace up to time t; the horizontal axis is the whole 52 millisecond trace, with the trigger at the dotted line at 26 milliseconds. The red curve is the integral of the fitted pulse: zero before the pulse, up within one millisecond, then flat, and its end value is exactly the green dashed line,** the closed-form value from the formula. So the energy does not depend on where you stop. **The grey curve is the integral of the raw trace, and it drifts.** The reason is simple: a baseline offset of just one nanoamp, over 15 milliseconds, is already 42 electron volts. **For the event on the right, the fit gives 277 electron volts and the raw integral ends at minus 169.** That is why the energy comes from the fit parameters A, tau r and tau f put into the formula, and not from a numerical integral of the data.

---

## Slide 9 — One event, all channels（约 50 秒）

**中文**：现在把一个事件的 11 个通道都算一遍，这里只放四个。各通道拿到的份额差别很大：PES1 是 489 电子伏，PES2 只有 195，说明这个事件发生的位置更靠近 PES1 那一边；时间常数也各不相同。11 个通道加起来是 3419 电子伏，占 10.37 keV 的 33.0%。作为核对，把官方窗口直接用在原始波形上，加起来是 3397，32.8%，两者只差 0.6%。右下角的 PDS2 要注意：5 毫秒之后波形有一个缓慢的大起伏，这是这个通道的低频伪影，它的拟合残差 0.14，是别的通道的三倍。后面它会成为问题。

**English**: Now the same thing for all eleven channels of one event; four of them are shown here. **The shares differ a lot: PES1 gets 489 electron volts, PES2 only 195,** so this event happened closer to the PES1 side, and the time constants differ too. **Summed over the eleven channels: 3419 electron volts, which is 33.0 percent of 10.37 keV.** As a check, the official window applied to the raw traces gives 3397, 32.8 percent, so the two agree to 0.6 percent. **Look at PDS2 in the bottom right: after 5 milliseconds there is a slow, large swing.** That is a low-frequency artefact of that channel; its fit residual is 0.14, three times the others. It will come back as a problem later.

---

## Slide 10 — Every event, one channel（约 55 秒）

**中文**：现在从一个事件走到所有事件。这是 PBS1，1917 个事件，每个事件一个拟合、一个积分，一个能量，横轴是能量，每格 10 电子伏，纵轴是事件数。红色是从拟合来的，灰色轮廓是官方窗口在原始波形上算的，两者峰位只差 0.2%。峰在 285 电子伏，宽度 42，也就是 15%。注意这是一条能量固定的谱线，但分布有 15% 宽。虚线是只对中间主体做的高斯拟合，所以 μ 是峰的位置，不是平均值。分布明显往右拖，一直到 600 电子伏，那些是发生在 PBS1 附近的事件。所以单通道的宽度主要来自事件的位置，不是噪声，单次拟合的噪声只有几个百分点。2207 个事件里有 290 个在这个通道没有通过拟合质量的 cut。

**English**: Now from one event to all of them. **This is PBS1, 1917 events, one fit, one integral, one energy per event: energy on the horizontal axis, ten electron volts per bin, number of events on the vertical.** Red is from the fit, the grey outline is the official window on the raw trace, and the two peaks agree to 0.2 percent. **The peak is at 285 electron volts and the width is 42, that is 15 percent,** for a line whose energy is fixed. The dashed curve is a Gaussian fitted to the core only, so mu is the position of the peak, not the mean. **The distribution clearly leans to the right, all the way out to 600 electron volts:** those are events that happened close to PBS1. So the width of a single channel is mostly event position, not noise; the noise of one fit is a few percent. Of the 2207 events, 290 fail the fit-quality cut in this channel.

---

## Slide 11 — Every channel（约 55 秒）

**中文**：每个通道都这样做，这里放四个，11 个全在 backup。每个通道都是右偏的，所以高斯峰都在平均值下面：PBS1 峰 285、平均 311，PES1 峰 256、平均 358。这里有个要小心的地方：右偏分布的峰不能相加。把 11 个峰加起来，比真实值低 21%。平均值才能加。所以下一页用的是逐事件求和，这才是老实的做法。宽度从 PFS1 的 6.8% 到 PDS1、PES2 的 27%，不同通道看到的位置效应不一样。最后是 PDS2：因为那个低频伪影，只有 42% 的事件能通过残差 cut。所以它不进核心求和，剩下 10 个通道，每个都能拟合 95% 以上的事件。

**English**: The same for every channel; four are shown, all eleven are in the backup. **Every channel leans to the right, so its Gaussian peak sits below its mean: PBS1 peak 285, mean 311; PES1 peak 256, mean 358.** And here is something to be careful about: **the peaks of skewed distributions do not add. Add up the eleven peaks and you are 21 percent low.** Means do add. So the next slide uses the sum event by event, which is the honest quantity. **The widths run from 6.8 percent for PFS1 to 27 percent for PDS1 and PES2;** the channels see the position effect differently. And finally **PDS2: because of that low-frequency artefact, only 42 percent of its events pass the residual cut.** So it stays out of the core sum; ten channels remain, and each of them fits more than 95 percent of the events.

---

## Slide 12 — Summed over channels: 32 ± 1 %（约 80 秒）

**中文**：这是结果。每个事件把通道加起来，下横轴是加起来的能量，上横轴是同一个数换算成 10.37 keV 的百分比。灰色是 10 个核心通道的和，1827 个事件，峰在 3162 电子伏，也就是 30.5%，宽度 7.5%。注意宽度：单通道是 15 到 27% 而且右偏，加起来以后变成对称的 7.5%，因为位置效应在求和的时候抵消掉了。绿色是 11 个通道全加，但只有 PDS2 也拟合成功的那 797 个事件，峰在 3263。问题是这个子样本有偏：这些事件在另外 10 个通道里的和比全体低 4.8%，所以 PDS2 的份额只能给一个范围。算下来完整的效率在 31.5% 到 32.9% 之间，写成 32 正负 1。要把这个范围收窄，办法是把 PDS2 修到能拟合，不是加统计量。最右边的红线是 10.37 keV，大约三分之二的能量根本没有到 TES。

**English**: This is the result. The channels are summed event by event. **The bottom axis is the summed energy; the top axis is the same number as a fraction of 10.37 keV. Grey is the sum over the ten core channels, 1827 events: the peak is at 3162 electron volts, which is 30.5 percent, and the width is 7.5 percent.** Note the width: single channels were 15 to 27 percent and skewed; summed, the distribution is symmetric and 7.5 percent wide, because the position effect cancels in the sum. **Green is all eleven channels, but only for the 797 events where PDS2 also fits, with the peak at 3263.** The problem is that this subsample is biased: on these events the sum of the other ten channels is 4.8 percent lower than for all events, so PDS2's share can only be bracketed. **That puts the full efficiency between 31.5 and 32.9 percent, which I write as 32 plus or minus 1.** The way to shrink that bracket is to make PDS2 fittable, not to add statistics. **The red line on the far right is 10.37 keV:** about two thirds of the energy never reaches the TESs.

---

## Slide 13 — Where 32 % sits, and what is not nailed down（约 50 秒）

*超时就只念加粗的三句。*

**中文**：对照一下。CDMS 收集效率文档在 R37 的 CUTE tower 上报的是 26% 到 41%，Z1 是 26 和 29，Z3 是 41，Z6 是 26，我们 Z7 的 32% 落在这个范围里。他们的做法是积分原始脉冲，积到衰减 90% 为止；我们是拟合脉冲的解析积分。在例子事件上官方窗口和拟合差 0.6%。还没有落实的几件事：第一，目前只有 Z7。第二，Z7 在这些 series 里的 HV 偏压还没确认，所有数字按 0 伏算；如果有偏压，Luke 声子会让放进晶体的能量变大，分母要改。第三，MSI 上没有 dI/dV 数据，loop gain 和电感都不知道，公式里的电感项是丢掉的，没法检查。第四，PDS2 就是那正负 1。第五，2207 个事件里有 276 个，12.5%，在任何通道都拟合不上，没进直方图，它们的能量是不是不一样还没查。

**English**: For comparison. **The CDMS collection-efficiency note reports 26 to 41 percent on the R37 CUTE tower: Z1 at 26 and 29, Z3 at 41, Z6 at 26. Our 32 percent for Z7 sits inside that range.** Their method integrates the raw pulse until it has decayed by 90 percent; ours integrates the fitted pulse in closed form. On the example event the official window and the fit agree to 0.6 percent. What is not nailed down yet: first, this is Z7 only. **Second, the HV bias of Z7 during these series is not established, so every number assumes zero volts;** with a bias, Luke phonons would enlarge the deposited energy and the denominator changes. **Third, there is no dI-dV data on MSI, so the loop gain and the inductance are unknown;** the inductor term of the equations is dropped and could not be checked. Fourth, PDS2 is the plus or minus one. Fifth, 276 of the 2207 events, 12.5 percent, fit in no channel at all and are not in the histograms; whether they carry a different energy has not been checked.

---

## Slide 14 — Summary（约 30 秒）

**中文**：总结。波形是电流。用 TES 方程和每个通道实测的偏置点换成功率，积分就是吸收的能量，二次项只有 2%。能量从拟合脉冲来，不从数据来：没有最大值的噪声偏差，没有基线漂移，也不需要积分窗口。单通道是 15% 宽的右偏分布，是位置效应；10 个通道加起来是对称的 7.5%。Z7 吸收了 10.37 keV 事件的 32 正负 1%，正负 1 来自 PDS2。下一步是其他 12 个探测器、修 PDS2、落实偏压、拿 dI/dV。代码和图都在 GitHub 的 collection_efficiency 目录里。谢谢大家。

**English**: To sum up. The trace is a current. Turned into power with the TES equations and the measured bias point of each channel, its integral is the absorbed energy, and the quadratic term is 2 percent. The energy comes from the fitted pulse, not from the data: no bias from the noisy maximum, no drift from the baseline, no integration window. One channel gives a 15 percent wide, right-skewed distribution, which is event position; ten channels summed give a symmetric 7.5 percent. **Z7 absorbs 32 plus or minus 1 percent of a 10.37 keV event in its TESs, and the plus or minus one is PDS2.** Next: the other twelve detectors, fixing PDS2, settling the bias, and getting dI-dV. Code and figures are in the collection_efficiency directory on GitHub. Thank you.

---

## Backup（仅备查，不占正片时间）

**B1 三个公式版本**：二次项系数 2 是 method 1，1 是精确小信号解，负 1 是 method 2。相对精确解，method 1 高 0.58%，method 2 低 1.15%。单通道 15% 的宽度和 PDS2 的正负 1 都比这大得多。
**B1 Three formula versions**: 2 is Method 1, 1 is the exact small-signal result, minus 1 is Method 2. Relative to the exact form, Method 1 is 0.58 percent high and Method 2 is 1.15 percent low; both far below the 15 percent single-channel width and the PDS2 bracket.

**B2 官方 Eabs**：触发在第 16383 点，基线是 93 到 15758 点的平均，20 kHz 五阶 Butterworth，窗口触发前 0.5 毫秒到后 1 毫秒，同一个 method 1 公式求和。我们复现到 0.2%。拟合脉冲有 98 到 99% 的能量在窗口里，所以窗口对拟合没问题，伤到原始波形的是漂移，不是尾巴。
**B2 The official Eabs**: trigger at bin 16383, baseline the mean of bins 93 to 15758, a 5-pole 20 kilohertz Butterworth, window minus 0.5 to plus 1 millisecond, the same Method-1 formula summed. We reproduce it to 0.2 percent. The fitted pulse puts 98 to 99 percent of its energy inside that window, so the window is fine for the fit; what hurts the raw trace is the drift, not the tail.

**B3–B8**：完整的原图：峰区大图、15 个事件的电流功率图和累计能量图、全通道的电流功率图和累计能量图、11 个通道的能量分布。
**B3–B8**: the full original figures: the peak figure, the 15-event current-and-power and cumulative-energy grids, the all-channel grids for event 30646, and the energy distribution of all eleven channels.

---

## 可能被问的问题 / Likely questions（回答一两句即可）

**Q1. 蓝线上那些规律的小波纹是什么？/ What is the regular ripple on the blue curve?**
中文：是一条 66 kHz 的噪声谱线，比周围频段高约 700 倍，150 个事件平均也一样。100 kHz 的低通挡不住它，20 kHz 的能滤掉。
English: It is a noise line at 66 kilohertz, about 700 times above the neighbouring band, and it is there in the average of 150 events too. The 100 kilohertz low pass lets it through; the 20 kilohertz one removes it.

**Q2. 为什么脉冲在时间 0 之前就开始了？/ Why does the pulse start before time zero?**
中文：时间 0 是波形里固定的触发位置，第 16383 个点。拟合出来的脉冲起点在触发前 0.175 毫秒。这个偏移的来源我没有再往下查。
English: Time zero is the fixed trigger position in the trace, sample 16383. The fitted pulse starts 0.175 milliseconds before it. I have not chased down where that offset comes from.

**Q3. 原始最大值偏高 23% 是普遍的吗？/ Is the 23 % bias of the raw maximum general?**
中文：这个数只是这一个事件的。大约 100 个独立的噪声点里，最大值平均在 2.5σ 左右；这里测到 1.88σ，因为相邻点有相关，平顶上的点也比峰略低。没有对所有事件做统计。
English: That number is for this one event. Among about a hundred independent noise samples the maximum is around 2.5 sigma on average; here it is 1.88 sigma, because neighbouring samples are correlated and the flat-top samples sit slightly below the peak. I have not done the statistics over all events.

**Q4. 为什么不用官方的 Eabs 就好？/ Why not just use the official Eabs?**
中文：官方 Eabs 我们复现到了 0.2%，峰位也和拟合法一致。但它对原始波形积分，依赖窗口和基线；拟合法没有噪声偏差、没有漂移、没有窗口，而且给出的是解析式。两者互相验证。
English: We reproduce the official Eabs to 0.2 percent, and its peak agrees with the fit method. But it integrates the raw trace, so it depends on the window and the baseline; the fit method has no noise bias, no drift and no window, and gives a closed form. The two check each other.

**Q5. 为什么 PDS2 会这样？/ What is wrong with PDS2?**
中文：它有一个低频的大起伏，5 毫秒之后波形整体鼓起来，双指数拟合的残差就超了。原因没有查清，做模板的时候也见过。
English: It carries a slow, large low-frequency swing after about 5 milliseconds, and that pushes the two-exponential residual over the cut. The cause is not established; it showed up in the template work too.

**Q6. 为什么高斯峰不能相加？/ Why can't the Gaussian peaks be added?**
中文：因为每个通道的分布都右偏，峰在平均值左边。事件能量的和，等于各通道平均值的和，不等于各通道峰的和。加峰会低 21%。
English: Because every channel's distribution is skewed to the right, so the peak sits left of the mean. The sum of the event energies equals the sum of the channel means, not the sum of the channel peaks; adding the peaks comes out 21 percent low.

**Q7. 拟合失败的 12.5% 事件呢？/ What about the 12.5 % of events that fit nowhere?**
中文：还没查。如果它们的能量分布不一样，效率会有偏差。这是列在待办里的。
English: Not checked yet. If their energy distribution is different, the efficiency would be biased. It is on the to-do list.

**Q8. Luke 声子会怎么改结果？/ How would Luke phonons change the result?**
中文：如果有偏压，晶体里的总能量是 10.37 keV 加上 Luke 贡献，分母变大，效率变小。Z7 这些 series 的偏压还没确认，所以按 0 伏算。
English: With a bias, the total energy in the crystal is 10.37 keV plus the Luke contribution, so the denominator grows and the efficiency drops. The bias of Z7 in these series is not established, so everything assumes zero volts.

---

## 术语自查表（只给自己，不进 PPT）

- δI：脉冲带来的电流变化，减掉基线之后的量。
- I₀：TES 的工作电流；R₀：工作点电阻；R_L = R_p + R_sh：负载电阻。
- 线性项 I₀(R_L−R₀)·δI：焦耳热对电流的一阶变化；二次项 2R_L·(δI)²：二阶。
- 闭式 / closed form：能量直接用 A、τ_f、τ_r 代公式，不做数值积分。
- NRMSE：拟合残差除以峰高，≤ 0.2 才保留。
- 核心通道 / core channels：拟合成功率 ≥ 90% 的 10 个通道，不含 PDS2。
- 高斯峰 μ：只对主体拟合，是峰位不是平均值。
