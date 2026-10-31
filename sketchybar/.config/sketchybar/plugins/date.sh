#!/bin/sh

# The $NAME variable is passed from sketchybar and holds the name of
# the item invoking this script:
# https://felixkratz.github.io/SketchyBar/config/events#events-and-scripting

case "$NAME" in
  date.notch) FORMAT="%a" ;;
  *) FORMAT="%A" ;;
esac

sketchybar --set "$NAME" label="$(/bin/date +"$FORMAT")"
