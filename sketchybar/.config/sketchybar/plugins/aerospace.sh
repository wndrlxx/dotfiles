#!/usr/bin/env bash

workspace="${FOCUSED_WORKSPACE:-$(aerospace list-workspaces --focused)}"

if [ -n "$workspace" ]; then
  case "$workspace" in
  1) label=, ;;
  2) label=. ;;
  3) label=U ;;
  4) label=I ;;
  5) label=O ;;
  6) label=P ;;
  7) label=N ;;
  8) label=M ;;
  *) label="$workspace" ;;
  esac
  sketchybar --set "$NAME" label="$label"
fi
