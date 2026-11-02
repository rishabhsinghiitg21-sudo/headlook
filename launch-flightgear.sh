#!/usr/bin/env bash
# Launch FlightGear with the telnet property server enabled on port 5401 so
# headlook can drive the cockpit view. Any extra args are passed through to FG
# (e.g. --aircraft=c172p --airport=KSFO).
#
# First launch may take a while: FlightGear downloads its base scenery/aircraft.
# You can also just open FlightGear normally and add `--telnet=5401` in the
# launcher's Settings > Additional Settings box — this script is the shortcut.
exec /Applications/FlightGear.app/Contents/MacOS/FlightGear \
  --telnet=5401 \
  "$@"
