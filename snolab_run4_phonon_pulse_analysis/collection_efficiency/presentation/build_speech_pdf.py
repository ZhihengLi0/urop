#!/usr/bin/env python3
"""Render speech_script.md into a presenter-friendly HTML, then PDF via headless
Chromium.

Layout: one slide's block never splits across a page; the English block is
protected the same way. Bold English (the ** ** in the markdown) is what is said
while pointing at the figure; it is highlighted in dark blue so it can be found
at a glance. Italic lines are private reminders.

Usage:
    python3 build_speech_pdf.py speech_script.md speech_script.html
    chromium-browser --headless --no-sandbox --print-to-pdf=speech_script.pdf speech_script.html
"""
import html
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().split("\n")


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)", r"<i class='hint'>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


out = []
card = False
en = False


def close_card():
    global card, en
    if en:
        out.append("</div>")
        en = False
    if card:
        out.append("</section>")
        card = False


for ln in lines:
    if ln.startswith("# "):
        out.append(f"<h1>{inline(ln[2:])}</h1>")
    elif ln.startswith("## "):
        close_card()
        out.append(f"<section class='card'><h2>{inline(ln[3:])}</h2>")
        card = True
    elif ln.strip() == "---":
        close_card()
    elif ln.startswith("**English**"):
        out.append(f"<div class='en'><p>{inline(ln)}</p>")
        en = True
    elif ln.startswith("**中文**"):
        out.append(f"<p class='zh'>{inline(ln)}</p>")
    elif ln.startswith("- "):
        out.append(f"<p class='li'>• {inline(ln[2:])}</p>")
    elif ln.strip():
        # the notes above the first slide are for the speaker only: set small
        cls = "" if card or any("class='card'" in o for o in out) else " class='intro'"
        out.append(f"<p{cls}>{inline(ln)}</p>")
close_card()

CSS = """
@page { size: A4; margin: 14mm 13mm; }
body { font-family: 'Droid Sans', 'DroidSansFallback', 'Noto Sans CJK SC', sans-serif;
       font-size: 12.5pt; line-height: 1.5; color: #222; max-width: 190mm; margin: 0 auto; }
h1 { font-size: 16pt; color: #1F3864; margin: 0 0 4pt; }
h2 { font-size: 14pt; color: #1F3864; margin: 0 0 6pt; border-bottom: 1.5px solid #1F3864; padding-bottom: 3pt; }
.card { break-inside: avoid; page-break-inside: avoid; margin: 0 0 10pt; padding: 6pt 8pt;
        border: 1px solid #D0D5DD; border-radius: 6px; }
.en { break-inside: avoid; page-break-inside: avoid; background: #F7F9FC; padding: 4pt 8pt; border-radius: 4px; }
.en b { color: #1F3864; background: #E4ECF7; }
.zh b { color: #1F3864; }
p { margin: 4pt 0; }
.hint, i.hint { color: #888; }
code { font-family: monospace; font-size: 11pt; background: #EEE; padding: 0 3px; }
.li { margin-left: 10pt; }
.intro { font-size: 9.5pt; line-height: 1.3; margin: 2pt 0; color: #444; }
"""
open(dst, "w", encoding="utf-8").write(
    "<!doctype html><html><head><meta charset='utf-8'><title>speech script</title>"
    f"<style>{CSS}</style></head><body>" + "\n".join(out) + "</body></html>")
print("wrote", dst)
