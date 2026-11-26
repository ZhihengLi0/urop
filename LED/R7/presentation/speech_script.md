# Speaker Script / 演讲稿 — LED runs in SNOLAB Run 7

约 15 分钟，15 页正片 + backup。每页先中文、后英文，意思一样，**英文可以直接照着念**。全部是短句。斜体是给自己的提示，不用念。

一句话主线：**哪个 LED → 稳不稳（幅度、触发）→ 模板和例子脉冲。**
时间（秒）：1 Title 15 · 2 The data 55 · 3 Which LED made the t 70 · 4 who triggers on whic 70 · 5 who triggers on whic 45 · 6 what we learn 70 · 7 amplitude vs time 65 · 8 whose change is it:  60 · 9 cases to look at aga 75 · 10 trigger fraction vs  80 · 11 one template per cel 75 · 12 own LED: pickup of t 55 · 13 all 43 cells 50 · 14 example pulses: Z7 P 75 · 15 Summary, and what co 65 → 约 925 秒。

---

## Slide 1 — Title（约 15 秒）

**中文**：大家好，我是李志恒。今天讲 Run 7 里 Cf 之后的 LED 数据。按老师给的四部分讲：谁看到哪个 LED，幅度稳不稳，触发稳不稳，最后是脉冲模板。

**English**: Hi everyone, I'm Zhiheng. Today: the LED runs in Run 7, after the Cf calibration. Four parts, as Prof. Liu asked: who sees which LED, is the amplitude stable, is the trigger stable, and the pulse templates.


---

## Slide 2 — The data（约 55 秒）

*提示：指着图：灰色是普通触发，蓝色是 LED 触发，两段中间停 3 秒。*

**中文**：数据是 9 月 15 号到 21 号的 LED series，一共 45 个。每个 run 先等大约 880 秒，然后开灯。**第一段 15 个 LED 一起闪，停 3 秒，第二段换 12 个 LED 再闪。**每个 LED 每秒闪一次，每段正好闪 151 次。还有一点要记住：每次触发只读出触发的那一个探测器。

**English**: The data: 45 LED series, from September 15 to 21. Each run waits about 880 seconds, then the LEDs turn on. **Phase one: 15 LEDs flash together. Three seconds off. Phase two: 12 other LEDs.** Each LED flashes once per second, exactly 151 times per phase. One thing to keep in mind: each trigger reads out only the detector that triggered.


---

## Slide 3 — Which LED made the trigger（约 70 秒）

*提示：一个峰就是一个 LED。*

**中文**：数据里没有记是哪个 LED 闪的，只有触发时间和触发的探测器。但是每个 LED 在一秒里闪的时刻是固定的。**把触发时间对一秒取余，每个 LED 就是一个峰。**看同一次闪光的探测器，触发时间差不超过 0.2 毫秒。脚本告诉我们哪些 LED 开着：峰上有它自己的探测器，就是它；自己不触发的，用排除法。有时候两个 LED 正好同时闪，分不开，这样的组有 22 个，我们不用。

**English**: The data do not record which LED flashed. We only have the trigger time and the detector. But each LED flashes at a fixed time within the second. **Take the trigger time modulo one second, and every LED is one peak.** Detectors that see the same flash trigger within 0.2 milliseconds of each other. The script tells us which LEDs are on. If the LED's own detector is in the peak, the peak is that LED; if not, we use elimination. Sometimes two LEDs flash at the same moment and cannot be separated. That happens in 22 groups; we leave them out.


---

## Slide 4 — Part 1 — who triggers on which LED: phase 1（约 70 秒）

**中文**：这张图回答：**每个 LED 闪的时候，哪个探测器触发。**横轴是第一段开的 15 个 LED，纵轴是探测器。格子里的数是：这个 LED 闪 151 次，这个探测器在多大比例的闪光上触发了，对 45 个 series 取平均。红框是 LED 自己的探测器，大部分是 1.00。**红框外面也有数字：隔壁的探测器也看到了光。**每个有数字的格子有一个编号，比如 P1-07，后面做模板用。

**English**: This plot answers: **when an LED flashes, which detector triggers?** Columns are the 15 LEDs of phase one, rows are detectors. The number is the fraction of the 151 flashes on which that detector triggers, averaged over 45 series. The red box is the LED's own detector; most are 1.00. **There are numbers outside the red boxes too: a neighbour also sees the light.** Every cell with a number has an ID, like P1-07. We use it for the templates later.


---

## Slide 5 — Part 1 — who triggers on which LED: phase 2（约 45 秒）

**中文**：第二段一样，12 个 LED。规律也一样：自己的探测器基本每次都触发，隔壁的探测器也经常触发。两段加起来一共 43 个格子。

**English**: Phase two, the same picture with 12 LEDs. The same pattern: the own detector triggers on almost every flash, and a neighbour often does too. Together the two phases have 43 cells.


---

## Slide 6 — Part 1 — what we learn（约 70 秒）

**中文**：第一部分的结论。第一，**光只照到编号相邻的探测器，再远没有。**43 个格子里 18 个是隔壁的探测器，没有一个隔一个号的。第二，也没有跨组的：所有的对都在 1 到 6、7 到 12、13 到 18、19 到 24 这四组里面。第三，**方向是固定的：0 号和 1 号 LED 照编号小一号的探测器，3、4、5 号 LED 照大一号的。**在一组的两头没有邻居，所以那些 LED 只有自己看得到。只有两个例外，写在下面。最后，我们只读出触发的探测器，低于阈值的光看不到，所以这些数是下限。

**English**: What we learn from part one. First, **light reaches only the detector with the adjacent number, nothing further.** 18 of the 43 cells are a neighbour, and none skips a number. Second, no pair crosses a group: all pairs are inside detectors 1 to 6, 7 to 12, 13 to 18, or 19 to 24. Third, **the direction is fixed: LED 0 and 1 light the detector with the number below, LED 3, 4 and 5 the one above.** At the end of a group there is no neighbour, so those LEDs are seen only by their own detector. There are two exceptions, listed below. Finally, only the triggering detector is read out, so light below threshold is invisible. These numbers are lower limits.


---

## Slide 7 — Part 2 — amplitude vs time（约 65 秒）

*提示：白色 = 1；红 = 偏高；蓝 = 偏低；灰 = 没有数据。*

**中文**：第二部分，幅度随时间。每一行是一个格子，每一列是一个 series，按时间排。颜色是这个 series 的幅度除以这一行的中位数。**白色就是正常。**大部分是白的：72.5% 的点在 5% 以内，90.8% 在 10% 以内。所以大部分是稳定的。另外，多数格子在慢慢往下走，中位数是每天 -0.9%。有几处颜色很明显，后面单独看。

**English**: Part two, amplitude over time. Each row is one cell, each column one series, in time order. The colour is that series' amplitude divided by the row's median. **White means normal.** Most of it is white: 72.5 percent of the points are within 5 percent, 90.8 percent within 10 percent. So it is mostly stable. Most cells also go down slowly; the median is -0.9 percent per day. A few spots stand out. We look at them in a moment.


---

## Slide 8 — Part 2 — whose change is it: the LED or the detector?（约 60 秒）

*提示：左图两条线一起动；中间两条线各走各的。*

**中文**：幅度在变，是 LED 在变，还是探测器在变？可以这样查。左边：同一个 LED，两个探测器在看，两条线一起动。中间：同一个探测器，看自己的两个不同的 LED，两条线不一起动。右边是所有的对：蓝色是同一个 LED，相关系数大多在 0.9 以上；橙色是同一个探测器的两个 LED，大多接近零。**所以变化主要来自 LED 的光，不是探测器。**

**English**: The amplitude changes. Is it the LED, or the detector? We can check. Left: one LED, seen by two detectors. The two lines move together. Middle: one detector, with its two different LEDs. The lines do not move together. Right: all the pairs. Blue is one LED on two detectors: the correlation is mostly above 0.9. Orange is one detector with its two LEDs: mostly near zero. **So the changes come mainly from the LED light, not from the detectors.**


---

## Slide 9 — Part 2 — cases to look at again（约 75 秒）

*提示：先讲 Z20，再快速过其他几个。*

**中文**：这几个要再看。**最明显的是 9 月 18 号凌晨，连续 3 个 series：Z20 的幅度只有正常的 0.25–0.26。**Z19 看 Z20 的 LED，也只有 0.56；但 Z19 看自己的 LED 是正常的。所以是 Z20 的 LED 变暗了。下一个 run 完全没有 LED 闪光，下午一点恢复正常。数据库里 LED 的设置没有变。另外，第一天有几个格子偏高大约两成，之后慢慢降下来。

**English**: These need a second look. **The clearest is the early morning of September 18, 3 series in a row: Z20 is at only 0.25–0.26 of normal.** Z19, looking at Z20's LED, is at 0.56; but Z19 with its own LED is normal. So Z20's LEDs were dim. The next run had no LED flashes at all, and by 1 pm it was back to normal. The LED settings in the ODB did not change. Also, on the first day a few cells are about 20 percent high, and then come down.


---

## Slide 10 — Part 3 — trigger fraction vs time（约 80 秒）

*提示：黑线 = 触发阈值改了。黄 = 每次都触发。*

**中文**：第三部分，触发比例随时间。还是一行一个格子，一列一个 series。黄色是每次闪光都触发。**自己的 LED 那些行一直是黄的，很稳定。**其他行有台阶：一下子从 0 变到 1，或者反过来。我去查了数据库：**台阶正好对应触发阈值被改的时间，就是图上的黑线。**这一周一共有 6 段不同的阈值设置。比如 Z9 和 Z10：只在第 2、4 段触发，正好是它们阈值调低的时候。所以这些台阶是设置变了，不是探测器不稳定。

**English**: Part three, trigger fraction over time. Again one row per cell, one column per series. Yellow means it triggers on every flash. **The own-LED rows stay yellow: stable.** Other rows show steps: from zero to one, or back. I checked the ODB: **the steps are exactly where the trigger thresholds were changed, the black lines.** There are 6 different threshold settings during the week. For example Z9 and Z10 trigger only in periods 2 and 4, which is when their thresholds were low. So the steps are settings, not unstable detectors.


---

## Slide 11 — Part 4 — one template per cell, made like the Z7 template（约 75 秒）

*提示：方法和 Z7 模板一样，只多一步去尖峰。*

**中文**：第四部分，模板。每个格子做一个模板，45 个 series 合在一起。方法和 Z7 的模板一样：每个脉冲先低通，减基线，除以峰值，用两个指数拟合，起始时间是自由的。**按拟合出来的起始时间对齐，再平均。**只多了一步：LED 通电的时候读出上有很窄的尖峰，先用一个很短的中值滤波去掉。最后对模板拟合一个解析函数：一个上升，两个下降。这是一个干净的例子，Z2 看自己的 LED：残差基本是平的。

**English**: Part four, templates. One template per cell, all 45 series together. The method is the same as for the Z7 template. Each pulse is low-passed, baseline-subtracted, divided by its peak, and fitted with two exponentials with a free start time. **Pulses are aligned on the fitted start, then averaged.** One extra step: when an LED is driven, the readout picks up a very narrow spike. A short median filter removes it first. At the end we fit an analytic function to the template: one rise, two falls. This is a clean example, Z2 with its own LED: the residual is nearly flat.


---

## Slide 12 — Part 4 — own LED: pickup of the LED drive pulse（约 55 秒）

*提示：只在自己 LED 的格子里有；隔壁探测器没有。*

**中文**：但是有些自己 LED 的格子，脉冲开头有问题。比如 Z7：有几个通道在脉冲开始的地方有一个很快的跳变，然后才是声子脉冲。**这是 LED 的驱动脉冲串进了自己探测器的读出。**隔壁的探测器看同一个 LED，就没有。一共 11 个格子有，都是自己的 LED。这些格子模板的开头不能直接用：可以用隔壁探测器的模板，或者把开头去掉再拟合。

**English**: But some own-LED cells have a problem at the start of the pulse. Take Z7: several channels show a fast step at the start, before the phonon pulse. **This is the LED drive pulse, picked up by the detector's own readout.** A neighbour looking at the same LED does not show it. 11 cells have it, all own-LED. For these, the start of the template cannot be used as it is. We can use the neighbour's template, or cut the start before fitting.


---

## Slide 13 — Part 4 — all 43 cells（约 50 秒）

**中文**：这是全部 43 个格子，每个格子一个小图：红色是探测器的模板，黑色虚线是解析函数。每个格子十二个通道的图在备用页，拟合出来的时间常数也在备用页和 CSV 文件里。

**English**: All 43 cells, one small panel each: the detector template in red, the analytic pulse in black dashes. The twelve-channel plot of every cell is in the backup, and so are the fitted time constants.


---

## Slide 14 — Part 4 — example pulses: Z7 PSum with Z7's LED（约 75 秒）

*提示：左：原始 ADC；中：放大；右：归一化以后只看形状。*

**中文**：老师想看脉冲形状随时间怎么变。这是 Z7 看自己的 LED，十二个通道加起来，就是 PSum。**每个 series 挑一个典型的脉冲，一共 45 条，颜色从浅到深是从早到晚。**左边是原始的 ADC，整条 52 毫秒。中间放大。开头那个负的尖峰就是刚才说的 LED 串扰。中间能看到幅度从浅色到深色在变小，就是第二部分说的 Z7 这个 LED 慢慢变暗。右边去掉尖峰，每条除以自己的峰值，只看形状：这一周的脉冲基本叠在一起，形状没有变。

**English**: Prof. Liu wanted to see how the pulse shape changes with time. This is Z7 with its own LED, all twelve channels summed: the PSum. **One typical pulse per series, 45 in total. Light to dark is early to late.** Left: raw ADC, the whole 52 milliseconds. Middle: zoom. The negative spike at the start is the LED pickup from before. In the middle you can see the amplitude going down from light to dark: that is the slow decline of this LED from part two. Right: spike removed, each pulse divided by its own peak, so only the shape is left. The pulses of the week lie nearly on top of each other: the shape did not change.


---

## Slide 15 — Summary, and what comes next（约 65 秒）

**中文**：总结。一，每个 LED 触发都能对应到一个 LED；光只照到相邻的探测器，方向是固定的。二，幅度大部分在 10% 以内，变化主要来自 LED 本身；9 月 18 号凌晨 Z20 的 LED 变暗，要查原因。三，触发比例的台阶是阈值设置变了。四，43 个格子都有模板和解析函数，方法和 Z7 一样；有几个探测器自己的 LED 有串扰，要注意。下一步：查 Z20 那几个小时发生了什么，处理串扰的格子，再和老师确认这些模板要怎么用。

**English**: To sum up. One: every LED trigger is traced to one LED. Light reaches only the adjacent detector, in a fixed direction. Two: amplitudes are mostly within 10 percent, and the changes come mainly from the LEDs. Z20's LEDs were dim on the morning of September 18; we need to find out why. Three: the steps in the trigger fraction are threshold settings. Four: all 43 cells have a template and an analytic pulse, made like the Z7 template. A few detectors pick up their own LED drive; watch out for those. Next: find out what happened to Z20 in those hours, handle the pickup cells, and agree on how these templates will be used.


---

## 可能被问的问题 / Likely questions（回答一两句就够）

**Q1. 为什么看不到更远的探测器？/ Why no detector further away?**
中文：我们只读出触发的探测器。光如果到了，但低于阈值，就看不到。所以图是下限。
English: Only the triggering detector is read out. If light arrives but stays below threshold, we cannot see it. So the plot is a lower limit.

**Q2. 两个 LED 同时闪怎么办？/ What if two LEDs flash at the same time?**
中文：LED 是一个接一个打开的，所以有时两个 LED 的闪光时刻差不到 0.2 毫秒。这时只靠时间分不开，我们就不用这一组。一共 22 组。
English: The LEDs are switched on one after the other, so sometimes two of them flash within 0.2 milliseconds. Time alone cannot separate them, so we do not use that group. There are 22 such groups.

**Q3. 中值滤波会不会改变脉冲形状？/ Does the median filter change the pulse shape?**
中文：基本不会。它只去掉比 18 微秒窄的尖峰。声子脉冲的上升比这慢，峰值和上升时间都不变。
English: Hardly. It removes only spikes narrower than 18 microseconds. The phonon rise is slower than that, so the peak and the rise time stay the same.

**Q4. Z20 那次是 LED 还是探测器？/ Was the Z20 drop the LED or the detector?**
中文：像是 LED。Z19 看 Z20 的 LED 也变暗了，但 Z19 看自己的 LED 是正常的。原因还不知道，要查那几个小时的记录。
English: It looks like the LED. Z19 also saw less of Z20's light, while Z19 with its own LED was normal. We do not know the cause yet; we need the logs of those hours.

**Q5. 触发阈值是谁改的？/ Who changed the trigger thresholds?**
中文：我不知道。我只看到每个 run 开始时数据库里的阈值，这一周有 6 种设置。要问当时值班的人。
English: I do not know. I only see the thresholds in the ODB at the start of each run; there are 6 settings during the week. We should ask the people on shift.

**Q6. 0918 脚本有什么不同？/ What changed with the 0918 script?**
中文：LED 的设置完全一样。它会关掉 Z17 的一级触发。但数据库里 Z17 的触发一直是开的，Z17 也一直在触发。
English: The LED settings are identical. It should switch off Z17's L1 trigger. But the ODB shows Z17's trigger on in every run, and Z17 keeps triggering.

**Q7. 幅度怎么算的？/ How is the amplitude defined?**
中文：先去掉尖峰，减基线，取最大值，单位 ADC。每个 series 取中位数，再除以所有 series 的中位数。
English: Remove the spikes, subtract the baseline, take the maximum, in ADC. Then the median per series, divided by the median over all series.

**Q8. 为什么说每组 6 个？/ Why groups of six?**
中文：这是从数据看出来的：没有一对跨过 6 和 7、12 和 13、18 和 19。数据库里读出板的数目也是这样分的。
English: That is what the data show: no pair crosses 6 and 7, 12 and 13, or 18 and 19. The number of readout boards in the ODB splits the same way.
