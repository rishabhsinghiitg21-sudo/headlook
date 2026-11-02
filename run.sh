#!/usr/bin/env bash
# Run headlook from the repo root using the venv that setup.sh created.
#   ./run.sh --mode preview     # webcam + tracking overlay, no injection
#   ./run.sh --mode run         # head -> synthetic mouse-look (experimental)
#   ./run.sh --mode run --output fgfs   # FlightGear (experimental)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { echo "No .venv yet. Run ./setup.sh first."; exit 1; }
source .venv/bin/activate
exec python -m headlook "$@"
