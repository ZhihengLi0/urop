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
        # a (plain, bold) pair puts the second half of the subtitle in bold
        para = tb.text_frame.add_paragraph()
        if isinstance(sub, tuple):
            run(para, sub[0], 14, GRAY)
            run(para, sub[1], 14, DARK, bold=True)
        else:
            run(para, sub, 14, GRAY)
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


def caption(s, text, l, t, w, size=11):
    """Small grey note, e.g. the sources of a formula."""
    tb = textbox(s, l, t, w, Inches(0.9))
    run(tb.text_frame.paragraphs[0], text, size, GRAY, italic=True)


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
tb = textbox(s, Inches(0.9), Inches(4.7), Inches(11.5), Inches(1.2))
run(tb.text_frame.paragraphs[0], "李知恒  ·  明尼苏达大学  ·  SuperCDMS SNOLAB Run 4  ·  2026 年 9 月", 16)
run(tb.text_frame.add_paragraph(), "github.com/ZhihengLi0/urop  →  snolab/collection_efficiency/", 13, GRAY)

# ------------------------------------------------------------------ 2 问题
s = new("主要思路")
pic(s, "chain.png", L, Inches(1.4), W, Inches(2.6))
lines(s, [
    "!对于在 0 V 下工作的探测器（没有 NTL 效应）：",
    "收集效率  =  TES 吸收的能量（所有通道求和）  ÷  事件放进晶体的 10.37 keV",
    "样本：Z7，Ge 活化的 K 线事件，来自 SNOLAB R4（2207 个事件，30 个 series，11 个通道）。",
], L, Inches(4.3), W, Inches(2.7))

# ------------------------------------------------------------------ 3 公式
s = new("公式和它需要的两个数", "采用 CDMS 收集效率文档里的 Method 1")
pic(s, "formula.png", L, T, W, Inches(3.55))
lines(s, [
    "δP = 电流变化 δI 之后焦耳热的变化量：一个线性项，加一个很小的二次项。",
    "I₀：工作点上流过 TES 的电流 · R₀：工作点上 TES 的电阻 · R_L = R_p + R_sh：负载电阻（R_p 寄生电阻，R_sh 分流电阻）· δI：电流的变化，来自波形",
    "文档里还有一个 Method 2：换成我们的符号是 δP = I₀(R_L − R₀)·δI − R_L·(δI)² —— 线性项相同，只有二次项不同，能量低 1.7%（PBS1，15 个事件的中位数）。",
], L, Inches(4.95), W, Inches(1.4), size=13)
caption(s, "来源：Antoine Rehberg 的 CDMS wiki 页面 Collection Efficiency Analysis   —   confluence.slac.stanford.edu/spaces/CDMS/pages/542577254", L, Inches(6.35), W, size=11)

# ------------------------------------------------------------------ 4 主图
s = new("例子：一个脉冲", ("Z7 PBS1，事件 30646：  ", "同一条波形，读成 ADC 计数、读成电流、读成功率"))
pic(s, "peak_full.png", L, T, W, Inches(5.3))
lines(s, [
    "!双指数拟合用的是 100 kHz 低通之后的波形（蓝线），不是原始采样点；原始采样点只是画出来对照。",
], L, Inches(6.62), W, Inches(0.5), size=14)

# ------------------------------------------------------------------ 5 峰高
s = new("脉冲高度：从拟合取，不从最大的采样点取")
pic(s, "peak_top.png", L, T, W, Inches(5.9))

# ------------------------------------------------------------------ 6 功率和面积
s = new("功率脉冲，它的面积就是能量")
pic(s, "power_panel.png", L, T, Inches(7.5), Inches(5.75))
pic(s, "power_legend_zh.png", Inches(8.15), Inches(2.1), Inches(4.7), Inches(4.1))

# ------------------------------------------------------------------ 7 积拟合不积 raw
s = new("为什么对拟合积分，不是对原始数据")
pic(s, "raw_cum_slide.png", L, T, W, Inches(5.1))
lines(s, [
    "上：这两个事件的原始电流；右上角小图把脉冲之后的基线放大。下：由原始电流累计的能量（灰）和由拟合累计的能量（红）。",
    "!右：脉冲过后电流比基线低 6 nA —— 埋在 28 nA 的噪声里看不出来，但 24 ms 积下来就是 −420 eV：原始 −169 eV，拟合 277 eV。",
], L, Inches(6.33), W, Inches(0.9), size=13)

# ------------------------------------------------------------------ 8 其他通道
s = new("同一个事件的其他通道：加起来是 33%", "Z7 事件 30646；11 个通道里的 4 个")
pic(s, "allchan_slide.png", L, T, Inches(8.5), Inches(4.75))
pic(s, "chan_table_zh.png", Inches(9.25), Inches(1.15), Inches(3.6), Inches(5.6))
lines(s, [
    "各通道分到的能量很不均匀：60% 落在第 1 面；PES1 一个通道就有 489 eV，而 PES2 只有 195 eV。",
    "!11 个通道加起来：3419 eV = 10.37 keV 的 33.0%。   PDS2（右下）有一个缓慢的大起伏。",
], L, Inches(6.1), Inches(8.6), Inches(1.1), size=14)

# ------------------------------------------------------------------ 9 所有事件
s = new("现在看所有事件：一个通道给出又宽又歪的分布", "PBS1，1917 个 K 线事件，每个事件一次拟合、一次积分")
pic(s, "hist_PBS1.png", L, T, Inches(8.8), Inches(5.9))
lines(s, [
    "红色：来自拟合。灰色：官方窗口在原始波形上算的。峰位只差 0.2%。",
    "!峰 285 eV，宽度 15% —— 这可是一条能量固定的谱线。",
    "往右拖的尾巴，是发生在这个通道附近的事件。",
    "!单通道的宽度是事件位置，不是噪声。",
], Inches(9.35), Inches(1.6), Inches(3.6), Inches(5.0), size=15)

# ------------------------------------------------------------------ 10 求和
s = new("各通道求和：32 ± 1%", "每个 K 线事件被 TES 吸收的总能量")
pic(s, "hist_sum.png", L, T, Inches(8.8), Inches(5.9))
lines(s, [
    "!10 个通道求和，1827 个事件：3162 eV = 30.5%，宽度降到 7.5% —— 位置效应抵消了。",
    "PDS2 只有 42% 的事件能拟合上（那个缓慢起伏），而且这些事件不典型；它的份额只能给一个范围。",
    "!完整效率 31.5–32.9%：  32 ± 1%。",
    "红线：10.37 keV —— 三分之二的能量根本没到 TES。",
], Inches(9.35), Inches(1.6), Inches(3.6), Inches(5.0), size=15)

# ------------------------------------------------------------------ 11 总结
s = new("总结，以及还没落实的")
lines(s, [
    "电流脉冲通过 TES 方程变成功率脉冲；功率下面的面积就是能量。",
    "能量用拟合脉冲来算，所以不受峰值噪声和基线漂移的影响。",
    "!Z7 把一个 10.37 keV 事件的 32 ± 1% 吸收进 TES。   CDMS 文档在 R37 CUTE tower 上得到的是 26–41%。",
    "还没落实：只做了 Z7 · Z7 的偏压没有确认（按 0 V 算） · 没有 dI/dV · PDS2 就是那 ±1% · 12.5% 的事件在任何通道都拟合不上。",
], L, Inches(1.6), W, Inches(4.6), size=19)

# ================================================================== backup
s = new("Backup — 事件谱")
pic(s, "spectrum_zip7.png", L, T, W, Inches(5.75))

s = new("Backup — 文档里的两个 Method")
lines(s, [
    "δP = I₀(R_L − R₀)·δI + c₂·R_L·(δI)²     c₂ = 2 是 Method 1（本报告用的），c₂ = −1 是 Method 2",
    "两者只有二次项不同：能量差 1.7%（PBS1，15 个事件的中位数）—— 远小于单通道 15% 的宽度和 PDS2 的范围。",
    "完整方程里的电感项需要 L 和 loop gain，要从 dI/dV 来，MSI 上这些 series 没有这个数据；这一项被忽略。",
    "官方 Eabs（触发在第 16383 点，基线是 93..15758 点的平均，5 阶 20 kHz 预滤波，窗口 −0.5/+1 ms，同一个公式）复现到 0.2%；直方图页上的灰色轮廓就是它。",
], L, Inches(1.45), W, Inches(5.5), size=17)

s = new("Backup — 公式推导和逻辑")
pic(s, "derivation_backup_zh.png", L, T, W, Inches(5.85))

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
