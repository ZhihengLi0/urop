# Speaker Script / 演讲稿: LED runs in SNOLAB Run 7

约 9 分钟，12 页正片，后面是备用页（只在被问到时用）。每页先中文、后英文，意思一样，英文可以直接照着念。

时间（秒）：1 Title 15，2 Background 45，3 One LED run 40，4 Visibility: phase 1 55，5 Visibility: phase 2 35，6 Stability: amplitude vs time 50，7 Amplitude: cases to look at again 50，8 Stability: trigger fraction vs time 55，9 Template generation: method 65，10 Templates: example 30，11 Example pulses: Z7 PSum with Z7's LED 60，12 Summary 40；合计约 540 秒。

---

## Slide 1: Title（约 15 秒）

**中文**：大家好，我是李志恒。今天讲 Run 7 的 LED 数据。按老师说的四点讲：谁看到哪个 LED，幅度稳不稳，触发稳不稳，还有脉冲模板。

**English**: Hi everyone, I'm Zhiheng. Today I'll show the LED data from Run 7. Four points: who sees which LED, amplitude stability, trigger stability, and pulse templates.


---

## Slide 2: Background（约 45 秒）

**中文**：先说背景。这是 Run 7 在 Cf 刻度之后的数据。DAQ 脚本一直循环：先取低本底数据，再取一个 LED run，大概每 2 个小时一次。上面每一条竖线是一个 LED run。从 9 月 15 号到 21 号一共 47 个，我们用了 45 个。

**English**: First, the background. This is Run 7 data after the Cf calibration. The DAQ script runs in a loop: low-background data, then one LED run, about every 2 hours. Each line on the top is one LED run. From September 15 to 21 there are 47 of them, and we use 45.


---

## Slide 3: One LED run（约 40 秒）

**中文**：一个 LED run 里面是这样的。第一段 15 个 LED 在闪，停 3 秒，第二段换 12 个 LED。每个 LED 每秒闪一次，一共 151 次。每次触发只读出触发的那个探测器。

**English**: Inside one LED run: in phase one, 15 LEDs flash. Then 3 seconds off. In phase two, 12 LEDs flash. Each LED flashes once per second, 151 times. Each trigger reads out only the detector that triggered.


---

## Slide 4: Visibility: phase 1（约 55 秒）

**中文**：这是第一段的可见度图。横轴是 LED，纵轴是探测器。格子里的数是：这个 LED 闪的时候，这个探测器触发的比例。红框是 LED 自己的探测器，基本都是 1。红框旁边的格子，是隔壁的探测器也看到了光。

**English**: This is the visibility plot for phase one. Columns are LEDs, rows are detectors. The number is how often the detector triggers when that LED flashes. The red box is the LED's own detector, and it is almost always one. A number next to a red box means the neighbouring detector also sees the light.


---

## Slide 5: Visibility: phase 2（约 35 秒）

**中文**：第二段也一样。自己的探测器基本每次都触发，隔壁的探测器也经常触发。光只到相邻的探测器，再远就没有了。

**English**: Phase two shows the same pattern. The own detector triggers almost every time, and often the next detector too. The light only reaches the next detector, never further.


---

## Slide 6: Stability: amplitude vs time（约 50 秒）

**中文**：第二点，幅度随时间。每一行是一个格子，每一列是一个 series，按时间排。白色就是正常。大部分是白的，91% 的点变化在 10% 以内。所以大部分是稳定的，但有几个地方要再看。

**English**: Second, amplitude versus time. Each row is one cell, each column is one series, in time order. White means normal. Most of it is white: 91 percent of the points are within 10 percent. So it is mostly stable, but a few spots need a second look.


---

## Slide 7: Amplitude: cases to look at again（约 50 秒）

**中文**：这几个要再看。最明显的是 9 月 18 号凌晨，Z20 的 LED 一下子暗了很多，过了几个小时又恢复了。Z19 看 Z20 的 LED 也变暗，所以是 LED 的问题，不是探测器。还有第一天几个格子偏高一点。

**English**: These need a second look. The clearest one: early on September 18, Z20's LEDs became much dimmer, and a few hours later they were back to normal. Z19 also saw Z20's LED get dimmer, so it is the LED, not the detector. Also, on the first day a few cells are a bit high.


---

## Slide 8: Stability: trigger fraction vs time（约 55 秒）

**中文**：第三点，触发比例随时间。黄色是每次闪光都触发。自己 LED 的格子一直是黄的，很稳定。其他格子有台阶。我查了数据库，台阶正好在触发阈值被改的地方，就是图上的黑线。所以这是设置变了，不是探测器不稳定。

**English**: Third, trigger fraction versus time. Yellow means it triggers on every flash. The own-LED cells stay yellow: stable. Other cells have steps. I checked the ODB: the steps are exactly where the trigger thresholds were changed, the black lines. So these are setting changes, not unstable detectors.


---

## Slide 9: Template generation: method（约 65 秒）

**中文**：第四点，模板。先说怎么做的。第一步，选事件：这个 LED 闪的时候，这个探测器触发的事件，十二个通道都用。第二步，用一个很短的中值滤波，去掉 LED 通电带来的窄尖峰。第三步，100 千赫的低通滤波。第四步，减掉基线，再除以峰值。第五步，每个脉冲用两个指数拟合，起始时间是自由的。右上图就是一个脉冲和它的拟合。第六步，按拟合出来的起始时间，把实测的脉冲对齐。第七步，把 45 个 series 所有对齐的脉冲取平均，这就是模板，右下图红色的线。拟合只用来找起始时间，模板本身是实测脉冲的平均。最后再用一个上升、两个下降的函数拟合模板，得到解析脉冲。

**English**: Fourth, templates. First, how they are made. Step one: select the events where this detector triggered on this LED's flash, and use all twelve channels. Step two: a very short median filter removes the narrow spike from the LED drive. Step three: a 100 kilohertz low-pass filter. Step four: subtract the baseline and divide by the peak. Step five: fit each pulse with two exponentials, with a free start time. The top right plot shows one pulse and its fit. Step six: shift each measured pulse so that the fitted start is at the same time. Step seven: average all aligned pulses of the 45 series. That is the template, the red line at the bottom right. The fit is only used to find the start time; the template itself is the mean of the measured pulses. Finally we fit the template with one rise and two falls to get the analytic pulse.


---

## Slide 10: Templates: example（约 30 秒）

**中文**：这是 Z2 的例子，十二个通道。蓝色是对齐后的单个脉冲，红色是模板，黑色虚线是解析脉冲。标题是灰色的通道，没有清楚的脉冲，所以不拟合解析脉冲。

**English**: Here is Z2 as an example, twelve channels. Blue are the aligned single pulses, red is the template, and the dashed black line is the analytic pulse. Channels with a grey title have no clear pulse, so we do not fit an analytic pulse there.


---

## Slide 11: Example pulses: Z7 PSum with Z7's LED（约 60 秒）

**中文**：老师想看脉冲形状随时间怎么变。这是 Z7 看自己的 LED，十二个通道加起来，就是 PSum。每个 series 取一个脉冲，一共 45 个，颜色从浅到深是从早到晚。左边是原始的 ADC，可以看到幅度慢慢变小。开头那个很尖的负信号是 LED 的串扰。右边每条除以自己的峰值，只看形状：基本叠在一起，形状没有变。

**English**: Prof. Liu wanted to see how the pulse shape changes with time. This is Z7 with its own LED, all twelve channels summed: the PSum. One pulse per series, 45 in total. Light to dark is early to late. On the left, raw ADC: the amplitude slowly goes down. The sharp negative spike at the start is pickup from the LED drive. On the right, each pulse is divided by its own peak, so we only see the shape. They lie on top of each other: the shape did not change.


---

## Slide 12: Summary（约 40 秒）

**中文**：总结一下。可见度：每个 LED 自己的探测器都看得到，隔壁的也常常看到。幅度：大部分稳定，9 月 18 号 Z20 的 LED 要再查。触发比例：稳定，台阶是阈值改了。模板：每个格子都有，Z7 的脉冲形状一周内没有变。谢谢。

**English**: To sum up. Visibility: each LED is seen by its own detector, and often by the next one. Amplitude: mostly stable; Z20's LEDs on September 18 need a closer look. Trigger fraction: stable; the steps are threshold changes. Templates: one for every cell, and the Z7 pulse shape did not change during the week. Thank you.


---

## 可能被问的问题 / Likely questions（回答一两句就够）

**Q1. 为什么看不到更远的探测器？/ Why no detector further away?**
中文：我们只读出触发的探测器。光如果太弱、没过阈值，就看不到。
English: Only the triggering detector is read out. If the light is below threshold, we cannot see it.

**Q2. Z20 那次是 LED 还是探测器？/ Was the Z20 drop the LED or the detector?**
中文：像是 LED。Z19 看 Z20 的 LED 也变暗了，但 Z19 看自己的 LED 是正常的。原因还不知道。
English: It looks like the LED. Z19 also saw Z20's LED get dimmer, but Z19 with its own LED was normal. We do not know why yet.

**Q3. 触发阈值是谁改的？/ Who changed the trigger thresholds?**
中文：我不知道，我只在数据库里看到它们改了。要问当时值班的人。
English: I do not know. I only see the changes in the ODB. We should ask the people on shift.

**Q4. 模板具体怎么做的？/ How exactly are the templates made?**
中文：每个脉冲：中值滤波、100 千赫低通、减基线、除以峰值，用两个指数拟合找起点，把实测脉冲按起点对齐，最后把所有 series 的脉冲取平均。拟合只用来找起点。
English: For each pulse: median filter, 100 kilohertz low-pass, subtract the baseline, divide by the peak, fit two exponentials to find the start, and shift the measured pulse to that start. Then we average the pulses of all series. The fit is only used to find the start.

**Q5. 有些模板开头有尖峰？/ Some templates have a spike at the start?**
中文：那是自己 LED 的格子，LED 驱动串进了读出。隔壁探测器看同一个 LED 是干净的，可以用那个模板。
English: Those are own-LED cells: the LED drive is picked up by the readout. The neighbouring detector sees the same LED cleanly, so we can use its template.
