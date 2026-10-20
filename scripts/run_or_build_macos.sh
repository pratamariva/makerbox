#!/usr/bin/env bash
# Run MakerBox now, or build a standalone macOS .app.
#   ./scripts/run_or_build_macos.sh run     # launch the GUI
#   ./scripts/run_or_build_macos.sh build   # make dist/MakerBox.app
set -euo pipefail
cd "$(dirname "$0")/.."
# Apple's Command Line Tools Python ships a Tk that crashes on this macOS
# build; use Homebrew's Python (own Tcl/Tk) when present.
PY="/opt/homebrew/bin/python3.12"
[ -x "$PY" ] || PY="python3"
case "${1:-run}" in
  run)   "$PY" src/app.py ;;
  build) "$PY" -m pip install --user pyinstaller
         "$PY" -m PyInstaller --onefile --windowed --name MakerBox src/app.py
         echo "Done -> dist/MakerBox" ;;
  *) echo "usage: $0 [run|build]"; exit 1 ;;
esac
