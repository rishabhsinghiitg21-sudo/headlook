#!/bin/sh
# Launch Art of Rally (Epic) with BepInEx + the head-look plugin.
# Replicates run_bepinex.sh's doorstop env vars but launches the binary directly,
# avoiding the script's ".app"-in-path requirement (the Epic bundle is "artofrally").
# Where the game lives. Override with:  ART_OF_RALLY_DIR="/path/to/artofrally" ./launch-artofrally.sh
# (default is the Epic Games Store location on macOS)
GAME="${ART_OF_RALLY_DIR:-/Users/Shared/Epic Games/artofrally}"

export DOORSTOP_ENABLED=1
export DOORSTOP_TARGET_ASSEMBLY="$GAME/BepInEx/core/BepInEx.Preloader.dll"
export DOORSTOP_IGNORE_DISABLED_ENV=0
export DOORSTOP_MONO_DEBUG_ENABLED=0
export DOORSTOP_MONO_DEBUG_ADDRESS="127.0.0.1:10000"
export DOORSTOP_MONO_DEBUG_SUSPEND=0
export DOORSTOP_MONO_DLL_SEARCH_PATH_OVERRIDE=""
export DYLD_LIBRARY_PATH="$GAME:$DYLD_LIBRARY_PATH"
export DYLD_INSERT_LIBRARIES="$GAME/libdoorstop.dylib"

exec "$GAME/Contents/MacOS/art of rally" "$@"
