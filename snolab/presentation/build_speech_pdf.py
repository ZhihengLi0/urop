#!/usr/bin/env python3
"""Render speech_script.md into a presenter-friendly HTML (then PDF via a
headless browser).

Layout rules:
  * one slide's block never splits across a page (break-inside: avoid); the
    page packs 2-3 slide cards, pushing a card that doesn't fit to the next
    page. The English block is additionally protected so it is never split.
  * readable font sizes.
  * the English sentences you say WHILE POINTING AT THE FIGURE are highlighted
    in one dark-blue colour (with a soft background). Say the highlighted part
    looking at the screen, then drop back to the black text and keep reading.
    The highlighted phrases per slide are listed in POINT below and must match
    the English in speech_script.md verbatim (including ** ** markers); if a
    phrase is edited in the md, update it here too or the highlight silently
    drops.

Usage:  python3 build_speech_pdf.py speech_script.md out.html
        then: chromium-browser --headless --print-to-pdf=out.pdf out.html
"""
import re
import html
import sys

# English phrases (verbatim from speech_script.md) said while pointing at the
# on-screen figure, keyed by slide number.
POINT = {
    3: [
        "What you see here are the PTOFamps spectra of all thirteen detectors",
        "The red line in each panel is the K-line position marked by Professor Saab's analysis",
        "Now look at the spectra: on a quiet detector like Z7, the K-line peak is well separated from the noise peak. But on the weaker detectors, the red line sits right inside the noise population",
    ],
    4: [
        "In these grids, each row is one event and each column is one channel — blue is the filtered trace, red is the fit.",
        "the left block is noise triggers, the right block is true K-line events",
    ],
    6: [
        "The dotted vertical line is the common pretrigger everything is aligned to.",
        "this fan plot shows **every** fitted event on this channel, 2203 curves",
    ],
    7: [
        "on the right, the fits that fit_ok removes are drawn in red — negative shapes, clearly non-physical",
    ],
    8: [
        "In this plot the two populations are far apart and the valley is obvious.",
    ],
    9: [
        "on the left all fit_ok curves, all 2008 of them drawn, no sampling; on the right the 1931 that survive the NRMSE cut — one very tight, consistent shape family remains",
    ],
    10: [
        "On the left are the **raw** traces of the rejected events. As you can see, there is simply no pulse there",
        "this figure has three layers: the gray-blue underneath is the aligned measured traces, green on top is the fitted curves that **pass** the cut, and red is the ones **removed**; the top-right corner shows each population's median NRMSE and its event count.",
        "The green ones are fast and consistent, bundled together; the red ones scatter everywhere",
    ],
    11: [
        "Each row is one event, and in every column except PDS2 you see a clean, fast pulse; only in the PDS2 column is there a large low-frequency swing riding on top of the trace",
        "the left one is a normal channel, PAS1 — almost every event sits in one narrow peak at about 0.25 milliseconds, and there's basically nothing past one millisecond; the right one is PDS2 — a broad tail that stretches all the way out to five or six milliseconds",
    ],
    12: [
        "On the screen, the blue **bundle** is the fitted curves that go into the average — that's the input, not the template.",
        "The plot at the bottom draws the two averages on top of each other: the solid red line is the NRMSE-weighted mean, the delivered 1x1 template; the dashed navy line is the plain unweighted mean of the clean PCA input curves, which is exactly nxm0.",
    ],
    13: [
        'the black curve, nxm-zero, is the average shape; the four colored ones are the four main "directions of deformation" in the data',
    ],
}

TS, TE = "\x01PS\x01", "\x01PE\x01"


def inline(t, slide=None):
    if slide in POINT:
        for ph in POINT[slide]:
            if ph in t:
                t = t.replace(ph, TS + ph + TE, 1)
    t = html.escape(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', t)
    t = t.replace(TS, '<span class="point">').replace(TE, '</span>')
    return t


def is_table_sep(line):
    s = line.strip()
    return bool(s) and set(s) <= set('|:- ') and '-' in s


def main(src, dst):
    lines = open(src, encoding='utf-8').read().split('\n')
    out = []
    i, n = 0, len(lines)
    cur_slide = None      # int for "Slide N", 0 for backup/other cards
    ref_mode = False      # after the Q&A header: render generically
    card = None           # dict(title, en, zh, notes) buffered so EN prints first

    def close_card():
        nonlocal card
        if card is not None:
            out.append('<div class="slide">')
            out.append(f'<div class="stitle">{card["title"]}</div>')
            if card["en"]:
                out.append(card["en"])
            if card["zh"]:
                out.append(card["zh"])
            out.extend(card["notes"])
            out.append('</div>')
            card = None

    # header block (title + intro + legend)
    out.append('<h1>Speaker Script — SNOLAB R4 Phonon Pulse Templates</h1>')
    out.append('<div class="legend">'
               '<b>怎么用这份稿子：</b>黑字照读；'
               '<span class="point">蓝色高亮</span>'
               ' = 抬头看 PPT、对着图指着说的部分，说完回到黑字继续念。'
               '每张 slide 整块不跨页。</div>')

    i = 5  # skip the original title + intro lines (regenerated above)
    while i < n:
        line = lines[i]
        s = line.strip()

        m = re.match(r'^## (Slide (\d+).*)$', s)
        mb = re.match(r'^## (Backup.*)$', s)
        mq = re.match(r'^## (可能被问.*|术语自查表.*)$', s)

        if mq:
            close_card()
            ref_mode = True
            out.append(f'<h2 class="sec">{inline(mq.group(1))}</h2>')
            i += 1
            continue

        if not ref_mode and (m or mb):
            close_card()
            cur_slide = int(m.group(2)) if m else 0
            title = m.group(1) if m else mb.group(1)
            card = {"title": inline(title), "en": None, "zh": None, "notes": []}
            i += 1
            continue

        if s == '---':
            close_card()
            i += 1
            continue

        if s == '':
            i += 1
            continue

        # reference tail: tables + generic paragraphs
        if ref_mode:
            if '|' in line and i + 1 < n and is_table_sep(lines[i + 1]):
                header = [c.strip() for c in line.strip().strip('|').split('|')]
                out.append('<table><thead><tr>' +
                           ''.join(f'<th>{inline(c)}</th>' for c in header) +
                           '</tr></thead><tbody>')
                i += 2
                while i < n and '|' in lines[i] and lines[i].strip():
                    cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                    out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells) + '</tr>')
                    i += 1
                out.append('</tbody></table>')
                continue
            if s.startswith('> '):
                out.append(f'<blockquote>{inline(s[2:])}</blockquote>')
                i += 1
                continue
            if s.startswith('**Q'):
                out.append(f'<div class="qa"><div class="q">{inline(s)}</div>')
                i += 1
                # gather until blank-then-next-Q or blank line
                while i < n and lines[i].strip() and not lines[i].strip().startswith('**Q'):
                    out.append(f'<p>{inline(lines[i].strip())}</p>')
                    i += 1
                out.append('</div>')
                continue
            out.append(f'<p>{inline(s)}</p>')
            i += 1
            continue

        # inside a slide card: English printed first, then 中文, then notes
        if card is not None and s.startswith('**中文**：'):
            body = s[len('**中文**：'):]
            card["zh"] = f'<div class="zh"><span class="lbl">中文</span>{inline(body, cur_slide)}</div>'
            i += 1
            continue
        if card is not None and s.startswith('**English**:'):
            body = s[len('**English**:'):].lstrip()
            card["en"] = f'<div class="en"><span class="lbl">EN</span>{inline(body, cur_slide)}</div>'
            i += 1
            continue
        # italic self-note or other line inside a card
        note = f'<p class="note">{inline(s, cur_slide)}</p>'
        if card is not None:
            card["notes"].append(note)
        else:
            out.append(note)
        i += 1

    close_card()

    css = """
    @page { size: A4; margin: 9mm 10mm; }
    body { font-family: 'Droid Sans','DroidSansFallback',sans-serif; color:#111; }
    h1 { font-size: 13pt; margin: 0 0 5px; }
    .legend { font-size: 8.5pt; background:#f4f7fa; border:1px solid #d6e0ea;
              border-radius:5px; padding:4px 8px; margin:0 0 8px; line-height:1.4; }
    .sec { font-size: 11pt; margin: 11px 0 5px; border-bottom:2px solid #333; padding-bottom:3px; }
    .slide { break-inside: avoid; page-break-inside: avoid;
             border:1.5px solid #8a8a8a; border-radius:5px;
             padding:6px 11px; margin:0 0 9px; }
    .stitle { font-size: 11pt; font-weight:700; color:#c01818; margin-bottom:2px; }
    .zh { font-size: 10pt; line-height:1.4; margin:2px 0; color:#444; }
    .en { font-size: 11.5pt; line-height:1.46; margin:2px 0 1px; color:#111;
          break-inside: avoid; page-break-inside: avoid; }
    .lbl { display:inline-block; font-size:7pt; font-weight:700; color:#fff;
           background:#7a8a99; border-radius:3px; padding:0 4px; margin-right:5px;
           vertical-align:1.5px; }
    .en .lbl { background:#2f6f4f; }
    .point { color:#0b3d66; background:#e4eff9; border-radius:2px;
             padding:0 2px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
    strong { color:#111; font-weight:700; }
    em { color:#666; }
    .note { font-size:8.5pt; color:#777; font-style:italic; margin:2px 0; }
    code { background:#f0f0f0; padding:0 3px; border-radius:3px; font-family:monospace; font-size:9pt; }
    .qa { break-inside: avoid; page-break-inside: avoid; border:1px solid #e3e3e3;
          border-radius:5px; padding:4px 8px; margin:0 0 5px; }
    .qa .q { font-weight:700; color:#204a34; font-size:9.5pt; margin-bottom:1px; }
    .qa p { font-size:9pt; line-height:1.38; margin:1px 0; }
    table { border-collapse:collapse; width:100%; margin:7px 0; font-size:8.5pt; }
    th,td { border:1px solid #ccc; padding:3px 6px; text-align:left; vertical-align:top; }
    th { background:#eee; }
    blockquote { background:#f7f7f7; border-left:4px solid #bbb; margin:6px 0;
                 padding:4px 8px; color:#555; font-size:8.5pt; }
    """
    doc = ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
           f'<style>{css}</style></head><body>' + '\n'.join(out) + '</body></html>')
    open(dst, 'w', encoding='utf-8').write(doc)
    print(f'wrote {dst} ({len(doc)} bytes)')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
