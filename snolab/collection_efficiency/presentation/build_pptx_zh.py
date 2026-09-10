#!/usr/bin/env python3
"""Chinese version of build_pptx.py, slide for slide, for reading and understanding.
Same figures, same numbers; only the slide text is translated.

One line of logic per slide, the figure does the talking: the deck is built
around one figure, a single pulse read as ADC, as current and as power, and then
follows that pulse to the whole detector.

    python3 build_pptx.py            # writes SNOLAB_R4_collection_efficiency_20260910.pptx
    module load libreoffice && libreoffice --headless --convert-to pdf <the pptx>

Every number is copied from ../results/plots/current_power_overlay/*.txt or
../NOTES.md; nothing is computed here.
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "SNOLAB_R4_collection_efficiency_20260910_zh.pptx")

NAVY = RGBColor(0x1F, 0x38, 0x64)
DARK = RGBColor(0x33, 0x33, 0x33)
GRAY = RGBColor(0x66, 0x66, 0x66)
RED = RGBColor(0xC0, 0x39, 0x2B)
SW, SH = Inches(13.333), Inches(7.5)
FONT = "Droid Sans Fallback"      # a CJK font LibreOffice on MSI can render

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]
n_slide = 0
L, T, W = Inches(0.55), Inches(1.25), Inches(12.3)


def textbox(s, l, t, w, h):
    tb = s.shapes.add_textbox(l, t, w, h)
    tb.text_frame.word_wrap = True
    return tb


def run(p, text, size, color=DARK, bold=False, italic=False):
    r = p.add_run(); r.text = text
    r.font.size, r.font.color.rgb, r.font.name = Pt(size), color, FONT
    r.font.bold, r.font.italic = bold, italic
    return r


def title(s, text, sub=None):
    tb = textbox(s, L, Inches(0.25), W, Inches(0.8))
    run(tb.text_frame.paragraphs[0], text, 27, NAVY, bold=True)
    if sub:
        run(tb.text_frame.add_paragraph(), sub, 14, GRAY)
    ln = s.shapes.add_shape(1, L, Inches(1.06), W, Emu(18000))
    ln.fill.solid(); ln.fill.fore_color.rgb = NAVY; ln.line.fill.background()


def lines(s, items, l, t, w, h, size=18):
    """A few short lines. A line starting with '!' is the red take-away."""
    tb = textbox(s, l, t, w, h)
    tf = tb.text_frame
    for i, txt in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        red = txt.startswith("!")
        run(p, txt.lstrip("!"), size, RED if red else DARK, bold=red)


def pic(s, name, l, t, max_w, max_h):
    path = os.path.join(FIG, name)
    w0, h0 = Image.open(path).size
    scale = min(max_w / w0, max_h / h0)
    w, h = int(w0 * scale), int(h0 * scale)
    s.shapes.add_picture(path, l + int((max_w - w) / 2), t + int((max_h - h) / 2),
                         width=w, height=h)


def new(ttl, sub=None, notes=""):
    global n_slide
    n_slide += 1
    s = prs.slides.add_slide(BLANK)
    if ttl:
        title(s, ttl, sub)
    tb = textbox(s, Inches(12.5), Inches(7.05), Inches(0.6), Inches(0.35))
    run(tb.text_frame.paragraphs[0], str(n_slide), 10, GRAY)
    s.notes_slide.notes_text_frame.text = notes
    return s



# ------------------------------------------------------------------ 1 题目
s = new(None)
tb = textbox(s, Inches(0.9), Inches(2.3), Inches(11.5), Inches(1.8))
run(tb.text_frame.paragraphs[0], "Z7 的声子收集效率", 40, NAVY, bold=True)
run(tb.text_frame.add_paragraph(), "一个 10.37 keV 的 K 线事件，有多少能量最后到了 TES 里 —— 先从一个脉冲读出来，再推到整个探测器", 18, GRAY)
tb = textbox(s, Inches(0.9), Inches(4.7), Inches(11.5), Inches(1.2))
run(tb.text_frame.paragraphs[0], "李知恒  ·  明尼苏达大学  ·  SuperCDMS SNOLAB Run 4  ·  2026 年 9 月", 16)
run(tb.text_frame.add_paragraph(), "github.com/ZhihengLi0/urop  →  snolab/collection_efficiency/", 13, GRAY)

# ------------------------------------------------------------------ 2 问题
s = new("问题是什么")
pic(s, "chain.png", L, Inches(1.4), W, Inches(2.6))
lines(s, [
    "收集效率  =  到达 TES 薄膜的能量  ÷  事件放进晶体的 10.37 keV",
    "我们记录下来的是一条电流脉冲。",
    "!电流曲线下面的面积是电荷，不是能量 —— 所以必须先把脉冲换成功率。",
    "样本：Z7，Ge 活化的 K 线事件（2207 个事件，30 个 series，11 个通道的原始波形全部保存）。",
], L, Inches(4.3), W, Inches(2.7))

# ------------------------------------------------------------------ 3 公式
s = new("电流 → 功率，功率 → 能量")
pic(s, "formula.png", L, T, W, Inches(4.3))
lines(s, [
    "功率 = 电流变化 δI 之后焦耳热的变化量：一个线性项，加一个很小的二次项。",
    "两个系数都是这个通道实测的偏置点 —— 没有任何拟合和调参。",
    "!如果脉冲是双指数形状，能量就是 A、τ_f、τ_r 的一个公式 —— 不需要积分窗口。",
], L, Inches(5.65), W, Inches(1.5), size=16)

# ------------------------------------------------------------------ 4 主图
s = new("一个脉冲，三种读法", "Z7 PBS1，事件 30646：同一条波形，读成 ADC 计数、读成电流、读成功率")
pic(s, "peak_full.png", L, T, W, Inches(5.75))

# ------------------------------------------------------------------ 5 峰高
s = new("脉冲高度：从拟合取，不从最大的采样点取")
pic(s, "peak_top.png", L, T, W, Inches(4.55))
lines(s, [
    "黄色竖带：98 个采样点都在峰高的 10% 以内。其中最大的那个，就是噪声往上跳得最多的那个。",
    "!原始数据最大值 885 ADC，拟合峰值 717 ADC：取最大值偏高 23%。滤波能减轻，拟合能消除。",
], L, Inches(5.9), W, Inches(1.2), size=16)

# ------------------------------------------------------------------ 6 功率和面积
s = new("功率脉冲，它的面积就是能量")
pic(s, "peak_bottom.png", L, T, W, Inches(3.4))
lines(s, [
    "红线：拟合出的电流代进公式。蓝色虚线：只有线性项。紫色点线：只有二次项，放大 20 倍。",
    "!二次项只占峰值的 1.9% —— 功率脉冲的形状和电流脉冲一样。",
    "!粉色面积就是这个通道吸收的能量：305 eV。",
], L, Inches(4.8), W, Inches(2.2), size=16)

# ------------------------------------------------------------------ 7 积拟合不积 raw
s = new("为什么积分的是拟合脉冲，不是原始数据", "从 52 ms 波形的开头一路累计的能量；触发在点线处")
pic(s, "cum_ev30646.png", L, T, Inches(6.05), Inches(2.4))
pic(s, "cum_ev210571.png", Inches(6.8), T, Inches(6.05), Inches(2.4))
pic(s, "cum_legend.png", Inches(3.3), Inches(3.7), Inches(6.7), Inches(0.4))
lines(s, [
    "红线，来自拟合：脉冲之前是 0，1 ms 之内升上去，之后保持水平 —— 终点正好等于公式算出的值。",
    "!灰线，来自原始波形：一直在漂。基线偏 1 nA，15 ms 积下来就是 42 eV。右图：拟合 277 eV，原始波形 −169 eV。",
], L, Inches(4.4), W, Inches(2.4), size=16)

# ------------------------------------------------------------------ 8 其他通道
s = new("同一个事件的其他通道：加起来是 33%", "Z7 事件 30646；11 个通道里的 4 个")
pic(s, "allchan_PBS1.png", L, T, Inches(6.05), Inches(2.1))
pic(s, "allchan_PES1.png", Inches(6.8), T, Inches(6.05), Inches(2.1))
pic(s, "allchan_PES2.png", L, Inches(3.45), Inches(6.05), Inches(2.1))
pic(s, "allchan_PDS2.png", Inches(6.8), Inches(3.45), Inches(6.05), Inches(2.1))
lines(s, [
    "各通道分到的能量很不均匀（PES1 489 eV，PES2 195 eV）：事件发生的位置更靠近一侧。",
    "!11 个通道加起来：3419 eV = 10.37 keV 的 33.0%。   PDS2（右下）有一个缓慢的大起伏 —— 记住它。",
], L, Inches(5.75), W, Inches(1.3), size=15)

# ------------------------------------------------------------------ 9 所有事件
s = new("现在看所有事件：一个通道给出又宽又歪的分布", "PBS1，1917 个 K 线事件，每个事件一次拟合、一次积分")
pic(s, "hist_PBS1.png", L, T, Inches(8.6), Inches(5.75))
lines(s, [
    "红色：来自拟合。灰色：官方窗口在原始波形上算的。峰位只差 0.2%。",
    "!峰 285 eV，宽度 15% —— 这可是一条能量固定的谱线。",
    "往右拖的尾巴，是发生在这个通道附近的事件。",
    "!单通道的宽度是事件位置，不是噪声。",
], Inches(9.35), Inches(1.6), Inches(3.6), Inches(5.0), size=15)

# ------------------------------------------------------------------ 10 求和
s = new("各通道求和：32 ± 1%", "每个 K 线事件被 TES 吸收的总能量")
pic(s, "hist_sum.png", L, T, Inches(8.6), Inches(5.75))
lines(s, [
    "!10 个通道求和，1827 个事件：3162 eV = 30.5%，宽度降到 7.5% —— 位置效应抵消了。",
    "PDS2 只有 42% 的事件能拟合上（那个缓慢起伏），而且这些事件不典型；它的份额只能给一个范围。",
    "!完整效率 31.5–32.9%：  32 ± 1%。",
    "红线：10.37 keV —— 三分之二的能量根本没到 TES。",
], Inches(9.35), Inches(1.6), Inches(3.6), Inches(5.0), size=15)

# ------------------------------------------------------------------ 11 总结
s = new("总结，以及还没落实的")
lines(s, [
    "电流脉冲通过 TES 方程变成功率脉冲；功率下面的面积就是能量。二次项只有 2%。",
    "能量来自拟合脉冲：没有最大值的噪声偏差，没有漂移，不需要积分窗口。",
    "单通道：15% 宽、歪的（位置效应）。10 个通道求和：7.5%、对称。",
    "!Z7 把一个 10.37 keV 事件的 32 ± 1% 吸收进 TES。CDMS 文档在 R37 CUTE tower 上报的是 26–41%。",
    "还没落实：只做了 Z7 · Z7 的 HV 偏压没有确认（按 0 V 算） · 没有 dI/dV，电感项被丢掉 · PDS2 就是那 ±1% · 12.5% 的事件在任何通道都拟合不上，没进直方图。",
], L, Inches(1.45), W, Inches(5.5), size=17)

# ================================================================== backup
s = new("Backup — 事件谱")
pic(s, "spectrum_zip7.png", L, T, W, Inches(5.75))

s = new("Backup — 功率公式的三个版本")
lines(s, [
    "P = I₀(R_L − R₀)·δI + c₂·R_L·(δI)²     c₂ = 2（method 1，本报告用的）、1（精确的小信号解）、−1（method 2）",
    "相对精确解：method 1 高 0.58%，method 2 低 1.15% —— 远小于单通道 15% 的宽度和 PDS2 的范围。",
    "完整方程里的电感项需要 L 和 loop gain，要从 dI/dV 来，MSI 上这些 series 没有这个数据；这一项被忽略。",
    "官方 Eabs（触发在第 16383 点，基线是 93..15758 点的平均，5 阶 20 kHz 预滤波，窗口 −0.5/+1 ms，同一个公式）复现到 0.2%；直方图页上的灰色轮廓就是它。",
], L, Inches(1.45), W, Inches(5.5), size=17)

for ttl, name in [
    ("Backup — 15 个事件，拟合电流和功率（PBS1）", "pulse_15events.png"),
    ("Backup — 15 个事件，累计能量（PBS1）", "cum_15events.png"),
    ("Backup — 事件 30646，全部通道", "allchan_pulses.png"),
    ("Backup — 每个通道的能量分布", "hist_allchan.png"),
]:
    s = new(ttl)
    pic(s, name, L, T, W, Inches(5.75))

prs.save(OUT)
print(f"saved {OUT}: {n_slide} slides")
