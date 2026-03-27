#!/bin/bash
CPU=$(top -l 2 -s 1 | grep -E "^CPU" | tail -1 | awk '{print $3}' | cut -d% -f1)
ROUNDED=$(printf '%.0f' "$CPU")

if [ "$ROUNDED" -gt 60 ]; then
  COLOR=0xFFFF0000
elif [ "$ROUNDED" -gt 30 ]; then
  COLOR=0xFFFFFF00
else
  COLOR=0xFFFFFFFF
fi

sketchybar --set cpu label="${ROUNDED}%" label.color=$COLOR
