# Speaker Script / 演讲稿 — Z7 Phonon Collection Efficiency

约 13 分钟，11 页正片 + 6 页 backup。每页先中文、后英文，两段意思一样，**英文可以直接照着念**。
用词尽量简单；专业词保持原样。斜体是给自己的提示，不用念。**加粗的英文**是看着屏幕说的句子。

整个报告只讲一件事：**先说明一个脉冲怎么算出能量，再把同样的算法用到所有通道和所有事件。**
时间分配（秒）：1 题目 20 · 2 主要思路 45 · 3 公式 65 · 4 主图 35 · 5 峰高 65 · 6 功率和面积 50 · 7 为什么用拟合 70 · 8 其他通道 50 · 9 所有事件 55 · 10 求和 70 · 11 总结 35 → 约 560 秒（约 9.5 分钟；讲的时候留出停顿和指图的时间，大约 12 分钟）。

---

## Slide 1 — Title（约 20 秒）

**中文**：大家好，我叫李知恒，来自明尼苏达大学。今天讲 Z7 的声子收集效率。问题是：一个 10.37 keV 的事件发生在晶体里，有多少能量被 TES 吸收。我们得到的结果是 30.5%，用的是 10 个通道；另外两个排除了，一个数据缺失，一个噪声太大。我先用一个脉冲说明能量是怎么算的，再把同样的方法用到整个探测器。

**English**: Hi everyone, my name is Zhiheng Li, from the University of Minnesota. Today I will talk about the phonon collection efficiency of Z7. The question is: when a 10.37 keV event happens in the crystal, how much of the energy is absorbed by the TESs. Our result is 30.5 percent, from 10 channels. We leave out two: one is missing, and one is too noisy. I will first use one pulse to show how the energy is calculated, and then apply the same method to the whole detector.

---

## Slide 2 — The Main Idea（约 45 秒）

**中文**：先给定义。这个定义针对工作在 0 伏的探测器，没有 NTL 效应。收集效率等于 TES 吸收的能量除以 10.37 keV，TES 吸收的能量是所有通道加起来。屏幕上这一行是计算步骤：事件在晶体里产生声子，声子到达 TES，我们记录到电流的变化 δI，把 δI 换算成功率的变化 δP，对 δP 积分得到一个通道的能量，把所有通道加起来，最后除以 10.37 keV。选 Z7 是因为它的噪声低，K 线的峰和噪声触发分得很开。

**English**: First, the definition. This is for a detector at zero volts, with no NTL effect. The collection efficiency is the energy absorbed by the TESs divided by 10.37 keV, and the absorbed energy is summed over all channels. **The line of boxes on the screen shows the steps: the event creates phonons in the crystal, the phonons reach the TES, we record the change in current, δI, we turn it into the change in power, δP, the integral of δP is the energy in one channel, we add up all the channels, and we divide by 10.37 keV.** We use Z7 because its noise is low and its K-line peak is well separated from the noise triggers.

---

## Slide 3 — The formula, and the two numbers it needs（约 65 秒）

**中文**：这一页是换算公式，我们用的是 CDMS 收集效率文档里的 Method 1。公式怎么来的：事件加热 TES，TES 的电阻变大，焦耳热变小。如果不考虑流到热浴的那部分热量，事件带进来的能量就等于焦耳热减少的总量。算下来就得到这个公式：δP 等于一个线性项加一个二次项。两个系数来自这个通道的工作点，幻灯片上的 I₀、R₀、R_L 就是。R_L 是和 TES 串联的负载电阻，等于寄生电阻加分流电阻。对 PBS1，线性项系数是 0.45 微伏，二次项系数是 0.0385 欧姆。二次项很小，只占能量的 1% 多一点。第二行是能量。δI 用双指数拟合，所以 δP 的积分是一个简单的公式，能量只和幅度和两个时间常数有关。文档里还有一个 Method 2。唯一的区别是二次项，它是负的 R_L，而不是 2R_L。链接在最下面。

**English**: This slide shows the conversion formula. **We use Method 1 from the CDMS collection-efficiency note.** Where it comes from: the event heats the TES, its resistance goes up, and its Joule heating goes down. If we ignore the heat that flows to the bath, the event energy equals the total drop in Joule heating. Working this out gives the formula: δP is a linear term plus a quadratic term. The two coefficients come from the operating point of the channel: I₀, R₀ and R_L on the slide. **R_L is the load resistance in series with the TES, and it equals the parasitic resistance plus the shunt resistance.** **For PBS1, the linear coefficient is 0.45 microvolts and the quadratic coefficient is 0.0385 ohms.** The quadratic term is small, a little more than 1 percent of the energy. **The second line is the energy. Because δI is fitted with two exponentials, the integral is a simple formula: the energy depends only on the amplitude and the two time constants.** **The note also gives a Method 2.** The only difference is the quadratic term, which is negative R_L instead of 2R_L. The link is at the bottom.

---

## Slide 4 — Example: one pulse（约 35 秒）

**中文**：下面看一个例子：通道 PBS1，事件 30646，只画出脉冲附近这 1.3 毫秒，横轴从触发前 0.35 毫秒到触发后 0.95 毫秒。同一条波形，可以用 ADC 计数、电流和功率三种单位来读。上半部分是脉冲，下半部分是功率，细节下两页再说。

**English**: Now an example: channel PBS1, event 30646, showing only 1.3 milliseconds around the pulse, from 0.35 milliseconds before the trigger to 0.95 after. **The same trace can be read in three units: as ADC counts, as current, and as power.** The top panel is the pulse and the bottom panel is the power; the details come on the next two slides.

---

## Slide 5 — The height（约 65 秒）

*这页指着图讲。*

**中文**：这是同一个脉冲的顶部放大。灰点是原始采样点。蓝线是同一条波形过了 100 kHz 低通之后的结果。红线是双指数拟合，拟合是在蓝线上做的。绿线是 20 kHz 低通，官方的 Eabs 用它。黄色竖条是脉冲的顶部，那里有近百个采样点，高度差不多。右上角的表是四种取高度的方法。**取原始采样点的最大值会偏高 23%**，因为挑到的是噪声最大的那个点。拟合用了所有的点，噪声互相抵消。所以我们用拟合来算能量。

**English**: **This is the top of the same pulse, zoomed in. Grey is the raw samples. Blue is the same trace after a 100 kilohertz low pass. Red is the two-exponential fit, and it is fitted on the blue line. Green is a 20 kilohertz low pass, which the official Eabs uses.** The yellow band is the top of the pulse, where about a hundred samples have almost the same height. The table lists four ways to take the height. **Taking the largest raw sample is 23 percent too high,** because it picks the sample with the most noise. The fit uses all the samples, so the noise averages out. That is why we use the fit to calculate the energy.

---

## Slide 6 — The power pulse, and its area（约 50 秒）

**中文**：这是同一个脉冲的功率。红线是拟合算出的功率，两项都算。蓝色虚线只有线性项，和红线几乎重合。橙色点线只有二次项，放大 20 倍才看得见。灰点是原始采样点算出的功率。绿线是 20 kHz 波形算出的功率。**粉色面积就是这个通道吸收的能量**，二次项只占其中 1.3%。

**English**: This is the power of the same pulse. Red is the power from the fit, with both terms. The blue dashed line is the linear term alone, and it almost overlaps the red. The orange dotted line is the quadratic term alone, drawn twenty times larger. The grey dots are the power from the raw samples. The green line is the power from the 20 kilohertz trace. **The shaded area is the energy absorbed in this channel,** and the quadratic term is only 1.3 percent of it.

---

## Slide 7 — Why we integrate the fit, not the raw data（约 70 秒）

**中文**：为什么不直接对原始数据积分？这一页就是答案。上面一排是两个事件的原始电流，红色是拟合出来的脉冲，黑线是基线。右上角的小图是脉冲之后那段的放大，橙色线是那段电流的平均值。左边这个事件，脉冲之后电流回到了基线；右边这个事件，明显低于基线。这点偏移埋在噪声里，用眼睛看不出来。下面一排是累计能量，横轴和上面一样。红线是对拟合脉冲积分：跟着脉冲升上去，然后保持不变，停在绿线上，绿线是公式算出的能量。灰线是对原始数据积分：左边和红线差不多，右边却一路往下，最后变成负的。积分把上面那点偏移一直累加下去。能量不可能是负的，所以我们用拟合来算。

**English**: Why not integrate the raw data directly? This slide shows why. **The top row shows the raw current of two events, with the fitted pulse in red and the baseline in black.** The small panel zooms in after the pulse; the orange line is the average current there. **On the left the current comes back to the baseline; on the right it stays below the baseline.** That offset is buried in the noise, so we cannot see it by eye. **The bottom row shows the cumulative energy, on the same time axis.** Red is the integral of the fit: it rises with the pulse, then stays flat, on the green line from the formula. **Grey is the integral of the raw data: on the left it is close to the red curve, but on the right it keeps going down and ends up negative.** The integral keeps adding up that small offset. An energy cannot be negative, so we use the fit.

---

## Slide 8 — The same event in its other channels（约 50 秒）

**中文**：一个通道讲完了，下面对同一个事件的 11 个通道都做同样的计算，这里显示其中 4 个。右边的表格列出了这个事件 11 个通道各自的能量，差别很大，最多的那个通道是最少的两倍多。第 1 面占 60%，第 2 面占 40%，所以这个事件发生在靠近第 1 面的位置。要注意 Z7 的 PFS2 没有读出，所以第 2 面只有 5 个通道。11 个通道加起来是 10.37 keV 的 33%。这是一个事件，而且含 PDS2。作为检查，用官方的算法在同一个事件上给出的结果差 0.6%。

**English**: That is one channel. Next, we do the same calculation for all 11 channels of the same event; 4 of them are shown here. **The table on the right lists the energy of each of the 11 channels for this event. They are very different: the largest channel has more than twice the smallest. Side 1 gets 60 percent and side 2 gets 40 percent,** so the event was closer to side 1. Note that PFS2 is not read out on Z7, so side 2 has only 5 channels. **Summed over the 11 channels, the event gives 33 percent of 10.37 keV.** This is one event, including PDS2. The official method gives the same result within 0.6 percent.

---

## Slide 9 — Now every event: one channel（约 55 秒）

**中文**：从一个事件扩展到所有事件。这里还是 PBS1，每个事件做一次拟合和一次积分，得到一个能量。横轴是能量，纵轴是事件数。红色来自拟合，灰色是官方的算法，两者的峰位差 0.2%。红色那条分布的峰在 285 电子伏。这些事件的能量都一样，但分布有 15% 宽。分布的右边有一条长尾，这些是离 PBS1 比较近的事件。所以宽度来自事件发生的位置，不是噪声。下一页会看到这一点。

**English**: Now we go from one event to all events. **This is still PBS1. For each event we do one fit and one integral, and get one energy. The horizontal axis is energy and the vertical axis is the number of events. Red is from the fit, grey is the official method, and the peaks agree within 0.2 percent. The peak is at 285 electron volts.** All these events have the same energy, but the width is 15 percent. **The distribution has a long tail on the right;** these are events that happened closer to PBS1. So the width comes from where the event happened, not from noise. The next slide shows this.

---

## Slide 10 — Summed over the channels: 30.5 %（约 70 秒）

**中文**：这是结果。对每个事件把各通道的能量加起来，再看这些总能量的分布。和上一页比，宽度从 15% 降到 7.5%，而且变对称了，说明事件位置造成的差别在求和后大部分抵消了。灰色是 10 个通道的和，峰在 10.37 keV 的 30.5%。这里没算 PDS2：它只有大约 40% 的事件能拟合上，能拟合上的都是信号明显的事件，也就是发生位置偏向 PDS2 的事件，所以我们把它排除。宽度除以峰位是 7.5%，这就是我们的误差。最右边的红线是 10.37 keV，可以看到大约三分之二的能量没有被 TES 吸收。

**English**: This is the result. For each event we add up the energies of the channels and look at the distribution of these totals. **Compared with the last slide, the width drops from 15 percent to 7.5 percent and the distribution becomes symmetric,** so most of the difference from the event position cancels in the sum. **Grey is the sum over 10 channels, and its peak sits at 30.5 percent of 10.37 keV.** PDS2 is not in it: only about 40 percent of its events can be fitted, and those are the events with a clear signal, so they happened closer to PDS2. That is why we leave it out. **The width over the peak, 7.5 percent, is our uncertainty.** **The red line on the far right is 10.37 keV:** about two thirds of the energy is not absorbed by the TESs.

---

## Slide 11 — Summary, and what is still open（约 35 秒）

**中文**：总结三句话。第一，把电流脉冲换算成功率脉冲，功率曲线下的面积就是能量，而且能量用拟合来算，不受噪声和基线漂移的影响。第二，结果是 Z7 的 TES 吸收了一个 10.37 keV 事件能量的 30.5%，用 10 个通道，排除了没有读出的和噪声大的那两个；CDMS 文档在 R37 的 CUTE tower 上得到 26% 到 41%，我们落在这个范围里。第三，还没解决的：只做了 Z7，其他探测器还没做；Z7 的偏压还没确认；没有 dI/dV 数据；PDS2 因为噪声没有算进去；还有 12.5% 的事件拟合不上。谢谢大家。

**English**: In summary. First, we turn the current pulse into a power pulse, the area under the power is the energy, and we take it from the fit, so the noise at the peak and the baseline drift do not enter. **Second, the TESs of Z7 absorb 30.5 percent of the energy of a 10.37 keV event, from 10 channels, with the unread and the noisy one left out, and the CDMS note found 26 to 41 percent on the R37 CUTE tower, so we sit inside that range.** Third, what is still open: only Z7 so far, the bias of Z7 is not confirmed, there is no dI/dV data, PDS2 is not included because of its noise, and 12.5 percent of the events could not be fitted. Thank you.

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
中文：两种方法只有二次项不同，算出的能量差 1.7%，比单个通道 15% 的宽度和求和后 7.5% 的宽度都小，所以对这个结果影响很小。用 Method 1 是导师的决定。如果需要，用 Method 2 重算一遍很快。
English: The two methods differ only in the quadratic term, and the energies differ by 1.7 percent. That is smaller than the 15 percent width in one channel and smaller than the 7.5 percent width of the sum, so it has little effect on the result. Using Method 1 was my supervisor's decision, and redoing the numbers with Method 2 would be quick if needed.

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
