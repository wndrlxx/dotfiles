#!/bin/bash

# Match macOS display IDs to SketchyBar's current arrangement IDs.
notched_displays=$(/usr/bin/osascript -l JavaScript <<'JAVASCRIPT'
ObjC.import("AppKit");
JSON.stringify(ObjC.unwrap($.NSScreen.screens)
  .filter(screen => screen.safeAreaInsets.top > 0)
  .map(screen => ObjC.unwrap(screen.deviceDescription.objectForKey("NSScreenNumber"))));
JAVASCRIPT
) || exit 1

displays=$(sketchybar --query displays) || exit 1
center_displays=$(jq -r --argjson notched "$notched_displays" '
  [.[] | select(.DirectDisplayID as $id | $notched | index($id) | not)
   | .["arrangement-id"]] | join(",")
' <<< "$displays") || exit 1
notch_displays=$(jq -r --argjson notched "$notched_displays" '
  [.[] | select(.DirectDisplayID as $id | $notched | index($id))
   | .["arrangement-id"]] | join(",")
' <<< "$displays") || exit 1

args=()
for item in weather date clock; do
  if [ -n "$center_displays" ]; then
    args+=(--set "$item" display="$center_displays" drawing=on)
  else
    args+=(--set "$item" drawing=off)
  fi
  if [ -n "$notch_displays" ]; then
    args+=(--set "$item.notch" display="$notch_displays" drawing=on)
  else
    args+=(--set "$item.notch" drawing=off)
  fi
done
sketchybar "${args[@]}"
