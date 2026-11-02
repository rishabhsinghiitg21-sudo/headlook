#!/bin/sh
# One-shot: launch Art of Rally (with BepInEx head-look) + the head tracker together.
# Run it from Terminal so the tracker inherits Terminal's camera permission.
# The tracker auto-stops (camera off) ~2s after the game quits.
# Set ART_OF_RALLY_DIR if your game is not in the default location (see launch-artofrally.sh).
cd "$(dirname "$0")" || exit 1

# 1) start the game with BepInEx (keeps running in the background)
nohup ./launch-artofrally.sh >/tmp/aor.log 2>&1 &

# 2) give the game a moment to come up, then start the tracker (foreground here so the
#    Terminal window reflects its lifetime; it self-quits when the game closes)
sleep 12
exec ./.venv/bin/python -m headlook.ratrack
