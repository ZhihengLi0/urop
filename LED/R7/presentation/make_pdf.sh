#!/bin/bash
# PDF export of the deck and the speaker script on MSI (same as didv/presentation/make_pdf.sh): the LibreOffice
# AppImage fails inside the group-owned project tree, so it runs from $HOME with absolute paths.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PPTX=${1:-$HERE/SNOLAB_R7_LED_runs_20261125.pptx}
module load libreoffice/12.05.22
cd "$HOME"
libreoffice --headless --convert-to pdf --outdir "$HERE" "$PPTX"
cd "$HERE"
python3 build_speech_pdf.py speech_script.md speech_script.html
python3 build_speech_pdf.py speech_script.md speech_script_en.html --en
chromium-browser --headless --no-sandbox --no-pdf-header-footer --print-to-pdf-no-header --print-to-pdf="$HERE/speech_script.pdf" "$HERE/speech_script.html" 2>/dev/null
chromium-browser --headless --no-sandbox --no-pdf-header-footer --print-to-pdf-no-header --print-to-pdf="$HERE/speech_script_en.pdf" "$HERE/speech_script_en.html" 2>/dev/null
ls -la "$HERE"/*.pdf
