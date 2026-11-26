#!/usr/bin/env python3
"""Build the R7 LED talk (16:9, speaker notes on every slide) and its speaker script.

    (container) python3 make_figures.py  ->  python3 build_pptx.py  ->  bash -lc ./make_pdf.sh
    python3 build_pptx.py --zh   ->  ..._zh.pptx: the same deck with Chinese text (for reading; no speaker script)

Content follows Prof. Liu's outline (Slack): background and timeline; visibility (phase 1, phase 2);
amplitude vs time (mostly stable, some cases to look at again); trigger fraction vs time; template generation
with the processing steps listed (as coded in ../lp_template_led.py and the
chain it imports) and the 45 Z7 PSum pulses on Z7's LED. One figure and at most three short lines per slide; details are in the
backup. Every number is read from stats.json or the CSV files of ../out; nothing is typed in.
speech_script.md (Chinese + English per slide, short sentences) is written from the same text as the notes.
"""
import csv
import json
import os
import sys

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ZH = "--zh" in sys.argv


def Z(en, zh):
    return zh if ZH else en


HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUTD = os.path.join(os.path.dirname(HERE), "out")
PPTX = os.path.join(HERE, "SNOLAB_R7_LED_runs_20261125%s.pptx" % ("_zh" if ZH else ""))
SPEECH = os.path.join(HERE, "speech_script.md")

NAVY, DARK, GRAY = RGBColor(0x1F, 0x38, 0x64), RGBColor(0x33, 0x33, 0x33), RGBColor(0x66, 0x66, 0x66)
SW, SH = Inches(13.333), Inches(7.5)
L, T, W = Inches(0.55), Inches(1.25), Inches(12.3)
MONTH = {"09": "Sep"}

st = json.load(open(os.path.join(HERE, "stats.json")))
cells = list(csv.DictReader(open(os.path.join(OUTD, "summary", "cells.csv"))))
tmpl = list(csv.DictReader(open(os.path.join(OUTD, "lpfit", "LED_cell_templates.csv"))))
thr_rows = list(csv.DictReader(open(os.path.join(OUTD, "summary", "trigger_settings.csv"))))
EX = "P1-07"          # Z7 PSum in Z7's LED (Prof. Liu's example)
CLEAN = "P1-02"       # a clean own-LED cell for the template slide
cell = {c["id"]: c for c in cells}

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]
n_slide = 0
speech = []          # (slide number, title, seconds, zh, en)


# ───────────────────────────────────────────────────────────────── helpers (as didv/presentation)
def textbox(s, l, t, w, h):
    tb = s.shapes.add_textbox(l, t, w, h)
    tb.text_frame.word_wrap = True
    return tb


def run(p, text, size, color=DARK, bold=False, italic=False):
    r = p.add_run()
    r.text = text
    r.font.size, r.font.color.rgb, r.font.name = Pt(size), color, "Arial"
    r.font.bold, r.font.italic = bold, italic
    if ZH:
        rpr = r._r.get_or_add_rPr()
        rpr.append(rpr.makeelement(qn("a:ea"), {"typeface": "Microsoft YaHei"}))
    return r


def title(s, text, sub=None):
    tb = textbox(s, L, Inches(0.25), W, Inches(0.8))
    run(tb.text_frame.paragraphs[0], text, 26, NAVY, bold=True)
    if sub:
        run(tb.text_frame.add_paragraph(), sub, 14, GRAY)
    ln = s.shapes.add_shape(1, L, Inches(1.06), W, Emu(18000))
    ln.fill.solid(); ln.fill.fore_color.rgb = NAVY; ln.line.fill.background()


def lines(s, items, l, t, w, h, size=17):
    tb = textbox(s, l, t, w, h)
    tf = tb.text_frame
    for i, txt in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(10)
        run(p, txt, size)


def pic(s, name, l, t, max_w, max_h):
    path = os.path.join(FIG, name)
    w0, h0 = Image.open(path).size
    scale = min(max_w / w0, max_h / h0)
    w, h = int(w0 * scale), int(h0 * scale)
    s.shapes.add_picture(path, l + int((max_w - w) / 2), t + int((max_h - h) / 2), width=w, height=h)


def caption(s, text, l, t, w, size=11):
    tb = textbox(s, l, t, w, Inches(0.6))
    run(tb.text_frame.paragraphs[0], text, size, GRAY, italic=True)


def new(ttl, sub=None, fig=None, sec=0, zh="", en=""):
    """One slide; zh / en are the spoken text (the speaker notes carry the text of the deck's language)."""
    global n_slide
    if fig and not os.path.exists(os.path.join(FIG, fig)):
        print("skipped '%s': %s missing" % (ttl, fig)); return None
    n_slide += 1
    s = prs.slides.add_slide(BLANK)
    if ttl:
        title(s, ttl, sub)
    tb = textbox(s, Inches(12.5), Inches(7.05), Inches(0.6), Inches(0.35))
    run(tb.text_frame.paragraphs[0], str(n_slide), 10, GRAY)
    s.notes_slide.notes_text_frame.text = (zh if ZH else en) or (ttl or "")
    speech.append((n_slide, ttl or "Title", sec, zh, en))
    return s


def table(s, rows, l, t, w, h, col_w=None, size=10):
    shape = s.shapes.add_table(len(rows), len(rows[0]), l, t, w, h)
    tbl = shape.table
    for j, cw in enumerate(col_w or []):
        tbl.columns[j].width = cw
    for i, row in enumerate(rows):
        for j, c_ in enumerate(row):
            c = tbl.cell(i, j)
            c.text = ""
            run(c.text_frame.paragraphs[0], str(c_), size, NAVY if i == 0 else DARK, bold=(i == 0))
            c.margin_left = c.margin_right = Inches(0.04)
            c.margin_top = c.margin_bottom = Inches(0.02)
    return tbl


def ledname(l):
    o, n = l.split("#")
    return "%s LED%s" % (o, n)


def when(series):
    """24260918_020910 -> '18 Sep 02:09'"""
    return "%d %s %s:%s" % (int(series[6:8]), MONTH.get(series[4:6], series[4:6]), series[9:11], series[11:13])


def day(series):
    return int(series[6:8])


def znum(z):
    return int(z[1:])


# ───────────────────────────────────────────────────────────────── numbers used on the slides
n_ok = st["n_series"]
cp = st["campaign"]
hours = int(round(cp["cycle_min"] / 60.0))
run_tm = json.load(open(os.path.join(OUTD, "24260915_063921", "timing.json")))
n_flash = run_tm["n_flashes"]["phase1"]
pause = int(round(run_tm["pause_s"]))
n_led1 = sum(r["phase"] == "phase1" for r in st["led_table"])
n_led2 = sum(r["phase"] == "phase2" for r in st["led_table"])
amp10 = int(round(st["amp_within_10pct"]))
z20 = st["z20_low"]
z20_from, z20_to = when(z20[0][0]), when(z20[-1][0])[-5:]
pk_det = sorted({p["det"] for p in st["pickup_cells"]}, key=znum)
epochs = st["epochs"]
thr = {(r["series"], r["det"], r["dcrc"]): r["activation_threshold"] for r in thr_rows}


def ep_cells(cid):
    return [(p or {}).get("mean") for p in st["trig_epoch"].get(cid, [])]


step_cells = [c for c in cells if [x for x in ep_cells(c["id"]) if x is not None]
              and max(x for x in ep_cells(c["id"]) if x is not None) - min(x for x in ep_cells(c["id"]) if x is not None) > 0.3]
own = [c for c in cells if c["own_led"] == "True"]
det_rows = [r for r in tmpl if r["channel"] == "detector" and r.get("model")]
no_det = [c["id"] for c in cells if c["id"] not in {r["id"] for r in det_rows}]
FIG_W, TXT_L, TXT_W = Inches(8.6), Inches(9.35), Inches(3.7)      # figure left, text right


# ───────────────────────────────────────────────────────────────── 1 title
s = new(None, sec=15,
        zh="大家好，我是李志恒。今天讲 Run 7 的 LED 数据。按老师说的四点讲：谁看到哪个 LED，幅度稳不稳，触发稳不稳，还有脉冲模板。",
        en="Hi everyone, I'm Zhiheng. Today I'll show the LED data from Run 7. Four points: who sees which LED, "
           "amplitude stability, trigger stability, and pulse templates.")
tb = textbox(s, Inches(0.9), Inches(2.2), Inches(11.5), Inches(2.0))
run(tb.text_frame.paragraphs[0], Z("LED runs in SNOLAB Run 7", "SNOLAB Run 7 的 LED 数据"), 36, NAVY, bold=True)
run(tb.text_frame.add_paragraph(), Z("visibility, stability and pulse templates", "可见度、稳定性和脉冲模板"), 20, GRAY)
tb = textbox(s, Inches(0.9), Inches(4.8), Inches(11.5), Inches(1.2))
run(tb.text_frame.paragraphs[0], Z("Zhiheng Li, University of Minnesota", "李志恒，明尼苏达大学"), 16)
run(tb.text_frame.add_paragraph(), Z("November 2026", "2026 年 11 月"), 14, GRAY)

# ───────────────────────────────────────────────────────────────── 2 background
s = new(Z("Background", "背景"),
        Z("%d LED runs from %d to %d Sep" % (cp["n_all"], day(cp["first_all"]), day(cp["last_all"])),
          "9 月 %d 日到 %d 日，%d 个 LED run" % (day(cp["first_all"]), day(cp["last_all"]), cp["n_all"])),
        fig="fig_week_timeline.png", sec=45,
        zh="先说背景。这是 Run 7 在 Cf 刻度之后的数据。DAQ 脚本一直循环：先取低本底数据，再取一个 LED run，大概每 %d 个小时一次。"
           "上面每一条竖线是一个 LED run。从 9 月 %d 号到 %d 号一共 %d 个，我们用了 %d 个。"
           % (hours, day(cp["first_all"]), day(cp["last_all"]), cp["n_all"], n_ok),
        en="First, the background. This is Run 7 data after the Cf calibration. The DAQ script runs in a loop: "
           "low-background data, then one LED run, about every %d hours. Each line on the top is one LED run. "
           "From September %d to %d there are %d of them, and we use %d."
           % (hours, day(cp["first_all"]), day(cp["last_all"]), cp["n_all"], n_ok))
pic(s, "fig_week_timeline.png", L, T, W, Inches(4.3))
lines(s, [Z("Run 7, after the Cf calibration.", "Run 7，Cf 刻度之后。"),
          Z("The script repeats: low-background run, then LED run, about every %d hours." % hours,
            "脚本循环：先低本底 run，再 LED run，大约每 %d 小时一次。" % hours),
          Z("%d LED runs, %d used." % (cp["n_all"], n_ok), "%d 个 LED run，用了 %d 个。" % (cp["n_all"], n_ok))],
      L, Inches(5.7), W, Inches(1.6))

# ───────────────────────────────────────────────────────────────── 3 one run
s = new(Z("One LED run", "一次 LED run"), Z("two phases of LED flashes", "两段 LED 闪光"), fig="fig_run_timeline.png", sec=40,
        zh="一个 LED run 里面是这样的。第一段 %d 个 LED 在闪，停 %d 秒，第二段换 %d 个 LED。每个 LED 每秒闪一次，一共 %d 次。"
           "每次触发只读出触发的那个探测器。" % (n_led1, pause, n_led2, n_flash),
        en="Inside one LED run: in phase one, %d LEDs flash. Then %d seconds off. In phase two, %d LEDs flash. "
           "Each LED flashes once per second, %d times. Each trigger reads out only the detector that triggered."
           % (n_led1, pause, n_led2, n_flash))
pic(s, "fig_run_timeline.png", L, T, W, Inches(4.3))
lines(s, [Z("Phase 1: %d LEDs.  %d s off.  Phase 2: %d LEDs." % (n_led1, pause, n_led2),
            "第一段 %d 个 LED，停 %d 秒，第二段 %d 个 LED。" % (n_led1, pause, n_led2)),
          Z("Each LED flashes once per second, %d times." % n_flash, "每个 LED 每秒闪一次，共 %d 次。" % n_flash),
          Z("Only the detector that triggers is read out.", "每次只读出触发的那个探测器。")],
      L, Inches(5.7), W, Inches(1.6))

# ───────────────────────────────────────────────────────────────── 4-5 visibility
for ph, sec in (("phase1", 55), ("phase2", 35)):
    k = ph[-1]
    if ph == "phase1":
        zh = ("这是第一段的可见度图。横轴是 LED，纵轴是探测器。格子里的数是：这个 LED 闪的时候，这个探测器触发的比例。"
              "红框是 LED 自己的探测器，基本都是 1。红框旁边的格子，是隔壁的探测器也看到了光。")
        en = ("This is the visibility plot for phase one. Columns are LEDs, rows are detectors. The number is how often "
              "the detector triggers when that LED flashes. The red box is the LED's own detector, and it is almost "
              "always one. A number next to a red box means the neighbouring detector also sees the light.")
        txt = [Z("Columns: LEDs.  Rows: detectors.", "横轴：LED。纵轴：探测器。"),
               Z("Number: how often the detector triggers when the LED flashes.", "数字：LED 闪的时候，这个探测器触发的比例。"),
               Z("Red box: the LED's own detector.", "红框：LED 自己的探测器。")]
    else:
        zh = "第二段也一样。自己的探测器基本每次都触发，隔壁的探测器也经常触发。光只到相邻的探测器，再远就没有了。"
        en = ("Phase two shows the same pattern. The own detector triggers almost every time, and often the next "
              "detector too. The light only reaches the next detector, never further.")
        txt = [Z("Same pattern as phase 1.", "和第一段一样。"),
               Z("The light reaches only the next detector, never further.", "光只到相邻的探测器，再远就没有。")]
    s = new(Z("Visibility: phase %s" % k, "可见度：第%s段" % ("一" if k == "1" else "二")),
            Z("who triggers on which LED, mean of %d series" % n_ok, "谁在哪个 LED 上触发，%d 个 series 的平均" % n_ok),
            fig="visibility_%s.png" % ph, sec=sec, zh=zh, en=en)
    pic(s, "visibility_%s.png" % ph, L, T, FIG_W, Inches(6.1))
    lines(s, txt, TXT_L, Inches(1.6), TXT_W, Inches(5.0))

# ───────────────────────────────────────────────────────────────── 6 amplitude
s = new(Z("Stability: amplitude vs time", "稳定性：幅度随时间"), fig="fig_amp_map.png", sec=50,
        zh="第二点，幅度随时间。每一行是一个格子，每一列是一个 series，按时间排。白色就是正常。"
           "大部分是白的，%d%% 的点变化在 10%% 以内。所以大部分是稳定的，但有几个地方要再看。" % amp10,
        en="Second, amplitude versus time. Each row is one cell, each column is one series, in time order. White means "
           "normal. Most of it is white: %d percent of the points are within 10 percent. So it is mostly stable, but a "
           "few spots need a second look." % amp10)
pic(s, "fig_amp_map.png", L, T, FIG_W, Inches(6.1))
lines(s, [Z("One row per cell, one column per series.", "一行一个格子，一列一个 series。"),
          Z("White means normal.", "白色就是正常。"),
          Z("Mostly stable: %d %% within 10 %%." % amp10, "大部分稳定：%d %% 在 10 %% 以内。" % amp10)],
      TXT_L, Inches(1.6), TXT_W, Inches(5.0))

# ───────────────────────────────────────────────────────────────── 7 cases
s = new(Z("Amplitude: cases to look at again", "幅度：需要再看的情况"), fig="fig_stab_cases.png", sec=50,
        zh="这几个要再看。最明显的是 9 月 18 号凌晨，Z20 的 LED 一下子暗了很多，过了几个小时又恢复了。"
           "Z19 看 Z20 的 LED 也变暗，所以是 LED 的问题，不是探测器。还有第一天几个格子偏高一点。",
        en="These need a second look. The clearest one: early on September 18, Z20's LEDs became much dimmer, and a few "
           "hours later they were back to normal. Z19 also saw Z20's LED get dimmer, so it is the LED, not the "
           "detector. Also, on the first day a few cells are a bit high.")
pic(s, "fig_stab_cases.png", L, T, W, Inches(4.55))
lines(s, [Z("%s to %s: Z20's LEDs were much dimmer." % (z20_from, z20_to), "%s 到 %s：Z20 的 LED 暗了很多。" % (z20_from, z20_to)),
          Z("Z19 saw it too, so it is the LED, not the detector.", "Z19 也看到了，所以是 LED，不是探测器。"),
          Z("First day: a few cells are a bit high.", "第一天：几个格子偏高一点。")],
      L, Inches(5.85), W, Inches(1.5), size=16)

# ───────────────────────────────────────────────────────────────── 8 trigger fraction
s = new(Z("Stability: trigger fraction vs time", "稳定性：触发比例随时间"), fig="fig_trig_map.png", sec=55,
        zh="第三点，触发比例随时间。黄色是每次闪光都触发。自己 LED 的格子一直是黄的，很稳定。"
           "其他格子有台阶。我查了数据库，台阶正好在触发阈值被改的地方，就是图上的黑线。所以这是设置变了，不是探测器不稳定。",
        en="Third, trigger fraction versus time. Yellow means it triggers on every flash. The own-LED cells stay yellow: "
           "stable. Other cells have steps. I checked the ODB: the steps are exactly where the trigger thresholds were "
           "changed, the black lines. So these are setting changes, not unstable detectors.")
pic(s, "fig_trig_map.png", L, T, FIG_W, Inches(6.1))
lines(s, [Z("Yellow: triggers on every flash.", "黄色：每次闪光都触发。"),
          Z("Own LED: stable.", "自己的 LED：稳定。"),
          Z("The steps are where the trigger thresholds were changed (black lines).", "台阶出现在触发阈值改动的地方（黑线）。")],
      TXT_L, Inches(1.6), TXT_W, Inches(5.0))

# ───────────────────────────────────────────────────────────────── 9 template method
# Steps as coded in ../lp_template_led.py (median filter MEDFILT, selection START_TOL), the imported
# lp_fit_align.py (100 kHz 4th-order Butterworth, baseline median, / peak, 2-exp fit with free start, shift of the
# measured trace), ../lp_template_combine.py (mean over all series) and ../fit_led.py (analytic pulse).
n_pulses = st["n_pulses_fit_ok"]
mill = "%.1f" % (n_pulses / 1e6)
s = new(Z("Template generation: method", "模板：处理流程"),
        Z("one template per cell and channel, all %d series together" % n_ok, "每个格子、每个通道一个模板，%d 个 series 合在一起" % n_ok),
        fig="fig_template_method.png", sec=65,
        zh="第四点，模板。先说怎么做的。第一步，选事件：这个 LED 闪的时候，这个探测器触发的事件，十二个通道都用。"
           "第二步，用一个很短的中值滤波，去掉 LED 通电带来的窄尖峰。第三步，100 千赫的低通滤波。"
           "第四步，减掉基线，再除以峰值。第五步，每个脉冲用两个指数拟合，起始时间是自由的。右上图就是一个脉冲和它的拟合。"
           "第六步，按拟合出来的起始时间，把实测的脉冲对齐。第七步，把 %d 个 series 所有对齐的脉冲取平均，这就是模板，右下图红色的线。"
           "拟合只用来找起始时间，模板本身是实测脉冲的平均。最后再用一个上升、两个下降的函数拟合模板，得到解析脉冲。" % n_ok,
        en="Fourth, templates. First, how they are made. Step one: select the events where this detector triggered on "
           "this LED's flash, and use all twelve channels. Step two: a very short median filter removes the narrow spike "
           "from the LED drive. Step three: a 100 kilohertz low-pass filter. Step four: subtract the baseline and divide "
           "by the peak. Step five: fit each pulse with two exponentials, with a free start time. The top right plot shows "
           "one pulse and its fit. Step six: shift each measured pulse so that the fitted start is at the same time. "
           "Step seven: average all aligned pulses of the %d series. That is the template, the red line at the bottom "
           "right. The fit is only used to find the start time; the template itself is the mean of the measured pulses. "
           "Finally we fit the template with one rise and two falls to get the analytic pulse." % n_ok)
pic(s, "fig_template_method.png", Inches(7.75), T, Inches(5.1), Inches(5.65))
lines(s, [Z("1. Events: the detector triggered on this LED's flash. All 12 channels.",
            "1. 事件：这个 LED 闪时该探测器触发的事件，12 个通道都用。"),
          Z("2. Median filter, 11 samples (18 µs): removes the narrow LED pickup spike.",
            "2. 中值滤波，11 个采样点（18 µs）：去掉 LED 串扰的窄尖峰。"),
          Z("3. Low-pass filter: 100 kHz, 4th-order Butterworth.", "3. 低通滤波：100 kHz，4 阶 Butterworth。"),
          Z("4. Subtract the baseline (median before the pulse), divide by the peak.",
            "4. 减基线（脉冲之前的中位数），再除以峰值。"),
          Z("5. Fit each pulse with two exponentials (rise and fall), start time free.",
            "5. 每个脉冲用两个指数拟合（上升和下降），起始时间自由。"),
          Z("6. Keep pulses with a valid fit; shift each measured pulse so that its fitted start is at the same time.",
            "6. 保留拟合合理的脉冲；把实测脉冲平移，使拟合出的起点对齐。"),
          Z("7. Template = mean of the aligned pulses of all %d series (%s million pulses in total)." % (n_ok, mill),
            "7. 模板 = %d 个 series 所有对齐后脉冲的平均（共 %s 百万个脉冲）。" % (n_ok, mill)),
          Z("Analytic pulse: fit of the template with one rise time and two fall times:",
            "解析脉冲：用一个上升时间、两个下降时间的函数拟合模板：")],
      L, Inches(1.45), Inches(7.0), Inches(4.6), size=15)
pic(s, "fig_formula_analytic.png", L, Inches(5.55), Inches(6.2), Inches(0.6))

# ───────────────────────────────────────────────────────────────── 10 template example
cc = cell[CLEAN]
s = new(Z("Templates: example", "模板：例子"),
        Z("%s with its own LED, 12 channels" % cc["det"], "%s 看自己的 LED，12 个通道" % cc["det"]),
        fig="cell_%s.png" % CLEAN, sec=30,
        zh="这是 %s 的例子，十二个通道。蓝色是对齐后的单个脉冲，红色是模板，黑色虚线是解析脉冲。"
           "标题是灰色的通道，没有清楚的脉冲，所以不拟合解析脉冲。" % cc["det"],
        en="Here is %s as an example, twelve channels. Blue are the aligned single pulses, red is the template, and the "
           "dashed black line is the analytic pulse. Channels with a grey title have no clear pulse, so we do not fit an "
           "analytic pulse there." % cc["det"])
pic(s, "cell_%s.png" % CLEAN, L, T, FIG_W, Inches(6.1))
lines(s, [Z("Blue: aligned single pulses.", "蓝色：对齐后的单个脉冲。"),
          Z("Red: template.", "红色：模板。"),
          Z("Black dashed: analytic pulse.", "黑色虚线：解析脉冲。"),
          Z("Grey title: no clear pulse in that channel, no analytic pulse.", "灰色标题：这个通道没有清楚的脉冲，不拟合解析脉冲。")],
      TXT_L, Inches(1.6), TXT_W, Inches(5.0))

# ───────────────────────────────────────────────────────────────── 11 example pulses
s = new(Z("Example pulses: Z7 PSum with Z7's LED", "例子脉冲：Z7 PSum，Z7 自己的 LED"),
        Z("%d pulses, one per series" % n_ok, "%d 个脉冲，每个 series 一个" % n_ok),
        fig="example_pulses_%s.png" % EX, sec=60,
        zh="老师想看脉冲形状随时间怎么变。这是 Z7 看自己的 LED，十二个通道加起来，就是 PSum。每个 series 取一个脉冲，一共 %d 个，"
           "颜色从浅到深是从早到晚。左边是原始的 ADC，可以看到幅度慢慢变小。开头那个很尖的负信号是 LED 的串扰。"
           "右边每条除以自己的峰值，只看形状：基本叠在一起，形状没有变。" % n_ok,
        en="Prof. Liu wanted to see how the pulse shape changes with time. This is Z7 with its own LED, all twelve "
           "channels summed: the PSum. One pulse per series, %d in total. Light to dark is early to late. On the left, "
           "raw ADC: the amplitude slowly goes down. The sharp negative spike at the start is pickup from the LED drive. "
           "On the right, each pulse is divided by its own peak, so we only see the shape. They lie on top of each "
           "other: the shape did not change." % n_ok)
pic(s, "example_pulses_%s.png" % EX, L, T, W, Inches(4.4))
lines(s, [Z("Light to dark: early to late.", "颜色由浅到深：时间由早到晚。"),
          Z("The amplitude goes down slowly.", "幅度慢慢变小。"),
          Z("Divided by its own peak, the shape stays the same.", "除以各自的峰值后，形状不变。")],
      L, Inches(5.8), W, Inches(1.5))

# ───────────────────────────────────────────────────────────────── 12 summary
s = new(Z("Summary", "总结"), sec=40,
        zh="总结一下。可见度：每个 LED 自己的探测器都看得到，隔壁的也常常看到。幅度：大部分稳定，9 月 18 号 Z20 的 LED 要再查。"
           "触发比例：稳定，台阶是阈值改了。模板：每个格子都有，Z7 的脉冲形状一周内没有变。谢谢。",
        en="To sum up. Visibility: each LED is seen by its own detector, and often by the next one. Amplitude: mostly "
           "stable; Z20's LEDs on September 18 need a closer look. Trigger fraction: stable; the steps are threshold "
           "changes. Templates: one for every cell, and the Z7 pulse shape did not change during the week. Thank you.")
lines(s, [Z("Visibility: each LED is seen by its own detector, and often by the next one.",
            "可见度：每个 LED 自己的探测器看得到，隔壁的也常常看到。"),
          Z("Amplitude: mostly stable. To look at again: Z20's LEDs on %s." % z20_from[:6],
            "幅度：大部分稳定。要再看：Z20 的 LED（%s）。" % z20_from[:6]),
          Z("Trigger fraction: stable. The steps are threshold changes.", "触发比例：稳定。台阶是阈值改了。"),
          Z("Templates: one per cell. The Z7 pulse shape is the same all week.", "模板：每个格子一个。Z7 的脉冲形状一周内不变。")],
      L, Inches(1.6), W, Inches(5.0), size=20)
n_main = n_slide

# ───────────────────────────────────────────────────────────────── backup (figures for questions; not presented)
s = new(Z("Backup: is it the LED or the detector?", "备用：是 LED 还是探测器？"), fig="fig_same_led.png")
if s:
    pic(s, "fig_same_led.png", L, T, W, Inches(4.8))
    lines(s, [Z("Same LED on two detectors: they move together. One detector with two LEDs: they do not.",
                "同一个 LED、两个探测器：一起变。同一个探测器、两个 LED：不一起变。"),
              Z("So the changes come from the LED light.", "所以变化来自 LED 的光。")], L, Inches(6.2), W, Inches(1.1), size=15)

s = new(Z("Backup: trigger thresholds", "备用：触发阈值"),
        Z("L1 activation threshold (DCRC0) in the ODB, per period", "ODB 里的 L1 触发阈值（DCRC0），按时间段"))
hdr = ["%d: %s to %s" % (e["epoch"], when(e["first"]), when(e["last"])) for e in epochs]
dets_thr = sorted({c["det"] for c in step_cells}, key=znum)
rows = [[Z("detector", "探测器")] + hdr] + [[z] + [str(thr.get((e["first"], z, "DCRC0"), "")) for e in epochs] for z in dets_thr]
table(s, rows, L, T, W, Inches(0.3) * len(rows), col_w=[Inches(1.2)] + [Inches(1.85)] * len(epochs), size=10)
caption(s, Z("Detectors whose trigger fraction changes between periods. All detectors: out/summary/trigger_settings.csv.",
             "只列出触发比例随时间段变化的探测器。全部探测器：out/summary/trigger_settings.csv。"), L, Inches(6.75), W)

s = new(Z("Backup: LED pickup in own-LED cells", "备用：自己 LED 格子里的串扰"),
        Z("example: Z7 with its own LED", "例子：Z7 看自己的 LED"), fig="cell_%s.png" % EX)
if s:
    pic(s, "cell_%s.png" % EX, L, T, FIG_W, Inches(6.1))
    lines(s, [Z("A fast spike at the pulse start: the LED drive, picked up by the detector's own readout.",
                "脉冲开头的快尖峰：LED 驱动串进了自己探测器的读出。"),
              Z("Seen in own-LED cells of %s." % ", ".join(pk_det), "出现在 %s 的自己 LED 格子里。" % "、".join(pk_det)),
              Z("The neighbouring detectors are clean.", "隔壁的探测器是干净的。")],
          TXT_L, Inches(1.6), TXT_W, Inches(5.0), size=15)

s = new(Z("Backup: templates of all %d cells" % len(cells), "备用：全部 %d 个格子的模板" % len(cells)),
        Z("red: detector template, black dashed: analytic pulse", "红色：探测器模板，黑色虚线：解析函数"), fig="cells_overview.png")
if s:
    pic(s, "cells_overview.png", L, T, W, Inches(5.75))
    if no_det:
        caption(s, Z("No detector template (too few pulses): %s." % ", ".join(no_det),
                     "没有探测器模板（脉冲太少）：%s。" % "、".join(no_det)), L, Inches(7.0), Inches(11.8), size=10)

s = new(Z("Backup: analytic pulse of the detector templates", "备用：探测器模板的解析函数"),
        Z("own-LED cells; all cells: out/lpfit/LED_cell_templates.csv", "自己 LED 的格子；全部格子：out/lpfit/LED_cell_templates.csv"))
rows = [[Z("cell", "格子"), Z("detector, LED", "探测器，LED"), "τ_rise [µs]", "τ_fall1 [µs]", "τ_fall2 [µs]", Z("model", "模型")]]
own_ids = {c["id"] for c in own}
for r in det_rows:
    if r["id"] in own_ids and r.get("tau_rise_us"):
        f2 = r.get("tau_fall2_us", "")
        f2 = "" if not f2 else ("> 20 000" if float(f2) > 20000 else "%.0f" % float(f2))
        rows.append([r["id"], "%s, %s" % (r["det"], ledname(r["led"])), "%.0f" % float(r["tau_rise_us"]),
                     "%.0f" % float(r["tau_fall1_us"]), f2, r["model"]])
half = (len(rows) + 1) // 2
cw = [Inches(0.65), Inches(1.75), Inches(0.9), Inches(0.95), Inches(1.0), Inches(0.65)]
table(s, rows[:half], L, T, Inches(5.9), Inches(0.3) * half, col_w=cw, size=10)
if len(rows) > half:
    table(s, [rows[0]] + rows[half:], Inches(6.85), T, Inches(5.9), Inches(0.3) * (len(rows) - half + 1), col_w=cw, size=10)
caption(s, Z("τ_fall2 > 20 000 µs: longer than the fit window, not constrained.", "τ_fall2 > 20 000 µs：比拟合窗口还长，定不出来。"),
        L, Inches(6.75), W)

s = new(Z("Backup: how a trigger is matched to an LED", "备用：怎么知道触发来自哪个 LED"), fig="fig_flash_groups.png")
if s:
    pic(s, "fig_flash_groups.png", L, T, W, Inches(4.3))
    lines(s, [Z("Each LED flashes at a fixed time within the second, so each LED is one peak.",
                "每个 LED 在一秒里闪的时刻固定，所以每个 LED 是一个峰。"),
              Z("Two LEDs within 0.2 ms cannot be separated; those series are left out (grey in the maps).",
                "两个 LED 相差不到 0.2 ms 时分不开，这些 series 不用（图上是灰色）。")], L, Inches(5.75), W, Inches(1.5), size=15)

for name, en_t, zh_t in (("shape_vs_time_%s.png" % EX, "Backup: Z7 rise and fall time per series", "备用：Z7 每个 series 的上升和下降时间"),
                         ("amplitude_vs_time.png", "Backup: amplitude vs time, every channel", "备用：幅度随时间，每个通道"),
                         ("trigger_fraction.png", "Backup: trigger fraction vs time, every cell", "备用：触发比例随时间，每个格子")):
    s = new(Z(en_t, zh_t), fig=name)
    if s:
        pic(s, name, L, T, W, Inches(6.1))

for c in cells:
    s = new(Z("Backup %s: %s with %s" % (c["id"], c["det"], ledname(c["led"])),
              "备用 %s：%s 看 %s" % (c["id"], c["det"], ledname(c["led"]))), fig="cell_%s.png" % c["id"])
    if s:
        pic(s, "cell_%s.png" % c["id"], L, T, W, Inches(6.1))

prs.save(PPTX)
print("wrote %s: %d slides (%d main)" % (PPTX, n_slide, n_main))
if ZH:              # the Chinese deck is for reading; the speaker script comes from the English build
    sys.exit(0)

# ───────────────────────────────────────────────────────────────── speaker script
main = [x for x in speech if x[2] > 0]
total = sum(x[2] for x in main)
out = ["# Speaker Script / 演讲稿: LED runs in SNOLAB Run 7", "",
       "约 %d 分钟，%d 页正片，后面是备用页（只在被问到时用）。每页先中文、后英文，意思一样，英文可以直接照着念。"
       % (round(total / 60.0), len(main)), "",
       "时间（秒）：" + "，".join("%d %s %d" % (n, t_, sec) for n, t_, sec, _, _ in main) + "；合计约 %d 秒。" % total,
       "", "---", ""]
for n, t_, sec, zh, en in main:
    out += ["## Slide %d: %s（约 %d 秒）" % (n, t_, sec), "",
            "**中文**：" + zh, "", "**English**: " + en, "", "", "---", ""]
out += ["## 可能被问的问题 / Likely questions（回答一两句就够）", "",
        "**Q1. 为什么看不到更远的探测器？/ Why no detector further away?**",
        "中文：我们只读出触发的探测器。光如果太弱、没过阈值，就看不到。",
        "English: Only the triggering detector is read out. If the light is below threshold, we cannot see it.", "",
        "**Q2. Z20 那次是 LED 还是探测器？/ Was the Z20 drop the LED or the detector?**",
        "中文：像是 LED。Z19 看 Z20 的 LED 也变暗了，但 Z19 看自己的 LED 是正常的。原因还不知道。",
        "English: It looks like the LED. Z19 also saw Z20's LED get dimmer, but Z19 with its own LED was normal. We do not know why yet.", "",
        "**Q3. 触发阈值是谁改的？/ Who changed the trigger thresholds?**",
        "中文：我不知道，我只在数据库里看到它们改了。要问当时值班的人。",
        "English: I do not know. I only see the changes in the ODB. We should ask the people on shift.", "",
        "**Q4. 模板具体怎么做的？/ How exactly are the templates made?**",
        "中文：每个脉冲：中值滤波、100 千赫低通、减基线、除以峰值，用两个指数拟合找起点，把实测脉冲按起点对齐，最后把所有 series 的脉冲取平均。拟合只用来找起点。",
        "English: For each pulse: median filter, 100 kilohertz low-pass, subtract the baseline, divide by the peak, fit two exponentials to find the start, and shift the measured pulse to that start. Then we average the pulses of all series. The fit is only used to find the start.", "",
        "**Q5. 有些模板开头有尖峰？/ Some templates have a spike at the start?**",
        "中文：那是自己 LED 的格子，LED 驱动串进了读出。隔壁探测器看同一个 LED 是干净的，可以用那个模板。",
        "English: Those are own-LED cells: the LED drive is picked up by the readout. The neighbouring detector sees the same LED cleanly, so we can use its template.", ""]
open(SPEECH, "w", encoding="utf-8").write("\n".join(out))
print("wrote %s (%d s = %.1f min, %d main slides)" % (SPEECH, total, total / 60.0, len(main)))
