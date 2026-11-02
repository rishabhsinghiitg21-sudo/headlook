#!/usr/bin/env bash
# One-time setup: a local .venv, the Python dependencies, and the MediaPipe
# face model (about 3.7 MB). Needed for the Python app and the Art of Rally
# tracker. The browser sandbox needs none of this.
set -e
cd "$(dirname "$0")"

# Pick a Python MediaPipe supports (3.10-3.13 preferred), else fall back to python3.
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3 not found. Install it first (e.g. brew install python@3.13)."; exit 1; }
echo "Using $($PY --version) ($PY)"

[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

mkdir -p models
MODEL=models/face_landmarker.task
if [ ! -s "$MODEL" ]; then
  echo "Downloading the MediaPipe face model..."
  curl -fL -o "$MODEL" \
    https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
fi

echo
echo "Done. Try:  ./run.sh --mode preview"
