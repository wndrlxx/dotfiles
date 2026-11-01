#!/bin/bash
# Include both user and system CPU time in total utilization.
CPU=$(top -l 2 -s 1 -n 0 | awk '/^CPU usage:/ { cpu = $3 + $5 } END { print cpu }')
ROUNDED=$(printf '%.0f' "$CPU")

if awk -v cpu="$CPU" 'BEGIN { exit !(cpu >= 30) }'; then
  LABEL_DRAWING=on
else
  LABEL_DRAWING=off
fi

if [ "$ROUNDED" -ge 60 ]; then
  COLOR=0xFFFF0000 # red
elif [ "$ROUNDED" -ge 30 ]; then
  COLOR=0xFFFFFF00 # yellow
else
  COLOR=0xFFFFFFFF # white
fi

sketchybar --set cpu label="${ROUNDED}%" label.color=$COLOR label.drawing=$LABEL_DRAWING
