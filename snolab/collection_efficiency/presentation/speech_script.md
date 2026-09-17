# Speaker Script / 演讲稿 — Z7 Phonon Collection Efficiency

约 13 分钟，11 页正片 + 6 页 backup。每页先中文、后英文，两段意思一样，**英文可以直接照着念**。
用词尽量简单；专业词保持原样。斜体是给自己的提示，不用念。**加粗的英文**是看着屏幕说的句子。

整个报告只讲一件事：**先说明一个脉冲怎么算出能量，再把同样的算法用到所有通道和所有事件。**
时间分配（秒）：1 题目 20 · 2 主要思路 60 · 3 公式 70 · 4 主图 60 · 5 峰高 110 · 6 功率和面积 90 · 7 为什么用拟合 80 · 8 其他通道 55 · 9 所有事件 70 · 10 求和 100 · 11 总结 50 → 约 765 秒。

---

## Slide 1 — Title（约 20 秒）

**中文**：大家好。今天讲 Z7 的声子收集效率。问题是：一个 10.37 keV 的事件发生在晶体里，有多少能量被 TES 吸收。我们得到的结果是 32%，误差正负 1%。我先用一个脉冲说明能量是怎么算的，再把同样的方法用到整个探测器。

**English**: Hi everyone. Today I will talk about the phonon collection efficiency of Z7. The question is: when a 10.37 keV event happens in the crystal, how much of the energy is absorbed by the TESs. Our result is 32 percent, with an uncertainty of plus or minus 1 percent. I will first use one pulse to show how the energy is calculated, and then apply the same method to the whole detector.

---

## Slide 2 — The Main Idea（约 60 秒）

**中文**：先给定义。这个定义只对工作在 0 伏的探测器成立，也就是没有 NTL 效应。收集效率等于 TES 吸收的能量除以 10.37 keV，TES 吸收的能量是所有通道加起来。为什么要求 0 伏：如果探测器加了电压，电子和空穴在电场里移动，会多产生一些声子，这就是 NTL 效应。那样晶体里的总能量就大于 10.37 keV，分母就不对了。屏幕上这一行是计算步骤：事件在晶体里产生声子，声子到达 TES，我们记录到电流的变化 δI，把 δI 换算成功率的变化 δP，对 δP 积分得到一个通道的能量，把所有通道加起来，最后除以 10.37 keV。数据来自 SNOLAB R4，是 Z7 上 Ge 活化产生的 K 线事件。选 Z7 是因为它的噪声低，K 线的峰和噪声触发分得很开，这些事件的能量都是 10.37 keV。

**English**: First, the definition. **It holds for a detector operated at zero volts, so with no NTL effect. The collection efficiency is the energy absorbed by the TESs divided by 10.37 keV,** and the absorbed energy is summed over all channels. Why zero volts: if there is a voltage on the detector, the electrons and holes move in the electric field and create extra phonons. This is the NTL effect. Then the total energy in the crystal is more than 10.37 keV, and the denominator would be wrong. **The line of boxes on the screen shows the steps:** the event creates phonons in the crystal, the phonons reach the TES, we record the change in current, δI, we turn it into the change in power, δP, the integral of δP is the energy in one channel, we add up all the channels, and we divide by 10.37 keV. The data are from SNOLAB R4: K-line events on Z7 from the germanium activation. We use Z7 because its noise is low and its K-line peak is well separated from the noise triggers. All of these events have the same energy, 10.37 keV.

---

## Slide 3 — The formula, and the two numbers it needs（约 70 秒）

**中文**：这一页是换算公式，我们用的是 CDMS 收集效率文档里的 Method 1。公式怎么来的，简单说一下：事件加热 TES，TES 的电阻变大，电流变小，TES 上的焦耳热也变小。脉冲结束后 TES 回到原来的温度。如果不考虑流到热浴的那部分热量，事件带进来的能量就等于焦耳热减少的总量。把电路方程代进去展开，就得到这个公式：δP 等于一个线性项加一个二次项。两个系数由这个通道的工作点决定：I₀ 是工作点上流过 TES 的电流，R₀ 是工作点上 TES 的电阻，R_L 是和 TES 串联的负载电阻，等于寄生电阻 R_p 加分流电阻 R_sh。幻灯片上列出了这三个数。对 PBS1，线性项系数是 0.45 微伏，二次项系数是 0.0385 欧姆。二次项很小，只占能量的 1% 多一点。第二行是能量。δI 用双指数函数拟合以后，δP 的积分可以直接写成公式，能量只和拟合得到的幅度 A 和两个时间常数有关。文档里还有一个 Method 2。它的线性项和 Method 1 一样，只有二次项不同：Method 1 是加 2R_L，Method 2 是减 R_L。链接在最下面。

**English**: This slide shows the conversion formula. **We use Method 1 from the CDMS collection-efficiency note.** Briefly, where it comes from: the event heats the TES, the TES resistance goes up, the current goes down, and the Joule heating on the TES goes down. After the pulse, the TES returns to its original temperature. If we ignore the heat that flows to the bath, the energy from the event equals the total decrease in Joule heating. Putting the circuit equation into this and expanding it gives the formula: **δP is a linear term plus a quadratic term.** The two coefficients are set by the operating point of the channel: the current through the TES at the bias point, the resistance of the TES at the bias point, and the load resistance in series with it, which is the parasitic resistance plus the shunt resistance. On the slide they are I₀, R₀ and R_L, with their values. **For PBS1, the linear coefficient is 0.45 microvolts and the quadratic coefficient is 0.0385 ohms.** The quadratic term is small, a little more than 1 percent of the energy. The second line is the energy. After we fit δI with a two-exponential function, the integral of δP can be written as a formula, and the energy depends only on the fitted amplitude A and the two time constants. **The note also gives a Method 2.** Its linear term is the same as in Method 1, and only the quadratic term is different: Method 1 has +2R_L, Method 2 has −R_L. The link is at the bottom.

---

## Slide 4 — Example: one pulse（约 60 秒）

**中文**：下面看一个例子：通道 PBS1，事件 30646，只画出脉冲附近这 1.3 毫秒，横轴从触发前 0.35 毫秒到触发后 0.95 毫秒。同一条波形，可以用 ADC 计数、电流和功率三种单位来读。上半部分是脉冲，下半部分是功率，细节下两页再说。这里先说明一点：双指数拟合用的是 100 kHz 低通滤波以后的波形，也就是蓝线，不是原始采样点。原始采样点只是画出来做对比。

**English**: Now an example: channel PBS1, event 30646, showing only 1.3 milliseconds around the pulse, from 0.35 milliseconds before the trigger to 0.95 after. **The same trace can be read in three units: as ADC counts, as current, and as power.** The top panel is the pulse and the bottom panel is the power; the details come on the next two slides. **One note first: the two-exponential fit is done on the trace after a 100 kilohertz low-pass filter, which is the blue line, not on the raw samples.** The raw samples are drawn only for comparison.

---

## Slide 5 — The height（约 110 秒）

*这页是重点，讲慢一点。*

**中文**：先说清楚一件事：这张图里红色的拟合曲线，是在 100 kHz 低通滤波之后的波形上拟合出来的，也就是蓝线，不是在灰色的原始采样点上。原始采样点只是画出来对照。下面看上半部分，问题是脉冲高度应该怎么取。图里各部分是：灰点是原始采样点，每 1.6 微秒一个；蓝线是 100 kHz 低通以后的波形；绿线是 20 kHz 低通以后的波形，官方的 Eabs 用这个滤波；红线是双指数拟合，上升时间 136 微秒，下降时间 213 微秒。红线两边的粉色带表示拟合加减一个 σ 的噪声，σ 等于 89 个 ADC，是在触发之前的基线上测的。黄色竖条标出脉冲的顶部，那里有 98 个采样点，都在峰高的 10% 以内。右上角的表列出四种取高度的方法：原始采样点的最大值是 885，100 kHz 滤波后的最大值是 786，20 kHz 滤波后的最大值是 737，拟合曲线的峰值是 717。原始最大值比拟合高 23%。原因是：顶部这 98 个点的真实高度差不多，每个点上都加了随机噪声。取最大值，得到的是噪声刚好最偏高的那个点，所以最大值会系统性地偏高。滤波可以减小这个偏差，但滤波太强也会把峰本身压低。拟合用的是上升、顶部和下降所有的点，噪声有正有负，会互相抵消，所以拟合的峰值没有这种偏高。后面所有的能量都用拟合结果来算。

**English**: One thing first: **the red fit in this figure is fitted to the trace after a 100 kilohertz low-pass filter, the blue line, not to the grey raw samples.** The raw samples are only drawn for comparison. Now the top panel, and the question is how to measure the pulse height. Here is what is in the plot. **The grey dots are the raw samples, one every 1.6 microseconds. The blue line is the trace after the 100 kilohertz low-pass filter. The green line is the trace after a 20 kilohertz low-pass filter, which is the filter used for the official Eabs. The red line is the two-exponential fit,** with a rise time of 136 microseconds and a fall time of 213 microseconds. **The pink band shows the fit plus or minus one sigma of noise;** sigma is 89 ADC, measured on the baseline before the trigger. **The yellow band marks the top of the pulse: it contains 98 samples, all within 10 percent of the peak height.** The table in the top right corner lists four ways to take the height: **the largest raw sample is 885, the largest value after the 100 kilohertz filter is 786, after the 20 kilohertz filter it is 737, and the peak of the fit is 717. The largest raw sample is 23 percent higher than the fit.** The reason is this: the 98 samples at the top have almost the same true height, and each one has random noise added to it. If we take the maximum, we get the sample where the noise happened to be the most positive, so the maximum is biased high. Filtering reduces this bias, but a strong filter also lowers the peak itself. The fit uses all the samples on the rise, the top, and the fall. The noise is sometimes positive and sometimes negative, so it averages out, and the fit peak does not have this bias. All energies from here on are calculated from the fit.

---

## Slide 6 — The power pulse, and its area（约 90 秒）

**中文**：再看下半部分。红线是把拟合得到的电流代入公式算出的功率，包括线性项和二次项。蓝色虚线只有线性项，和红线几乎重合。紫色点线只有二次项，因为太小，放大了 20 倍才画出来。功率峰值是 104.6 飞瓦，其中线性项 102.6，二次项 2.0。二次项占峰值功率的 1.9%，占能量的 1.3%。所以功率脉冲和电流脉冲的形状基本一样，只是单位不同，这也是上一页三条纵轴可以画在一起的原因。粉色面积就是这个通道吸收的能量，305 电子伏，其中 99% 落在图里画出的这段时间以内。灰点和绿线是用同一个公式算的原始采样点和 20 kHz 波形的功率，只做对比，它们在红线周围上下波动，这是噪声。最下面一行列出了这个通道的工作点参数，两个系数就是用这些数算的。

**English**: Now the bottom panel. **The red line is the power calculated by putting the fitted current into the formula, with both the linear term and the quadratic term. The blue dashed line is the linear term only, and it almost overlaps the red line. The purple dotted line is the quadratic term only; it is very small, so it is drawn 20 times larger.** The peak power is 104.6 femtowatts: 102.6 from the linear term and 2.0 from the quadratic term. The quadratic term is 1.9 percent of the peak power and 1.3 percent of the energy. So the power pulse has almost the same shape as the current pulse, only in different units, and this is why the three axes on the last slide can be drawn together. **The shaded area is the energy absorbed in this channel: 305 electron volts, and 99 percent of it is inside the time range drawn here.** The grey dots and the green line are the power from the raw samples and from the 20 kilohertz trace, using the same formula. They are only for comparison; they go up and down around the red line because of noise. The bottom line lists the operating point of this channel, which is used to calculate the two coefficients.

---

## Slide 7 — Why we integrate the fit, not the raw data（约 80 秒）

**中文**：有人可能会问：公式对任何电流都能用，为什么不直接对原始数据积分？这一页回答这个问题。上面一排是两个事件的原始电流。灰色是原始采样点，蓝色是 20 kHz 低通以后的波形，红色是拟合的脉冲，黑线是基线。每张图右上角的小图，把脉冲之后的部分放大，纵轴只有正负 25 纳安，橙色虚线是脉冲之后电流的平均值，左上方的橙色箭头指着它。左边的事件，脉冲之后电流回到了基线，只差 0.1 纳安。右边的事件，脉冲之后电流比基线低了 6 纳安。下面一排是累计能量，横轴和上面一样。红线是对拟合脉冲积分：触发前是 0，1 毫秒内升上去，然后保持不变，最后的值和绿色虚线的公式值相同。灰线是对原始数据积分。左边的事件，两者只差 11 电子伏。右边的事件，6 纳安的偏移比每个采样点上 28 纳安的噪声小很多，所以用眼睛看不出来。但是换算成功率是负 2.8 飞瓦，在 24 毫秒里积分就是负 420 电子伏。所以原始数据的积分最后是负 169 电子伏，而拟合给出 277 电子伏。结论是：能量要用拟合来算，这样不受峰值噪声和基线漂移的影响。

**English**: One question is: the formula works for any current, so why not integrate the raw data directly? This slide answers that. **The top row shows the raw current of two events. Grey is the raw samples, blue is the trace after a 20 kilohertz low-pass filter, red is the fitted pulse, and the black line is the baseline. The small panel in the top right of each plot zooms in on the part after the pulse, with a vertical range of only plus or minus 25 nanoamps; the orange dashed line there is the average current after the pulse, and the orange arrow points to it.** For the left event, the current returns to the baseline after the pulse, within 0.1 nanoamps. **For the right event, the current after the pulse is 6 nanoamps below the baseline.** **The bottom row shows the cumulative energy, on the same time axis.** Red is the integral of the fitted pulse: it is zero before the trigger, rises within one millisecond, and then stays flat, and its final value is the same as the formula value shown by the green dashed line. Grey is the integral of the raw data. For the left event, the two differ by 11 electron volts. For the right event, the 6 nanoamp offset is much smaller than the 28 nanoamps of noise on each sample, so we cannot see it by eye. But as power it is minus 2.8 femtowatts, and over 24 milliseconds this adds up to minus 420 electron volts. **So the integral of the raw data ends at minus 169 electron volts, while the fit gives 277 electron volts.** The conclusion is that the energy should be calculated from the fit, so that it is not affected by the noise at the peak or by baseline drift.

---

## Slide 8 — The same event in its other channels（约 55 秒）

**中文**：一个通道讲完了，下面对同一个事件的 11 个通道都做同样的计算，这里显示其中 4 个。右边的表格列出了这个事件 11 个通道各自的能量。差别很大：PES1 是 489 电子伏，PES2 只有 195 电子伏。按面来看，第 1 面一共 2062 电子伏，占 60%；第 2 面 1357 电子伏，占 40%，说明这个事件可能发生在靠近第 1 面的位置。要注意 Z7 的 PFS2 没有读出，所以第 2 面只有 5 个通道。11 个通道加起来是 3419 电子伏，是 10.37 keV 的 33%。作为检查，用官方的积分窗口直接对原始波形积分，加起来是 3397 电子伏，两者差 0.6%。右下角的 PDS2 波形上有一个很慢的大起伏，第 10 页会说它带来的影响。

**English**: That is one channel. Next, we do the same calculation for all 11 channels of the same event; 4 of them are shown here. **The table on the right lists the energy of each of the 11 channels for this event. They are very different: PES1 has 489 electron volts and PES2 only 195. By face, side 1 has 2062 electron volts, 60 percent of the total, and side 2 has 1357, 40 percent,** so this event probably happened closer to side 1. Note that PFS2 is not read out on Z7, so side 2 has only 5 channels. **The sum over the 11 channels is 3419 electron volts, which is 33 percent of 10.37 keV.** As a check, if we use the official integration window directly on the raw traces, the sum is 3397 electron volts, and the two differ by 0.6 percent. **Bottom right, the PDS2 trace has a slow, large swing;** what it costs us comes on slide 10.

---

## Slide 9 — Now every event: one channel（约 70 秒）

**中文**：从一个事件扩展到所有事件。这里还是 PBS1，一共 1917 个事件，每个事件做一次拟合和一次积分，得到一个能量。横轴是能量，每格 10 电子伏，纵轴是事件数。红色来自拟合，灰色轮廓来自官方窗口对原始波形的积分，两者的峰位只差 0.2%。峰在 285 电子伏，宽度 42 电子伏，也就是 15%。要注意，这些事件的真实能量都一样，但分布的宽度有 15%。分布的右边有一条长尾，一直到 600 电子伏左右，这些是离 PBS1 比较近的事件。所以一个通道的宽度主要来自事件发生的位置，而不是噪声。下一页会看到证据：把通道加起来以后宽度会明显变小。虚线是只对中间部分做的高斯拟合，所以 μ 是峰的位置，不是平均值。

**English**: Now we go from one event to all events. **This is still PBS1, with 1917 events. For each event we do one fit and one integral, and get one energy. The horizontal axis is energy, 10 electron volts per bin, and the vertical axis is the number of events. Red is from the fit, the grey outline is from the official window on the raw traces, and their peaks differ by only 0.2 percent. The peak is at 285 electron volts and the width is 42 electron volts, which is 15 percent.** Note that all of these events have the same true energy, but the distribution is 15 percent wide. **The distribution has a long tail on the right, up to about 600 electron volts;** these are events that happened closer to PBS1. So the width in one channel comes mainly from where the event happened, and not from noise. The next slide shows the evidence: when we add the channels, the width becomes much smaller. The dashed curve is a Gaussian fit to the central part only, so mu is the position of the peak, not the mean.

---

## Slide 10 — Summed over the channels: 32 ± 1 %（约 100 秒）

**中文**：这是结果。对每一个事件，把各通道的能量加起来，再看这些总能量的分布。灰色是 10 个通道的和。和上一页比有两个变化：宽度从 15% 降到 7.5%，而且分布变对称了。这说明事件位置造成的差别，在求和以后大部分互相抵消了。峰的位置在 10.37 keV 的 30.5%，这就是这 10 个通道收到的能量。为什么是 10 个通道？因为 PDS2 有低频起伏，只有一部分事件能拟合成功，所以先把它单独放在一边。绿色是把 PDS2 也加进来的结果，但它只包括 PDS2 拟合成功的那些事件，这批事件不能代表全部事件，所以 PDS2 的贡献只能给一个范围。算下来完整的效率在 31.5% 到 32.9% 之间，写成 32% 加减 1%。要缩小这个范围，需要解决 PDS2 的噪声问题，增加事件数没有帮助。最右边的红线是 10.37 keV，可以看到大约三分之二的能量没有被 TES 吸收。

**English**: This is the result. For each event we add up the energies of the channels, and then look at the distribution of these totals. **Grey is the sum over 10 channels.** Two things change compared with the last slide: **the width drops from 15 percent to 7.5 percent, and the distribution becomes symmetric.** So most of the difference caused by the event position cancels when we add the channels. **The peak sits at 30.5 percent of 10.37 keV,** which is the energy these 10 channels collect. Why 10 channels? Because PDS2 has the low-frequency swing and only part of its events can be fitted, so we keep it aside for a moment. Green is the sum including PDS2, but only for the events where PDS2 is fitted, and those events are not representative of all events, so we can only give a range for its contribution. **That puts the full efficiency between 31.5 and 32.9 percent, which we write as 32 plus or minus 1 percent.** To make the range smaller we need to fix the noise in PDS2; more events would not help. **The red line on the far right is 10.37 keV:** about two thirds of the energy is not absorbed by the TESs.

---

## Slide 11 — Summary, and what is still open（约 50 秒）

**中文**：总结一下。第一，用 TES 的公式把电流脉冲换算成功率脉冲，功率曲线下的面积就是能量，公式里的二次项只占 2% 左右。第二，能量用拟合的脉冲来算，这样不受峰值噪声和基线漂移的影响。第三，一个通道的能量分布宽 15%，而且不对称，主要是事件位置的影响；10 个通道加起来以后宽 7.5%，而且对称。结果是：Z7 的 TES 吸收了 10.37 keV 事件能量的 32% 加减 1%。CDMS 文档在 R37 的 CUTE tower 上得到的是 26% 到 41%，我们的结果在这个范围内。还没有解决的问题有：目前只做了 Z7；Z7 在这些 series 里是否是 0 伏还没有确认，我们是按 0 伏算的；没有 dI/dV 数据，公式里的电感项没有包括；PDS2 的噪声带来了正负 1% 的误差；还有 12.5% 的事件在所有通道都拟合失败，没有进入统计。谢谢大家。

**English**: To summarize. First, we use the TES formula to convert the current pulse into a power pulse, and the area under the power curve is the energy; the quadratic term is only about 2 percent. Second, we calculate the energy from the fitted pulse, so it is not affected by the noise at the peak or by baseline drift. Third, in one channel the energy distribution is 15 percent wide and not symmetric, mainly because of the event position; after adding 10 channels it is 7.5 percent wide and symmetric. **The result is that the TESs of Z7 absorb 32 plus or minus 1 percent of the energy of a 10.37 keV event. The CDMS note found 26 to 41 percent on the R37 CUTE tower, and our result is within this range.** Open issues: so far we have only done Z7; we have not confirmed that Z7 was at zero volts in these series, and we assume zero volts; there is no dI/dV data, so the inductor term in the formula is not included; the noise in PDS2 gives the plus or minus 1 percent; and 12.5 percent of the events could not be fitted in any channel and are not included. Thank you.

---

## Backup（仅备查，不占正片时间）

**B1 事件谱**：Z7 的 PTOFamps 分布。紫色是我们用 Prompt 处理结果重新画的，没有加 cut；黑色是运行记录里的图；红线是 K 线的位置，2 乘 10 的负 6 次方安培。
**B1 The events**: the PTOFamps distribution of Z7. Purple is our own plot from the Prompt processing, with no cut. Black is the plot from the ops note. The red line is the K-line position, 2 times 10 to the minus 6 amps.

**B2 两个 Method 和官方 Eabs**：公式是 δP = I₀(R_L − R₀)·δI + c₂·R_L·(δI)²。c₂ 等于 2 是 Method 1（本报告用的），等于负 1 是 Method 2；两者算出的能量差 1.7%。官方 Eabs 我们自己重新算了一遍，差别在 0.2% 以内。它的做法是：触发在第 16383 个点，基线用第 93 到 15758 个点的平均值，用 5 阶 20 kHz Butterworth 滤波，积分窗口从触发前 0.5 毫秒到触发后 1 毫秒。
**B2 The two Methods and the official Eabs**: the formula is δP = I₀(R_L − R₀)·δI + c₂·R_L·(δI)². c₂ = 2 is Method 1, the one used here, and c₂ = −1 is Method 2; the two differ by 1.7 percent in energy. We reproduce the official Eabs to within 0.2 percent. It uses the trigger at sample 16383, the baseline as the mean of samples 93 to 15758, a 5-pole 20 kilohertz Butterworth filter, and an integration window from 0.5 milliseconds before to 1 millisecond after the trigger.

**B3–B6**：完整的原图：15 个事件的电流和功率图、15 个事件的累计能量图、事件 30646 所有通道的图、11 个通道各自的能量分布（每个通道都是右边长，PDS2 标出没有加进总和）。
**B3–B6**: the full original figures: current and power for 15 events, cumulative energy for 15 events, all channels of event 30646, and the energy distribution of each of the 11 channels (each has a long tail on the right; PDS2 is marked as not included in the sum).

---

## 可能被问的问题 / Likely questions（回答一两句就够）

**Q1. 蓝线上有规律的小波纹是什么？/ What is the regular ripple on the blue line?**
中文：是 66 kHz 的噪声，它在这个频率上比附近频率高大约 700 倍，150 个事件平均以后也一样。100 kHz 低通滤不掉它，20 kHz 低通可以滤掉。
English: It is noise at 66 kilohertz. At this frequency it is about 700 times higher than at nearby frequencies, and it is also there in the average of 150 events. The 100 kilohertz low-pass filter does not remove it; the 20 kilohertz filter does.

**Q2. 为什么脉冲在时间 0 之前就开始了？/ Why does the pulse start before time zero?**
中文：时间 0 是波形里固定的触发位置，第 16383 个点。拟合得到的脉冲起点在触发前 0.175 毫秒。这个差别的原因我们还没有查。
English: Time zero is the fixed trigger position in the trace, sample 16383. The fitted pulse starts 0.175 milliseconds before it. We have not yet checked the reason for this difference.

**Q3. 原始最大值偏高 23% 是不是每个事件都这样？/ Is the 23 % bias of the raw maximum the same for every event?**
中文：23% 只是这一个事件的数。如果有 100 个互相独立的噪声点，最大值平均在 2.5σ 左右；这里是 1.88σ，因为相邻的点不是完全独立的，而且顶部的点比峰稍低。我们没有对所有事件做统计。
English: The 23 percent is for this event only. For 100 independent noise samples, the maximum is about 2.5 sigma on average; here it is 1.88 sigma, because neighboring samples are not fully independent, and the samples at the top are a little lower than the peak. We have not done this for all events.

**Q4. 为什么不直接用官方的 Eabs？/ Why not just use the official Eabs?**
中文：我们重复算出了官方 Eabs，差别在 0.2% 以内，峰位也和拟合方法一致。但是官方 Eabs 是对原始波形积分，结果会受积分窗口和基线的影响。拟合方法不受峰值噪声和基线漂移的影响，也不需要选积分窗口。两种方法可以互相检查。
English: We reproduce the official Eabs to within 0.2 percent, and its peak agrees with the fit method. But the official Eabs integrates the raw trace, so the result depends on the integration window and the baseline. The fit method is not affected by noise at the peak or by baseline drift, and it does not need an integration window. The two methods check each other.

**Q5. PDS2 有什么问题？/ What is wrong with PDS2?**
中文：PDS2 的波形上有一个低频的大起伏，大约 5 毫秒以后很明显，所以双指数拟合的残差超过了标准。原因还没有查清楚。做脉冲模板的时候也看到过这个问题。
English: The PDS2 trace has a large low-frequency swing, clearly visible after about 5 milliseconds, so the two-exponential fit residual is above the limit. The cause is not known yet. We also saw this problem when making the pulse templates.

**Q6. 为什么不能把各通道的高斯峰位相加？/ Why can't the Gaussian peaks of the channels be added?**
中文：每个通道的分布右边长，峰位比平均值小。事件总能量的平均值等于各通道平均值之和，不等于各通道峰位之和。把峰位相加会低 21%。
English: Each channel's distribution has a long tail on the right, so its peak is lower than its mean. The mean of the total energy equals the sum of the channel means, not the sum of the channel peaks. Adding the peaks gives a value that is 21 percent too low.

**Q7. 拟合失败的 12.5% 事件怎么处理？/ What about the 12.5 % of events that could not be fitted?**
中文：还没有检查。如果这些事件的能量分布和其他事件不同，效率会有偏差。这是下一步要做的。
English: We have not checked them yet. If their energy distribution is different from the other events, the efficiency could be biased. This is one of the next steps.

**Q8. 如果不是 0 伏，结果会怎么变？/ How would the result change if the detector was not at zero volts?**
中文：如果有电压，晶体里的总能量等于 10.37 keV 加上 NTL 效应多产生的能量，分母变大，效率会变小。Z7 在这些 series 里的电压还没有确认，所以现在按 0 伏算。
English: With a voltage, the total energy in the crystal is 10.37 keV plus the extra energy from the NTL effect. The denominator gets larger, so the efficiency gets smaller. We have not confirmed the voltage of Z7 in these series, so for now we assume zero volts.

**Q9. 公式里的电感项是怎么处理的？/ How is the inductor term handled?**
中文：完整的方程里有一项和电感、loop gain 有关，是一个小的修正。MSI 上没有这些 series 的 dI/dV 数据，所以没有 L 和 loop gain 的值，这一项没有包括，也没办法检查。
English: The full equations have a term that depends on the inductance and the loop gain; it is a small correction. There is no dI/dV data for these series on MSI, so we do not have the values of L and the loop gain. This term is not included and could not be checked.

**Q10. 公式是怎么推导出来的？/ How is the formula derived?**
中文：第一步，写出 TES 的热平衡方程，对整个脉冲积分。脉冲结束后温度回到原值，所以热容那一项积分是 0；如果不考虑流到热浴的热量，事件能量等于焦耳热减少量的积分。第二步，用电路方程 V_TES = V − I·R_L − L·dI/dt，焦耳热是 I 乘 V_TES。第三步，把 I 写成 I₀ + δI 代进去展开。第四步，对整个脉冲积分，电感项在开始和结束时都是 0，所以积分为 0。最后得到的形式就是幻灯片上的公式：一个线性项 I₀(R_L − R₀)·δI 加上一个二次项。
English: Step one: write the heat balance equation of the TES and integrate it over the whole pulse. After the pulse the temperature returns to its original value, so the heat-capacity term integrates to zero. If we ignore the heat flow to the bath, the event energy equals the integral of the decrease in Joule heating. Step two: use the circuit equation, V_TES = V − I·R_L − L·dI/dt; the Joule heating is I·V_TES. Step three: write I as I₀ + δI and expand. Step four: integrate over the whole pulse; the inductor term is zero at the start and at the end, so its integral is zero. The result has the form on the slide: a linear term, I₀(R_L − R₀)·δI, plus a quadratic term.

**Q11. CDMS 文档说 Method 2 更准一些，为什么用 Method 1？/ The note says Method 2 is a bit more accurate. Why use Method 1?**
中文：两种方法只有二次项不同，算出的能量差 1.7%，比单个通道 15% 的宽度和 PDS2 带来的正负 1% 都小，所以对这个结果影响很小。用 Method 1 是导师的决定。如果需要，用 Method 2 重算一遍很快。
English: The two methods differ only in the quadratic term, and the energies differ by 1.7 percent. That is smaller than the 15 percent width in one channel and smaller than the plus or minus 1 percent from PDS2, so it has little effect on the result. Using Method 1 was my supervisor's decision, and redoing the numbers with Method 2 would be quick if needed.

---

## 术语自查表（只给自己，不进 PPT）

- δI：脉冲引起的电流变化，已经减去基线。
- I₀：TES 工作点的电流；R₀：工作点的电阻；R_L = R_p + R_sh：负载电阻。
- 线性项 I₀(R_L−R₀)·δI：焦耳热随电流变化的一阶部分；二次项 2R_L·(δI)²：二阶部分（Method 1）。
- 解析积分 / closed form：能量直接用拟合的 A、τ_f、τ_r 代入公式计算，不做数值积分。
- NRMSE：拟合残差除以峰高；小于等于 0.2 的拟合才保留，正常的拟合在 0.03 到 0.07 之间。
- 10 个通道 / core channels：拟合成功率在 90% 以上的通道，不包括 PDS2。
- 高斯峰位 μ：只对分布中间部分做高斯拟合得到的峰位置，不是平均值。
- NTL 效应：探测器加电压时，电子和空穴在电场里移动产生额外声子。
