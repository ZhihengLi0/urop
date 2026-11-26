#!/usr/bin/env python3
"""Render speech_script.md into a presenter-friendly HTML, then PDF via headless
Chromium.  Same layout as the collection-efficiency talk: one slide's block
never splits across a page; bold English is what is said while pointing at the
figure; italic lines are private reminders.

    python3 build_speech_pdf.py speech_script.md speech_script.html          # bilingual (local)
    python3 build_speech_pdf.py speech_script.md speech_script_en.html --en  # English only (versioned)
    chromium-browser --headless --no-sandbox --print-to-pdf=<pdf> <html>
"""
import html
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
EN_ONLY = "--en" in sys.argv
lines = open(src, encoding="utf-8").read().split("\n")
CJK = re.compile(r"[一-鿿]")


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)", r"<i class='hint'>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def en_part(s):
    """for --en: drop Chinese lines; in mixed 'Chinese / English' lines keep the English side"""
    if not CJK.search(s):
        return s
    # 'Chinese / English' pairs: the slash follows a Chinese question mark or a space
    parts = re.split(r"(?<=[？?。])\s*/\s*|\s/\s", s)
    if len(parts) > 1:
        kept = [p for p in parts if not CJK.search(p)]
        if kept:
            m = re.match(r"(\*\*[QB]\d+\.?\s*)", parts[0])      # keep the '**Q1. ' prefix
            return (m.group(1) if m else "") + " / ".join(kept)
    return None


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
    if EN_ONLY:
        if ln.startswith("## "):
            ln = "## " + re.sub(r"（约 (\d+) 秒）", r"(about \1 s)", ln[3:])
            ln = ln.replace("## 可能被问的问题 / Likely questions（回答一两句就够）", "## Likely questions (one or two sentences each)")
            ln = ln.replace("## Backup（仅备查，不占正片时间）", "## Backup (for reference only)")
            if CJK.search(ln):
                ln = None
        elif ln.startswith("# "):
            ln = "# Speaker Script — LED runs in SNOLAB Run 7"
        elif ln.startswith("English: "):
            ln = ln[len("English: "):]
        elif ln.strip() and ln.strip() != "---":
            ln = en_part(ln)
        if ln is None:
            continue
        if ln.startswith("**English**: "):
            ln = ln[len("**English**: "):]
    if ln.startswith("# "):
        out.append(f"<h1>{inline(ln[2:])}</h1>")
    elif ln.startswith("## "):
        close_card()
        out.append(f"<section class='card'><h2>{inline(ln[3:])}</h2>")
        card = True
    elif ln.strip() == "---":
        close_card()
    elif re.match(r"\*\*Q\d+\.", ln):
        close_card()                                   # one card per question
        out.append(f"<section class='card'><p>{inline(ln)}</p>")
        card = True
    elif ln.startswith("**English**"):
        out.append(f"<div class='en'><p>{inline(ln)}</p>")
        en = True
    elif ln.startswith("**中文**"):
        out.append(f"<p class='zh'>{inline(ln)}</p>")
    elif ln.startswith("- "):
        out.append(f"<p class='li'>• {inline(ln[2:])}</p>")
    elif ln.strip():
        cls = "" if card or any("class='card'" in o for o in out) else " class='intro'"
        if EN_ONLY and card and not en and not ln.startswith("**"):
            out.append(f"<div class='en'><p>{inline(ln)}</p>")
            en = True
        else:
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
print("wrote", dst, "(English only)" if EN_ONLY else "(bilingual)")
