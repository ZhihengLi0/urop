#!/usr/bin/env python3
"""Build the R7 LED talk (16:9, English slides, speaker notes on every slide) and its speaker script.

    (container) python3 make_figures.py  ->  python3 build_pptx.py  ->  bash -lc ./make_pdf.sh
    python3 build_pptx.py --zh   ->  ..._zh.pptx: the same deck with Chinese text (for reading; no speaker script)

Outline from Prof. Liu (Slack): visibility (phase 1; phase 2); stability: amplitude vs time (mostly stable, some
cases to look at again); stability: trigger fraction vs time; template generation, with example pulses (Z7 PSum
in Z7's LED) to see the pulse shape over time. About 15 minutes. outline.md lists the content and the checked
facts. Every number on a slide is read from stats.json or the CSV files of ../out; nothing is typed in.
speech_script.md (Chinese + English per slide, short sentences) is written from the same text as the notes.
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ZH = "--zh" in sys.argv   # Chinese slides for reading: same numbers, figures keep their English labels


def Z(en, zh):
    return zh if ZH else en


HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUTD = os.path.join(os.path.dirname(HERE), "out")
PPTX = os.path.join(HERE, "SNOLAB_R7_LED_runs_20261125%s.pptx" % ("_zh" if ZH else ""))
SPEECH = os.path.join(HERE, "speech_script.md")

NAVY, DARK, GRAY, RED = (RGBColor(0x1F, 0x38, 0x64), RGBColor(0x33, 0x33, 0x33),
                         RGBColor(0x66, 0x66, 0x66), RGBColor(0xC0, 0x39, 0x2B))
SW, SH = Inches(13.333), Inches(7.5)
L, T, W = Inches(0.55), Inches(1.25), Inches(12.3)
MONTH = {"09": "Sep"}

st = json.load(open(os.path.join(HERE, "stats.json")))
cells = list(csv.DictReader(open(os.path.join(OUTD, "summary", "cells.csv"))))
tmpl = list(csv.DictReader(open(os.path.join(OUTD, "lpfit", "LED_cell_templates.csv"))))
thr_rows = list(csv.DictReader(open(os.path.join(OUTD, "summary", "trigger_settings.csv"))))
EX = "P1-07"          # Z7 PSum in Z7's LED (Prof. Liu's example)
CLEAN = "P1-02"       # a clean own-LED cell for the method slide
cell = {c["id"]: c for c in cells}

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]
n_slide = 0
speech = []          # (slide number, title, seconds, hint, zh, en)


# ───────────────────────────────────────────────────────────────── helpers
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


def lines(s, items, l, t, w, h, size=15):
    tb = textbox(s, l, t, w, h)
    tf = tb.text_frame
    for i, txt in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(6)
        red = txt.startswith("!")
        run(p, txt.lstrip("!"), size, RED if red else DARK, bold=red)


def pic(s, name, l, t, max_w, max_h):
    path = os.path.join(FIG, name)
    w0, h0 = Image.open(path).size
    scale = min(max_w / w0, max_h / h0)
    w, h = int(w0 * scale), int(h0 * scale)
    s.shapes.add_picture(path, l + int((max_w - w) / 2), t + int((max_h - h) / 2), width=w, height=h)


def caption(s, text, l, t, w, size=11):
    tb = textbox(s, l, t, w, Inches(0.6))
    run(tb.text_frame.paragraphs[0], text, size, GRAY, italic=True)


def new(ttl, sub=None, fig=None, sec=0, hint="", zh="", en=""):
    """One slide; zh / en are the spoken text (en also goes into the speaker notes)."""
    global n_slide
    if fig and not os.path.exists(os.path.join(FIG, fig)):
        print("skipped '%s': %s missing" % (ttl, fig)); return None
    n_slide += 1
    s = prs.slides.add_slide(BLANK)
    if ttl:
        title(s, ttl, sub)
    tb = textbox(s, Inches(12.5), Inches(7.05), Inches(0.6), Inches(0.35))
    run(tb.text_frame.paragraphs[0], str(n_slide), 10, GRAY)
    s.notes_slide.notes_text_frame.text = (zh if ZH else en).replace("**", "") or (ttl or "")
    speech.append((n_slide, ttl or "Title", sec, hint, zh, en))
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


def pct(x):
    return "%d %%" % round(100 * float(x))


def when(series):
    """24260918_020910 -> '18 Sep 02:09'"""
    return "%d %s %s:%s" % (int(series[6:8]), MONTH.get(series[4:6], series[4:6]), series[9:11], series[11:13])


def znum(z):
    return int(z[1:])


# ───────────────────────────────────────────────────────────────── numbers used on the slides
n_ok = st["n_series"]
n1, n2 = st["n_cells_phase"]["phase1"], st["n_cells_phase"]["phase2"]
own = [c for c in cells if c["own_led"] == "True"]
neigh = [c for c in cells if c["own_led"] == "False"]
n_groups, n_amb, n_ret = st["n_groups"], len(st["ambiguous"]), len(st["retrigger"])
off_lo, off_hi = st["offset_us_range"]
leds = st["led_table"]
n_leds = len(leds)
own_full = [r for r in leds if r["own"] >= 0.995]
own_part = sorted([r for r in leds if 0.05 <= r["own"] < 0.995], key=lambda r: r["own"])
own_never = [r for r in leds if r["own"] < 0.05]
dets_seen = {c["det"] for c in cells}

# direction: LED 0 / 1 -> the detector with the number below, LED 3 / 4 / 5 -> the one above
rule_ok, rule_end, rule_exc = [], [], []
for r in leds:
    k = znum(r["led"].split("#")[0])
    side, other = ("prev", "next") if r["number"] in (0, 1) else ("next", "prev")
    nb, ob = (k - 1, k + 1) if side == "prev" else (k + 1, k - 1)
    at_end = r["first_in_tower"] if side == "prev" else r["last_in_tower"]
    if r[side] >= 0.05:
        rule_ok.append(r)
    elif at_end or nb == 12:
        rule_end.append(r)
    else:
        rule_exc.append(Z("%s is not seen by Z%d%s", "%s 没有被 Z%d 看到%s") % (ledname(r["led"]), nb, "" if "Z%d" % nb in dets_seen
                                                    else Z(" (Z%d triggers on no LED at all)", "（Z%d 在任何 LED 上都不触发）") % nb))
    if r[other] >= 0.05:
        rule_exc.append(Z("%s is seen by Z%d (%s)", "%s 被 Z%d 看到（%s）") % (ledname(r["led"]), ob, pct(r[other])))

# amplitude
amp5, amp10 = st["amp_within_5pct"], st["amp_within_10pct"]
slope = st["slope_pct_per_day"]
sl_led = sorted(st["same_led_corr"], key=lambda p: -p["r"])
sl_det = st["same_det_corr"]
sl_hi = [p for p in sl_led if p["r"] >= 0.9]
sl_lo = [p for p in sl_led if p["r"] < 0.9]
z20a, z20b, z19 = st["z20_low"], st["z20_led3_low"], st["z19_low"]
camp = st["cell_amp"]
first_high = sorted([(v["first_day"], k) for k, v in camp.items() if v.get("first_day") and v["first_day"] >= 1.15], reverse=True)


def rng(vals):
    lo, hi = min(vals), max(vals)
    return "%.2f" % lo if abs(hi - lo) < 0.005 else "%.2f–%.2f" % (lo, hi)


# trigger thresholds
epochs = st["epochs"]
thr = {(r["series"], r["det"], r["dcrc"]): r["activation_threshold"] for r in thr_rows}


def ep_thr(e, det):
    return thr.get((e["first"], det, "DCRC0"), "")


def ep_cells(cid):
    """per-epoch mean trigger fraction of a cell (None when no separable series in the epoch)"""
    return [(p or {}).get("mean") for p in st["trig_epoch"].get(cid, [])]


z9_cells = [c for c in cells if c["det"] in ("Z9", "Z10")]
z9_on = sorted({i + 1 for c in z9_cells for i, m in enumerate(ep_cells(c["id"])) if m is not None and m > 0.5})
step_cells = []
for c in cells:
    m = [x for x in ep_cells(c["id"]) if x is not None]
    if m and max(m) - min(m) > 0.3:
        step_cells.append(c)
stable_own = [c for c in own if all(x is None or x >= 0.95 for x in ep_cells(c["id"]))]

# templates
pk = st["pickup_cells"]
pk_det = sorted({p["det"] for p in pk}, key=znum)
det_rows = [r for r in tmpl if r["channel"] == "detector" and r.get("model")]
neg = sorted({(r["det"], r["channel"], r["id"]) for r in tmpl if "negative" in r.get("flags", "")})
no_det = [c["id"] for c in cells if c["id"] not in {r["id"] for r in det_rows}]


# ───────────────────────────────────────────────────────────────── 1 title
s = new(None, sec=15,
        zh="大家好，我是李志恒。今天讲 Run 7 里 Cf 之后的 LED 数据。按老师给的四部分讲：谁看到哪个 LED，幅度稳不稳，触发稳不稳，最后是脉冲模板。",
        en="Hi everyone, I'm Zhiheng. Today: the LED runs in Run 7, after the Cf calibration. Four parts, as Prof. Liu asked: "
           "who sees which LED, is the amplitude stable, is the trigger stable, and the pulse templates.")
tb = textbox(s, Inches(0.9), Inches(2.2), Inches(11.5), Inches(2.0))
run(tb.text_frame.paragraphs[0], Z("LED runs in SNOLAB Run 7", "SNOLAB Run 7 的 LED 数据"), 36, NAVY, bold=True)
run(tb.text_frame.add_paragraph(), Z("who sees which LED, stability over a week, and pulse templates", "谁看到哪个 LED、一周内的稳定性、脉冲模板"), 20, GRAY)
tb = textbox(s, Inches(0.9), Inches(4.8), Inches(11.5), Inches(1.2))
run(tb.text_frame.paragraphs[0], Z("Zhiheng Li  ·  University of Minnesota  ·  November 2026", "李志恒  ·  明尼苏达大学  ·  2026 年 11 月"), 16)
run(tb.text_frame.add_paragraph(), Z("%d LEDStability series, %s – %s (after the Cf calibration)", "%d 个 LEDStability series，%s – %s（Cf 刻度之后）") % (
    n_ok, when(st["first"])[:6], when(st["last"])[:6]), 13, GRAY)

# ───────────────────────────────────────────────────────────────── 2 data
s = new(Z("The data", "数据"), Z("%d LED series; one run = two LED phases", "%d 个 LED series；一次 run = 两段 LED") % n_ok, fig="fig_run_timeline.png", sec=55,
        hint="指着图：灰色是普通触发，蓝色是 LED 触发，两段中间停 3 秒。",
        zh="数据是 9 月 15 号到 21 号的 LED series，一共 %d 个。每个 run 先等大约 880 秒，然后开灯。"
           "**第一段 15 个 LED 一起闪，停 3 秒，第二段换 12 个 LED 再闪。**每个 LED 每秒闪一次，每段正好闪 151 次。"
           "还有一点要记住：每次触发只读出触发的那一个探测器。" % n_ok,
        en="The data: %d LED series, from September 15 to 21. Each run waits about 880 seconds, then the LEDs turn on. "
           "**Phase one: 15 LEDs flash together. Three seconds off. Phase two: 12 other LEDs.** Each LED flashes once per "
           "second, exactly 151 times per phase. One thing to keep in mind: each trigger reads out only the detector that "
           "triggered." % n_ok)
pic(s, "fig_run_timeline.png", L, T, W, Inches(3.9))
lines(s, [Z("Sequencer script SR1a LEDStability: 800 s wait, then LEDs at 1 Hz, 100 µs pulses (Z17 200 µs, Z20 50 µs).", "序列脚本 SR1a LEDStability：先等 800 s，然后 LED 以 1 Hz 闪，脉宽 100 µs（Z17 200 µs，Z20 50 µs）。"),
          Z("Phase 1: 15 LEDs  ·  3 s off  ·  phase 2: 12 LEDs.  151 flashes per phase in all %d series.", "第一段：15 个 LED  ·  停 3 s  ·  第二段：12 个 LED。全部 %d 个 series 里每段都是 151 次闪光。") % n_ok,
          Z("Not used: 24260916_232802 (74 events), 24260918_084531 (no LED flashes).  One detector is read out per trigger.", "没有用：24260916_232802（74 个事件）、24260918_084531（没有 LED 闪光）。每次触发只读出一个探测器。")],
      L, Inches(5.25), W, Inches(2.0), size=14)

# ───────────────────────────────────────────────────────────────── 3 which LED
s = new(Z("Which LED made the trigger", "这次触发来自哪个 LED"), Z("each LED flashes at its own fixed time within the second", "每个 LED 在一秒内固定的时刻闪"), fig="fig_flash_groups.png",
        sec=70, hint="一个峰就是一个 LED。",
        zh="数据里没有记是哪个 LED 闪的，只有触发时间和触发的探测器。但是每个 LED 在一秒里闪的时刻是固定的。"
           "**把触发时间对一秒取余，每个 LED 就是一个峰。**看同一次闪光的探测器，触发时间差不超过 0.2 毫秒。"
           "脚本告诉我们哪些 LED 开着：峰上有它自己的探测器，就是它；自己不触发的，用排除法。"
           "有时候两个 LED 正好同时闪，分不开，这样的组有 %d 个，我们不用。" % n_amb,
        en="The data do not record which LED flashed. We only have the trigger time and the detector. But each LED flashes "
           "at a fixed time within the second. **Take the trigger time modulo one second, and every LED is one peak.** "
           "Detectors that see the same flash trigger within 0.2 milliseconds of each other. The script tells us which "
           "LEDs are on. If the LED's own detector is in the peak, the peak is that LED; if not, we use elimination. "
           "Sometimes two LEDs flash at the same moment and cannot be separated. That happens in %d groups; we leave "
           "them out." % n_amb)
pic(s, "fig_flash_groups.png", L, T, W, Inches(3.9))
lines(s, [Z("Same flash, different detectors: trigger times within %d … +%d µs of the LED's own detector.", "同一次闪光、不同探测器：触发时间与 LED 自己的探测器相差 %d … +%d µs。") % (off_lo, off_hi),
          Z("%d flash groups in %d series; %d hold two LEDs within 0.2 ms (not separable, left out); "
          "%d are a second Z1 trigger 13 ms after its flash (not counted).", "%d 个闪光组，来自 %d 个 series；%d 个组里两个 LED 相差不到 0.2 ms（分不开，不用）；%d 个是 Z1 在闪光后 13 ms 的第二次触发（不计）。") % (n_groups, n_ok, n_amb, n_ret),
          Z("!Every other LED trigger is assigned to exactly one LED.", "!其余每个 LED 触发都对应到唯一的一个 LED。")],
      L, Inches(5.25), W, Inches(2.0), size=14)

# ───────────────────────────────────────────────────────────────── 4-5 visibility
for ph, sec in (("phase1", 70), ("phase2", 45)):
    cs = [c for c in cells if c["phase"] == ph]
    nb = [c for c in cs if c["own_led"] == "False"]
    if ph == "phase1":
        zh = ("这张图回答：**每个 LED 闪的时候，哪个探测器触发。**横轴是第一段开的 15 个 LED，纵轴是探测器。"
              "格子里的数是：这个 LED 闪 151 次，这个探测器在多大比例的闪光上触发了，对 %d 个 series 取平均。"
              "红框是 LED 自己的探测器，大部分是 1.00。**红框外面也有数字：隔壁的探测器也看到了光。**"
              "每个有数字的格子有一个编号，比如 P1-07，后面做模板用。" % n_ok)
        en = ("This plot answers: **when an LED flashes, which detector triggers?** Columns are the 15 LEDs of phase one, "
              "rows are detectors. The number is the fraction of the 151 flashes on which that detector triggers, "
              "averaged over %d series. The red box is the LED's own detector; most are 1.00. **There are numbers outside "
              "the red boxes too: a neighbour also sees the light.** Every cell with a number has an ID, like P1-07. "
              "We use it for the templates later." % n_ok)
    else:
        zh = ("第二段一样，12 个 LED。规律也一样：自己的探测器基本每次都触发，隔壁的探测器也经常触发。"
              "两段加起来一共 %d 个格子。" % len(cells))
        en = ("Phase two, the same picture with 12 LEDs. The same pattern: the own detector triggers on almost every "
              "flash, and a neighbour often does too. Together the two phases have %d cells." % len(cells))
    s = new(Z("Part 1 — who triggers on which LED: %s", "第一部分 — 谁在哪个 LED 上触发：%s") % ph.replace("phase", "phase "),
            Z("fraction of each LED's 151 flashes on which a detector triggers, mean of %d series", "每个 LED 的 151 次闪光里探测器触发的比例；%d 个 series 的平均") % n_ok,
            fig="visibility_%s.png" % ph, sec=sec, zh=zh, en=en)
    pic(s, "visibility_%s.png" % ph, L, T, Inches(8.6), Inches(6.1))
    lines(s, [Z("Red box = the LED's own detector.", "红框 = LED 自己的探测器。"),
              Z("Neighbour cells:  ", "邻居格子：  ") + ";  ".join("%s → %s %s" % (ledname(c["led"]), c["det"], pct(c["fraction"])) for c in nb),
              Z("%d cells in this phase, IDs %s … %s: one template each (Part 4).", "这一段有 %d 个格子，编号 %s … %s：每个做一个模板（第四部分）。") % (len(cs), cs[0]["id"], cs[-1]["id"])],
          Inches(9.25), Inches(1.4), Inches(3.7), Inches(5.6), size=12)

# ───────────────────────────────────────────────────────────────── 6 what we learn
s = new(Z("Part 1 — what we learn", "第一部分 — 结论"), Z("light reaches the adjacent detector only, in a fixed direction per LED", "光只到相邻的探测器，每个 LED 的方向固定"), sec=70,
        zh="第一部分的结论。第一，**光只照到编号相邻的探测器，再远没有。**%d 个格子里 %d 个是隔壁的探测器，没有一个隔一个号的。"
           "第二，也没有跨组的：所有的对都在 1 到 6、7 到 12、13 到 18、19 到 24 这四组里面。"
           "第三，**方向是固定的：0 号和 1 号 LED 照编号小一号的探测器，3、4、5 号 LED 照大一号的。**"
           "在一组的两头没有邻居，所以那些 LED 只有自己看得到。只有两个例外，写在下面。"
           "最后，我们只读出触发的探测器，低于阈值的光看不到，所以这些数是下限。" % (len(cells), len(neigh)),
        en="What we learn from part one. First, **light reaches only the detector with the adjacent number, nothing "
           "further.** %d of the %d cells are a neighbour, and none skips a number. Second, no pair crosses a group: all "
           "pairs are inside detectors 1 to 6, 7 to 12, 13 to 18, or 19 to 24. Third, **the direction is fixed: LED 0 and "
           "1 light the detector with the number below, LED 3, 4 and 5 the one above.** At the end of a group there is no "
           "neighbour, so those LEDs are seen only by their own detector. There are two exceptions, listed below. "
           "Finally, only the triggering detector is read out, so light below threshold is invisible. These numbers are "
           "lower limits." % (len(neigh), len(cells)))
lines(s, [Z("!Adjacent detector only: %d of %d cells are a neighbour; no cell skips a detector number.", "!只到相邻的探测器：%d / %d 个格子是邻居；没有隔一个编号的。") % (len(neigh), len(cells)),
          Z("All pairs lie inside Z1–6, Z7–12, Z13–18, Z19–24: none crosses Z6|Z7, Z12|Z13, Z18|Z19 "
          "(the ODB shows the same groups: one DCRC for Z1–6 and Z19–24, two for Z7–18).", "所有的对都在 Z1–6、Z7–12、Z13–18、Z19–24 之内：没有跨过 Z6|Z7、Z12|Z13、Z18|Z19 的（ODB 里也是这样分组：Z1–6 和 Z19–24 各一块 DCRC，Z7–18 各两块）。"),
          Z("!Direction: LED 0, 1 → the detector with the number below; LED 3, 4, 5 → the one above (%d of %d LEDs).", "!方向：0、1 号 LED → 编号小一号的探测器；3、4、5 号 LED → 大一号的（%d / %d 个 LED）。") % (len(rule_ok), n_leds),
          Z("No detector on that side (end of a group, or Z12): %s — seen only by their own detector.", "那一侧没有探测器（组的两端，或 Z12）：%s — 只有自己的探测器看到。") % ", ".join(ledname(r["led"]) for r in rule_end),
          Z("Exceptions: ", "例外：") + ";  ".join(rule_exc) + ".",
          Z("Own detector: fraction 1.00 for %d of %d LEDs; lower for %s; never for %s (thresholds: Part 3).", "自己的探测器：%d / %d 个 LED 的比例是 1.00；较低的有 %s；从不触发的有 %s（阈值：见第三部分）。") % (
              len(own_full), n_leds, ", ".join("%s %s" % (ledname(r["led"]), pct(r["own"])) for r in own_part),
              ", ".join(ledname(r["led"]) for r in own_never)),
          Z("One detector is read out per trigger → light below a detector's threshold is not seen: lower limits.", "每次触发只读出一个探测器 → 低于阈值的光看不到：这些都是下限。")],
      L, T, W, Inches(5.9), size=15)

# ───────────────────────────────────────────────────────────────── 7 amplitude map
s = new(Z("Part 2 — amplitude vs time", "第二部分 — 幅度随时间"), Z("median pulse amplitude per series / its median over all series, one row per cell", "每个 series 的脉冲幅度中位数 ÷ 所有 series 的中位数；一行一个格子"),
        fig="fig_amp_map.png", sec=65, hint="白色 = 1；红 = 偏高；蓝 = 偏低；灰 = 没有数据。",
        zh="第二部分，幅度随时间。每一行是一个格子，每一列是一个 series，按时间排。颜色是这个 series 的幅度除以这一行的中位数。"
           "**白色就是正常。**大部分是白的：%s%% 的点在 5%% 以内，%s%% 在 10%% 以内。"
           "所以大部分是稳定的。另外，多数格子在慢慢往下走，中位数是每天 %s%%。有几处颜色很明显，后面单独看。"
           % (amp5, amp10, slope["median"]),
        en="Part two, amplitude over time. Each row is one cell, each column one series, in time order. The colour is "
           "that series' amplitude divided by the row's median. **White means normal.** Most of it is white: %s percent "
           "of the points are within 5 percent, %s percent within 10 percent. So it is mostly stable. Most cells also go "
           "down slowly; the median is %s percent per day. A few spots stand out. We look at them in a moment."
           % (amp5, amp10, slope["median"]))
pic(s, "fig_amp_map.png", L, T, Inches(8.8), Inches(6.1))
lines(s, [Z("!Mostly stable:", "!大部分稳定："),
          Z("%s %% of the %d (cell, series) values are within ±5 %%, %s %% within ±10 %%.", "%s %% 的值（共 %d 个“格子 × series”）在 ±5 %% 以内，%s %% 在 ±10 %% 以内。") % (amp5, st["amp_cells_series"], amp10),
          Z("Slow decline: %d of %d cells have a negative slope; median %s %% per day (range %s … %s).", "缓慢下降：%d / %d 个格子斜率为负；中位数每天 %s %%（范围 %s … %s）。") % (
              slope["n_negative"], slope["n_cells"], slope["median"], slope["min"], slope["max"]),
          Z("Amplitude = median of the good pulses in a series (peak above baseline, ADC, after removing the LED pickup "
          "spikes); cell value = median over its channels.", "幅度 = 一个 series 里好脉冲的中位数（峰值减基线，ADC，先去掉 LED 串扰尖峰）；格子的值 = 各通道的中位数。"),
          Z("Every channel vs time: backup.", "每个通道随时间的图：见备用页。")],
      Inches(9.5), Inches(1.4), Inches(3.5), Inches(5.6), size=13)

# ───────────────────────────────────────────────────────────────── 8 whose change
s = new(Z("Part 2 — whose change is it: the LED or the detector?", "第二部分 — 是谁在变：LED 还是探测器？"), Z("same LED on two detectors, and the same detector with its two LEDs", "同一个 LED 被两个探测器看到；同一个探测器看自己的两个 LED"),
        fig="fig_same_led.png", sec=60, hint="左图两条线一起动；中间两条线各走各的。",
        zh="幅度在变，是 LED 在变，还是探测器在变？可以这样查。左边：同一个 LED，两个探测器在看，两条线一起动。"
           "中间：同一个探测器，看自己的两个不同的 LED，两条线不一起动。右边是所有的对：蓝色是同一个 LED，相关系数大多在 0.9 以上；"
           "橙色是同一个探测器的两个 LED，大多接近零。**所以变化主要来自 LED 的光，不是探测器。**",
        en="The amplitude changes. Is it the LED, or the detector? We can check. Left: one LED, seen by two detectors. "
           "The two lines move together. Middle: one detector, with its two different LEDs. The lines do not move "
           "together. Right: all the pairs. Blue is one LED on two detectors: the correlation is mostly above 0.9. "
           "Orange is one detector with its two LEDs: mostly near zero. **So the changes come mainly from the LED light, "
           "not from the detectors.**")
pic(s, "fig_same_led.png", L, T, W, Inches(4.2))
lines(s, [Z("!One LED seen by two detectors: r ≥ 0.9 for %d of %d pairs (%s).", "!同一个 LED、两个探测器：%d / %d 对的 r ≥ 0.9（%s）。") % (
              len(sl_hi), len(sl_led), ", ".join("%s %.2f" % (ledname(p["led"]), p["r"]) for p in sl_hi)),
          Z("Lower: ", "较低的：") + ", ".join("%s (%s, %s) %.2f" % (ledname(p["led"]), p["a"], p["b"], p["r"]) for p in sl_lo) + ".",
          Z("One detector with its two LEDs: ", "同一个探测器、两个 LED：") + ", ".join("%s %.2f" % (p["det"], p["r"]) for p in sl_det) + ".",
          Z("→ the changes are mainly in the LED light. (Z20: both of its LEDs dropped together, next slide.)", "→ 变化主要来自 LED 的光。（Z20：它的两个 LED 一起变暗，见下一页。）")],
      L, Inches(5.5), W, Inches(1.9), size=13)

# ───────────────────────────────────────────────────────────────── 9 cases
s = new(Z("Part 2 — cases to look at again", "第二部分 — 需要再看的情况"), Z("amplitude / median, detector median over its channels", "幅度 ÷ 中位数；探测器取各通道的中位数"), fig="fig_stab_cases.png",
        sec=75, hint="先讲 Z20，再快速过其他几个。",
        zh="这几个要再看。**最明显的是 9 月 18 号凌晨，连续 %d 个 series：Z20 的幅度只有正常的 %s。**"
           "Z19 看 Z20 的 LED，也只有 %s；但 Z19 看自己的 LED 是正常的。所以是 Z20 的 LED 变暗了。"
           "下一个 run 完全没有 LED 闪光，下午一点恢复正常。数据库里 LED 的设置没有变。"
           "另外，第一天有几个格子偏高大约两成，之后慢慢降下来。"
           % (len(z20a), rng([x[1] for x in z20a]), rng([x[1] for x in z19])),
        en="These need a second look. **The clearest is the early morning of September 18, %d series in a row: Z20 is at "
           "only %s of normal.** Z19, looking at Z20's LED, is at %s; but Z19 with its own LED is normal. So Z20's LEDs "
           "were dim. The next run had no LED flashes at all, and by 1 pm it was back to normal. The LED settings in the "
           "ODB did not change. Also, on the first day a few cells are about 20 percent high, and then come down."
           % (len(z20a), rng([x[1] for x in z20a]), rng([x[1] for x in z19])))
pic(s, "fig_stab_cases.png", L, T, Inches(8.3), Inches(5.9))
lines(s, [Z("!%s – %s: Z20 at %s (its LED0) and %s (its LED3); Z19 seeing Z20's LED0 at %s, while Z19 with its own LED is "
          "normal → Z20's LEDs were dim.", "!%s – %s：Z20 只有正常值的 %s（它的 LED0）和 %s（它的 LED3）；Z19 看 Z20 的 LED0 是 %s，而 Z19 看自己的 LED 正常 → 是 Z20 的 LED 变暗了。") % (when(z20a[0][0]), when(z20a[-1][0])[-5:], rng([x[1] for x in z20a]),
                                              rng([x[1] for x in z20b]), rng([x[1] for x in z19])),
          Z("The next run (18 Sep 08:45) has no LED flashes; normal again at 13:03. LED settings in the ODB unchanged.", "下一个 run（9 月 18 日 08:45）没有 LED 闪光；13:03 恢复正常。ODB 里的 LED 设置没有变。"),
          Z("First day (15 Sep) high: ", "第一天（9 月 15 日）偏高：") + ", ".join("%s ← %s %.2f" % (cell[k]["det"], ledname(cell[k]["led"]), v)
                                                   for v, k in first_high[:5]) + ".",
          Z("Black lines: trigger thresholds changed (Part 3). Red dotted: 0913 → 0918 script.", "黑线：触发阈值改动（第三部分）。红色虚线：0913 → 0918 脚本。")],
      Inches(9.0), Inches(1.4), Inches(4.0), Inches(5.6), size=12)

# ───────────────────────────────────────────────────────────────── 10 trigger fraction
z9d = "Z9"
s = new(Z("Part 3 — trigger fraction vs time", "第三部分 — 触发比例随时间"), Z("fraction of the 151 flashes on which the detector triggers, one row per cell", "151 次闪光里探测器触发的比例；一行一个格子"),
        fig="fig_trig_map.png", sec=80, hint="黑线 = 触发阈值改了。黄 = 每次都触发。",
        zh="第三部分，触发比例随时间。还是一行一个格子，一列一个 series。黄色是每次闪光都触发。"
           "**自己的 LED 那些行一直是黄的，很稳定。**其他行有台阶：一下子从 0 变到 1，或者反过来。"
           "我去查了数据库：**台阶正好对应触发阈值被改的时间，就是图上的黑线。**这一周一共有 %d 段不同的阈值设置。"
           "比如 Z9 和 Z10：只在第 %s 段触发，正好是它们阈值调低的时候。所以这些台阶是设置变了，不是探测器不稳定。"
           % (len(epochs), "、".join(str(x) for x in z9_on)),
        en="Part three, trigger fraction over time. Again one row per cell, one column per series. Yellow means it "
           "triggers on every flash. **The own-LED rows stay yellow: stable.** Other rows show steps: from zero to one, or "
           "back. I checked the ODB: **the steps are exactly where the trigger thresholds were changed, the black "
           "lines.** There are %d different threshold settings during the week. For example Z9 and Z10 trigger only in "
           "periods %s, which is when their thresholds were low. So the steps are settings, not unstable detectors."
           % (len(epochs), " and ".join(str(x) for x in z9_on)))
pic(s, "fig_trig_map.png", L, T, Inches(8.8), Inches(6.1))
lines(s, [Z("!Own-LED cells: %d of %d stay at ≥ 0.95 in every period.", "!自己 LED 的格子：%d / %d 个在每一段都 ≥ 0.95。") % (len(stable_own), len(own)),
          Z("!The steps follow the L1 trigger thresholds in the ODB (black lines): %d periods.", "!台阶对应 ODB 里 L1 触发阈值的改动（黑线）：共 %d 段。") % len(epochs),
          Z("Z9 triggers only in periods %s, where its threshold is %s (%s in the others).", "Z9 只在第 %s 段触发，那时它的阈值是 %s（其他段是 %s）。") % (
              ", ".join(str(x) for x in z9_on),
              "/".join(sorted({str(ep_thr(e, z9d)) for e in epochs if e["epoch"] in z9_on}, key=int)),
              "/".join(sorted({str(ep_thr(e, z9d)) for e in epochs if e["epoch"] not in z9_on}, key=int))),
          Z("%d cells change by more than 0.3 between periods (table in the backup).", "%d 个格子在不同段之间变化超过 0.3（表在备用页）。") % len(step_cells),
          Z("Inside a period a few cells near threshold still drift.", "同一段内，少数接近阈值的格子仍有漂移。"),
          Z("Grey: two LEDs flash together in that series.", "灰色：那个 series 里两个 LED 同时闪，分不开。")],
      Inches(9.5), Inches(1.4), Inches(3.5), Inches(5.6), size=13)

# ───────────────────────────────────────────────────────────────── 11 template method + clean cell
cc = cell[CLEAN]
s = new(Z("Part 4 — one template per cell, made like the Z7 template", "第四部分 — 每个格子一个模板，做法和 Z7 模板一样"),
        Z("%s: %s with %s — aligned pulses (blue), template (red), analytic pulse (dashed), residual (gray)", "%s：%s 看 %s — 对齐后的脉冲（蓝）、模板（红）、解析脉冲（虚线）、残差（灰）") % (CLEAN, cc["det"], ledname(cc["led"])),
        fig="cell_%s.png" % CLEAN, sec=75, hint="方法和 Z7 模板一样，只多一步去尖峰。",
        zh="第四部分，模板。每个格子做一个模板，%d 个 series 合在一起。方法和 Z7 的模板一样："
           "每个脉冲先低通，减基线，除以峰值，用两个指数拟合，起始时间是自由的。**按拟合出来的起始时间对齐，再平均。**"
           "只多了一步：LED 通电的时候读出上有很窄的尖峰，先用一个很短的中值滤波去掉。"
           "最后对模板拟合一个解析函数：一个上升，两个下降。这是一个干净的例子，%s 看自己的 LED：残差基本是平的。"
           % (n_ok, cc["det"]),
        en="Part four, templates. One template per cell, all %d series together. The method is the same as for the Z7 "
           "template. Each pulse is low-passed, baseline-subtracted, divided by its peak, and fitted with two "
           "exponentials with a free start time. **Pulses are aligned on the fitted start, then averaged.** One extra "
           "step: when an LED is driven, the readout picks up a very narrow spike. A short median filter removes it "
           "first. At the end we fit an analytic function to the template: one rise, two falls. This is a clean example, "
           "%s with its own LED: the residual is nearly flat." % (n_ok, cc["det"]))
pic(s, "cell_%s.png" % CLEAN, L, T, Inches(8.4), Inches(6.1))
lines(s, [Z("Events of a cell: its detector triggered on that LED's flash; all 12 channels.", "一个格子的事件：它的探测器在这个 LED 的闪光上触发；12 个通道都用。"),
          Z("Per pulse (Z7 chain): 100 kHz low-pass → baseline → ÷ peak → 2-exp fit, start free → align on the fitted start.", "每个脉冲（Z7 的流程）：100 kHz 低通 → 减基线 → ÷ 峰值 → 双指数拟合（起点自由）→ 按拟合的起点对齐。"),
          Z("LED data only: 11-sample (18 µs) median filter first, against the LED pickup spikes.", "LED 数据多一步：先做 11 点（18 µs）中值滤波，去掉 LED 串扰尖峰。"),
          Z("Template = mean of the aligned pulses of all series.", "模板 = 所有 series 对齐后脉冲的平均。"),
          Z("!Analytic pulse: A₁(e^(−t/τf1) − e^(−t/τr)) + A₂(e^(−t/τf2) − e^(−t/τr))", "!解析脉冲：A₁(e^(−t/τf1) − e^(−t/τr)) + A₂(e^(−t/τf2) − e^(−t/τr))"),
          Z("%s single-pulse fits; %d channel templates with signal; %d detector templates.", "%s 个单脉冲拟合；%d 个有信号的通道模板；%d 个探测器模板。") % (
              format(st["n_pulses_fit_ok"], ","), st["chan_signal"], st["det_templates"])],
      Inches(9.05), Inches(1.4), Inches(4.0), Inches(5.6), size=12)

# ───────────────────────────────────────────────────────────────── 12 pickup
exc = cell[EX]
s = new(Z("Part 4 — own LED: pickup of the LED drive pulse", "第四部分 — 自己的 LED：LED 驱动脉冲的串扰"), Z("%s: %s with %s", "%s：%s 看 %s") % (EX, exc["det"], ledname(exc["led"])),
        fig="cell_%s.png" % EX, sec=55, hint="只在自己 LED 的格子里有；隔壁探测器没有。",
        zh="但是有些自己 LED 的格子，脉冲开头有问题。比如 Z7：有几个通道在脉冲开始的地方有一个很快的跳变，然后才是声子脉冲。"
           "**这是 LED 的驱动脉冲串进了自己探测器的读出。**隔壁的探测器看同一个 LED，就没有。"
           "一共 %d 个格子有，都是自己的 LED。这些格子模板的开头不能直接用：可以用隔壁探测器的模板，或者把开头去掉再拟合。" % len(pk),
        en="But some own-LED cells have a problem at the start of the pulse. Take Z7: several channels show a fast "
           "step at the start, before the phonon pulse. **This is the LED drive pulse, picked up by the detector's own "
           "readout.** A neighbour looking at the same LED does not show it. %d cells have it, all own-LED. For these, "
           "the start of the template cannot be used as it is. We can use the neighbour's template, or cut the start "
           "before fitting." % len(pk))
pic(s, "cell_%s.png" % EX, L, T, Inches(8.4), Inches(6.1))
lines(s, [Z("!A fast transient at the pulse start: the LED drive, picked up by the detector's own readout.", "!脉冲开头有一个很快的瞬变：LED 的驱动脉冲串进了自己探测器的读出。"),
          Z("In %d cells, all own-LED: %s.", "共 %d 个格子，都是自己的 LED：%s。") % (len(pk), ", ".join("%s (%s)" % (p["id"], p["det"]) for p in pk)),
          Z("Neighbour cells of the same LEDs are clean.", "同一个 LED 的邻居格子是干净的。"),
          Z("The 18 µs median filter removes only the narrow spike.", "18 µs 的中值滤波只能去掉窄的尖峰。")] +
         ([Z("Not a phonon pulse at all (large negative transient): ", "根本不是声子脉冲（很大的负向瞬变）：") + ", ".join("%s %s (%s)" % n_ for n_ in neg) + "."] if neg else []) +
         [Z("For these cells: use the neighbour's template, or cut the first ~0.2 ms before fitting.", "这些格子：改用邻居的模板，或去掉开头约 0.2 ms 再拟合。")],
      Inches(9.05), Inches(1.4), Inches(4.0), Inches(5.6), size=12)

# ───────────────────────────────────────────────────────────────── 13 overview
s = new(Z("Part 4 — all %d cells", "第四部分 — 全部 %d 个格子") % len(cells), Z("detector template (channels with signal, weighted by their amplitude) and its analytic pulse", "探测器模板（有信号的通道按幅度加权）和它的解析脉冲"),
        fig="cells_overview.png", sec=50,
        zh="这是全部 %d 个格子，每个格子一个小图：红色是探测器的模板，黑色虚线是解析函数。"
           "每个格子十二个通道的图在备用页，拟合出来的时间常数也在备用页和 CSV 文件里。" % len(cells),
        en="All %d cells, one small panel each: the detector template in red, the analytic pulse in black dashes. The "
           "twelve-channel plot of every cell is in the backup, and so are the fitted time constants." % len(cells))
pic(s, "cells_overview.png", L, T, W, Inches(5.75))
caption(s, Z("Time constants of every cell and channel: out/lpfit/LED_cell_templates.csv; own-LED cells in the backup table.", "每个格子、每个通道的时间常数：out/lpfit/LED_cell_templates.csv；自己 LED 的格子见备用页的表。")
        + (Z("  No detector template (no channel with enough pulses above SNR 8): %s.", "  没有探测器模板（没有通道有足够多信噪比 ≥ 8 的脉冲）：%s。") % ", ".join(no_det) if no_det else ""),
        L, Inches(7.0), Inches(11.8), size=10)

# ───────────────────────────────────────────────────────────────── 14 example pulses
s = new(Z("Part 4 — example pulses: Z7 PSum with Z7's LED", "第四部分 — 例子脉冲：Z7 PSum，Z7 自己的 LED"), Z("one typical pulse per series, light → dark in time", "每个 series 一个典型脉冲；颜色由浅到深 = 时间由早到晚"),
        fig="example_pulses_%s.png" % EX, sec=75, hint="左：原始 ADC；中：放大；右：归一化以后只看形状。",
        zh="老师想看脉冲形状随时间怎么变。这是 Z7 看自己的 LED，十二个通道加起来，就是 PSum。"
           "**每个 series 挑一个典型的脉冲，一共 %d 条，颜色从浅到深是从早到晚。**"
           "左边是原始的 ADC，整条 52 毫秒。中间放大。开头那个负的尖峰就是刚才说的 LED 串扰。"
           "中间能看到幅度从浅色到深色在变小，就是第二部分说的 Z7 这个 LED 慢慢变暗。"
           "右边去掉尖峰，每条除以自己的峰值，只看形状：这一周的脉冲基本叠在一起，形状没有变。" % n_ok,
        en="Prof. Liu wanted to see how the pulse shape changes with time. This is Z7 with its own LED, all twelve "
           "channels summed: the PSum. **One typical pulse per series, %d in total. Light to dark is early to late.** "
           "Left: raw ADC, the whole 52 milliseconds. Middle: zoom. The negative spike at the start is the LED pickup "
           "from before. In the middle you can see the amplitude going down from light to dark: that is the slow "
           "decline of this LED from part two. Right: spike removed, each pulse divided by its own peak, so only the "
           "shape is left. The pulses of the week lie nearly on top of each other: the shape did not change." % n_ok)
pic(s, "example_pulses_%s.png" % EX, L, T, W, Inches(5.0))
caption(s, Z("Typical = the pulse whose PSum amplitude is closest to that series' median. PSum = unweighted sum of the 12 raw "
           "channels, each minus its own baseline; no filter in the left and middle panels. Amplitude of this cell: %+.1f %% per day "
           "(Part 2); the normalised shape stays the same. Rise and fall times per series: backup.", "典型 = PSum 幅度最接近该 series 中位数的那个脉冲。PSum = 12 个原始通道各自减基线后直接相加；左图和中图没有滤波。这个格子的幅度：每天 %+.1f %%（第二部分）；归一化后的形状不变。每个 series 的上升和下降时间：见备用页。") % camp[EX]["slope_pct_per_day"],
        L, Inches(6.4), W)

# ───────────────────────────────────────────────────────────────── 15 summary
s = new(Z("Summary, and what comes next", "总结和下一步"), sec=65,
        zh="总结。一，每个 LED 触发都能对应到一个 LED；光只照到相邻的探测器，方向是固定的。"
           "二，幅度大部分在 10%% 以内，变化主要来自 LED 本身；9 月 18 号凌晨 Z20 的 LED 变暗，要查原因。"
           "三，触发比例的台阶是阈值设置变了。四，%d 个格子都有模板和解析函数，方法和 Z7 一样；有几个探测器自己的 LED 有串扰，要注意。"
           "下一步：查 Z20 那几个小时发生了什么，处理串扰的格子，再和老师确认这些模板要怎么用。" % len(cells),
        en="To sum up. One: every LED trigger is traced to one LED. Light reaches only the adjacent detector, in a fixed "
           "direction. Two: amplitudes are mostly within 10 percent, and the changes come mainly from the LEDs. Z20's "
           "LEDs were dim on the morning of September 18; we need to find out why. Three: the steps in the trigger "
           "fraction are threshold settings. Four: all %d cells have a template and an analytic pulse, made like the Z7 "
           "template. A few detectors pick up their own LED drive; watch out for those. Next: find out what happened to "
           "Z20 in those hours, handle the pickup cells, and agree on how these templates will be used." % len(cells))
lines(s, [Z("Every LED trigger is assigned to one LED. Light reaches the adjacent detector only, in a fixed direction per LED.", "每个 LED 触发都对应到一个 LED。光只到相邻的探测器，每个 LED 的方向固定。"),
          Z("Amplitude: %s %% of (cell, series) within ±5 %%, %s %% within ±10 %%; the changes are mainly in the LED light.", "幅度：%s %% 的“格子 × series”在 ±5 %% 以内，%s %% 在 ±10 %% 以内；变化主要来自 LED 的光。") % (amp5, amp10),
          Z("Trigger fraction: own-LED cells stable; the steps follow the L1 threshold settings (%d periods).", "触发比例：自己 LED 的格子稳定；台阶对应 L1 阈值设置的改动（%d 段）。") % len(epochs),
          Z("%d cells: template + analytic pulse (one rise, two falls), Z7 method; Z7 PSum over the week shown.", "%d 个格子：模板 + 解析脉冲（一个上升、两个下降），Z7 的方法；展示了 Z7 PSum 一周内的变化。") % len(cells),
          Z("!To look at: Z20's LEDs dim on %s – %s, then a run with no LED flashes.", "!要再看：Z20 的 LED 在 %s – %s 变暗，之后一个 run 没有 LED 闪光。") % (when(z20a[0][0]), when(z20a[-1][0])[-5:]),
          Z("!To look at: LED-drive pickup in the own-LED cells of %s.", "!要再看：%s 的自己 LED 格子里有 LED 驱动串扰。") % ", ".join(pk_det),
          Z("!To look at: Z1 triggers again 13 ms after some LED flashes (%d series).", "!要再看：Z1 在某些闪光后 13 ms 再触发一次（%d 个 series）。") % n_ret,
          Z("!Open: the 0918 script switches off Z17's L1 trigger, but the ODB shows it enabled in all %d series, and Z17 keeps triggering.", "!未解决：0918 脚本会关掉 Z17 的 L1 触发，但 ODB 显示全部 %d 个 series 里它都是开的，Z17 也一直在触发。") % n_ok,
          Z("Code and results: ~/urop/LED/R7 on MSI (out/summary, out/stability, out/lpfit).", "代码和结果：MSI 上的 ~/urop/LED/R7（out/summary、out/stability、out/lpfit）。")],
      L, T, W, Inches(5.9), size=15)
n_main = n_slide

# ───────────────────────────────────────────────────────────────── backup
s = new(Z("Backup: pulse shape vs time, %s", "备用：脉冲形状随时间，%s") % EX, Z("per series: median rise and fall time of the single-pulse fits, per channel", "每个 series：单脉冲拟合的上升和下降时间中位数，按通道"),
        fig="shape_vs_time_%s.png" % EX)
if s:
    pic(s, "shape_vs_time_%s.png" % EX, L, T, W, Inches(5.6))
    caption(s, Z("2-exp fit of every pulse (Z7 chain). Channels with LED pickup in this cell have less reliable rise times.", "每个脉冲的双指数拟合（Z7 的流程）。这个格子里有 LED 串扰的通道，上升时间不太可靠。"), L, Inches(6.9), W)

s = new(Z("Backup: analytic pulse of the detector templates", "备用：探测器模板的解析脉冲"), Z("own-LED cells; every cell and channel: out/lpfit/LED_cell_templates.csv", "自己 LED 的格子；全部格子和通道：out/lpfit/LED_cell_templates.csv"))
rows = [[Z("cell", "格子"), Z("detector ← LED", "探测器 ← LED"), "τ_rise [µs]", "τ_fall1 [µs]", "τ_fall2 [µs]", Z("model", "模型")]]
own_ids = {c["id"] for c in own}
for r in det_rows:
    if r["id"] in own_ids and r.get("tau_rise_us"):
        f2 = r.get("tau_fall2_us", "")
        f2 = "—" if not f2 else ("> 20 000" if float(f2) > 20000 else "%.0f" % float(f2))
        rows.append([r["id"], "%s ← %s" % (r["det"], ledname(r["led"])), "%.0f" % float(r["tau_rise_us"]),
                     "%.0f" % float(r["tau_fall1_us"]), f2, r["model"]])
half = (len(rows) + 1) // 2
cw = [Inches(0.65), Inches(1.75), Inches(0.9), Inches(0.95), Inches(1.0), Inches(0.65)]
table(s, rows[:half], L, T, Inches(5.9), Inches(0.3) * half, col_w=cw, size=10)
if len(rows) > half:
    table(s, [rows[0]] + rows[half:], Inches(6.85), T, Inches(5.9), Inches(0.3) * (len(rows) - half + 1), col_w=cw, size=10)
caption(s, Z("τ_fall2 > 20 000 µs: the slow tail is longer than the 24 ms fit window and is not constrained. "
           "Cells with LED pickup at the start (%s) have a less reliable τ_rise.", "τ_fall2 > 20 000 µs：慢尾巴比 24 ms 的拟合窗口还长，定不出来。开头有 LED 串扰的格子（%s）τ_rise 不太可靠。") % ", ".join(p["id"] for p in pk), L, Inches(6.55), W)

hdr = ["%d: %s – %s (%d)" % (e["epoch"], when(e["first"]), when(e["last"]), e["n_series"]) for e in epochs]
s = new(Z("Backup: L1 trigger thresholds per period", "备用：每一段的 L1 触发阈值"),
        Z("ActivationThreshold (DCRC0) from the ODB at the start of each run; period: first – last series (number of series)", "每个 run 开始时 ODB 里的 ActivationThreshold（DCRC0）；段：第一个 – 最后一个 series（series 数）"))
dets_thr = sorted({c["det"] for c in step_cells}, key=znum)
rows = [[Z("detector", "探测器")] + hdr] + [[z] + [str(ep_thr(e, z)) for e in epochs] for z in dets_thr]
table(s, rows, L, T, W, Inches(0.3) * len(rows), col_w=[Inches(1.2)] + [Inches(1.85)] * len(epochs), size=10)
caption(s, Z("Detectors with a cell whose trigger fraction changes by more than 0.3 between periods. "
           "All detectors and both DCRCs: out/summary/trigger_settings.csv.", "只列出有格子的触发比例在不同段之间变化超过 0.3 的探测器。全部探测器和两块 DCRC：out/summary/trigger_settings.csv。"), L, Inches(6.75), W)

s = new(Z("Backup: trigger fraction per period", "备用：每一段的触发比例"), Z("mean over the series of a period, for the cells that change by more than 0.3; — = no separable series", "一段内各 series 的平均；只列变化超过 0.3 的格子；— = 没有能分开的 series"))
rows = [[Z("cell (detector ← LED)", "格子（探测器 ← LED）")] + [Z("period %d", "第 %d 段") % e["epoch"] for e in epochs]]
for c in step_cells:
    rows.append(["%s  %s ← %s" % (c["id"], c["det"], ledname(c["led"]))] +
                ["—" if m is None else "%.2f" % m for m in ep_cells(c["id"])])
table(s, rows, L, T, W, Inches(0.28) * len(rows), col_w=[Inches(2.7)] + [Inches(1.6)] * len(epochs), size=10)

s = new(Z("Backup: which way each LED shines", "备用：每个 LED 照向哪边"), Z("trigger fraction of the LED's own detector, the detector below and the detector above", "LED 自己的探测器、编号小一号、编号大一号的探测器的触发比例"))
rows = [["LED", Z("phase", "段"), Z("own", "自己"), Z("number − 1", "编号 − 1"), Z("number + 1", "编号 + 1")]]
for r in leds:
    rows.append([ledname(r["led"]), r["phase"][-1], "%.2f" % r["own"], "%.2f" % r["prev"] if r["prev"] >= 0.005 else "—",
                 "%.2f" % r["next"] if r["next"] >= 0.005 else "—"])
half = (len(rows) + 1) // 2
cw = [Inches(1.3), Inches(0.8), Inches(0.9), Inches(1.2), Inches(1.2)]
table(s, rows[:half], L, T, Inches(5.4), Inches(0.3) * half, col_w=cw, size=10)
table(s, [rows[0]] + rows[half:], Inches(6.85), T, Inches(5.4), Inches(0.3) * (len(rows) - half + 1), col_w=cw, size=10)

s = new(Z("Backup: amplitude vs time, every channel", "备用：幅度随时间，每个通道"), fig="amplitude_vs_time.png")
if s:
    pic(s, "amplitude_vs_time.png", L, T, W, Inches(6.1))
s = new(Z("Backup: trigger fraction vs time", "备用：触发比例随时间"), fig="trigger_fraction.png")
if s:
    pic(s, "trigger_fraction.png", L, T, W, Inches(6.1))

s = new(Z("Backup: how a trigger is assigned to an LED", "备用：怎么把一次触发对应到 LED"))
lines(s, [Z("Per run and detector: histogram of TriggerTime mod 1 s (0.5 ms bins) → 1 Hz peaks (≥ 20 triggers); each peak keeps its own centre and width.", "每个 run、每个探测器：TriggerTime mod 1 s 的直方图（0.5 ms 一格）→ 1 Hz 的峰（≥ 20 个触发）；每个峰有自己的中心和宽度。"),
          Z("The 3 s pause = largest gap between LED triggers in the middle of the LED period → phase 1 / phase 2; the LED period is where triggers repeat at 1 Hz.", "3 s 的停顿 = LED 时段中间最大的空隙 → 分出第一段 / 第二段；LED 时段就是触发以 1 Hz 重复的那一段。"),
          Z("Peaks of different detectors are one flash group when their centres are within 0.2 ms (measured: %d … +%d µs between the LED's own detector and a neighbour).", "不同探测器的峰，中心相差不到 0.2 ms 就算同一个闪光组（实测：LED 自己的探测器和邻居之间相差 %d … +%d µs）。") % (off_lo, off_hi),
          Z("Z20's LEDs flash with a ±0.7 ms jitter: Z20 and the neighbours that see them all show the same wide peak (tolerance 0.3 × the width there).", "Z20 的 LED 闪光时刻有 ±0.7 ms 的抖动：Z20 和看到它的邻居都是同样的宽峰（那里的容差取 0.3 × 宽度）。"),
          Z("LED of a group: the LED of a member detector whose LED is on, or the LED a member stands in for when the owner does not trigger (Z1 LED4 → Z2, Z5 LED3 → Z6, Z13 LED5 → Z14, Z18 LED1 → Z17, Z17 LED0 → Z16, Z9 LED4 → Z10; inferred: Z22 LED0 → Z21, Z11 LED0 → Z10).", "一个组是哪个 LED：组里某个探测器自己开着的 LED；或者主人不触发时由邻居代表的 LED（Z1 LED4 → Z2，Z5 LED3 → Z6，Z13 LED5 → Z14，Z18 LED1 → Z17，Z17 LED0 → Z16，Z9 LED4 → Z10；推断的：Z22 LED0 → Z21，Z11 LED0 → Z10）。"),
          Z("An LED is required in a group when it has no other group. One required LED → the group is that LED; two → not separable (%d groups, left out; %d LED-series are grey in the maps).", "一个 LED 如果没有别的组可去，它在这个组里就是必需的。一个必需 LED → 这个组就是它；两个 → 分不开（%d 个组，不用；图上有 %d 个“LED × series”是灰色）。") % (n_amb, st["ambiguous_led_series"]),
          Z("A second peak of the same LED within 1 ms is the same flash; further away it is a re-trigger (Z1, 13 ms, %d series).", "同一个 LED 在 1 ms 内的第二个峰算同一次闪光；更远的是重复触发（Z1，13 ms，%d 个 series）。") % n_ret,
          Z("Pulse cuts (Part 2): baseline, SNR ≥ 8, rise found, no glitch, not bipolar, on the despiked trace (11-sample median).", "脉冲的筛选（第二部分）：基线、信噪比 ≥ 8、找到上升沿、不是 glitch、不是双极；都在去尖峰（11 点中值）的波形上。")],
      L, T, W, Inches(5.9), size=13)

for c in cells:
    s = new(Z("Backup %s: %s ← %s (%s, %s of the flashes)", "备用 %s：%s ← %s（%s，%s 的闪光）") % (c["id"], c["det"], ledname(c["led"]), c["phase"].replace("phase", "phase "), pct(c["fraction"])),
            fig="cell_%s.png" % c["id"])
    if s:
        pic(s, "cell_%s.png" % c["id"], L, T, W, Inches(6.1))

prs.save(PPTX)
print("wrote %s: %d slides (%d main)" % (PPTX, n_slide, n_main))

# ───────────────────────────────────────────────────────────────── speaker script
if ZH:              # the Chinese deck is for reading; the speaker script comes from the English build
    sys.exit(0)
main = [x for x in speech if x[2] > 0]
total = sum(x[2] for x in main)
out = ["# Speaker Script / 演讲稿 — LED runs in SNOLAB Run 7", "",
       "约 %d 分钟，%d 页正片 + backup。每页先中文、后英文，意思一样，**英文可以直接照着念**。全部是短句。斜体是给自己的提示，不用念。"
       % (round(total / 60.0), len(main)), "",
       "一句话主线：**哪个 LED → 稳不稳（幅度、触发）→ 模板和例子脉冲。**",
       "时间（秒）：" + " · ".join("%d %s %d" % (n, re.sub(r"^Part \d — ", "", t_)[:20], sec) for n, t_, sec, _, _, _ in main) +
       " → 约 %d 秒。" % total, "", "---", ""]
for n, t_, sec, hint, zh, en in main:
    out += ["## Slide %d — %s（约 %d 秒）" % (n, t_, sec), ""]
    if hint:
        out += ["*提示：%s*" % hint, ""]
    out += ["**中文**：" + zh, "", "**English**: " + en, "", "", "---", ""]
out += ["## 可能被问的问题 / Likely questions（回答一两句就够）", "",
        "**Q1. 为什么看不到更远的探测器？/ Why no detector further away?**",
        "中文：我们只读出触发的探测器。光如果到了，但低于阈值，就看不到。所以图是下限。",
        "English: Only the triggering detector is read out. If light arrives but stays below threshold, we cannot see it. So the plot is a lower limit.", "",
        "**Q2. 两个 LED 同时闪怎么办？/ What if two LEDs flash at the same time?**",
        "中文：LED 是一个接一个打开的，所以有时两个 LED 的闪光时刻差不到 0.2 毫秒。这时只靠时间分不开，我们就不用这一组。一共 %d 组。" % n_amb,
        "English: The LEDs are switched on one after the other, so sometimes two of them flash within 0.2 milliseconds. Time alone cannot separate them, so we do not use that group. There are %d such groups." % n_amb, "",
        "**Q3. 中值滤波会不会改变脉冲形状？/ Does the median filter change the pulse shape?**",
        "中文：基本不会。它只去掉比 18 微秒窄的尖峰。声子脉冲的上升比这慢，峰值和上升时间都不变。",
        "English: Hardly. It removes only spikes narrower than 18 microseconds. The phonon rise is slower than that, so the peak and the rise time stay the same.", "",
        "**Q4. Z20 那次是 LED 还是探测器？/ Was the Z20 drop the LED or the detector?**",
        "中文：像是 LED。Z19 看 Z20 的 LED 也变暗了，但 Z19 看自己的 LED 是正常的。原因还不知道，要查那几个小时的记录。",
        "English: It looks like the LED. Z19 also saw less of Z20's light, while Z19 with its own LED was normal. We do not know the cause yet; we need the logs of those hours.", "",
        "**Q5. 触发阈值是谁改的？/ Who changed the trigger thresholds?**",
        "中文：我不知道。我只看到每个 run 开始时数据库里的阈值，这一周有 %d 种设置。要问当时值班的人。" % len(epochs),
        "English: I do not know. I only see the thresholds in the ODB at the start of each run; there are %d settings during the week. We should ask the people on shift." % len(epochs), "",
        "**Q6. 0918 脚本有什么不同？/ What changed with the 0918 script?**",
        "中文：LED 的设置完全一样。它会关掉 Z17 的一级触发。但数据库里 Z17 的触发一直是开的，Z17 也一直在触发。",
        "English: The LED settings are identical. It should switch off Z17's L1 trigger. But the ODB shows Z17's trigger on in every run, and Z17 keeps triggering.", "",
        "**Q7. 幅度怎么算的？/ How is the amplitude defined?**",
        "中文：先去掉尖峰，减基线，取最大值，单位 ADC。每个 series 取中位数，再除以所有 series 的中位数。",
        "English: Remove the spikes, subtract the baseline, take the maximum, in ADC. Then the median per series, divided by the median over all series.", "",
        "**Q8. 为什么说每组 6 个？/ Why groups of six?**",
        "中文：这是从数据看出来的：没有一对跨过 6 和 7、12 和 13、18 和 19。数据库里读出板的数目也是这样分的。",
        "English: That is what the data show: no pair crosses 6 and 7, 12 and 13, or 18 and 19. The number of readout boards in the ODB splits the same way.", ""]
open(SPEECH, "w", encoding="utf-8").write("\n".join(out))
print("wrote %s (%d s = %.1f min, %d main slides)" % (SPEECH, total, total / 60.0, len(main)))
