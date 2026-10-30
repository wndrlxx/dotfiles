#!/usr/bin/env bash

workspace="${FOCUSED_WORKSPACE:-$(aerospace list-workspaces --focused)}"

if [ -n "$workspace" ]; then
    case "$workspace" in
        1) label=N ;;
        2) label=M ;;
        3) label=U ;;
        4) label=I ;;
        5) label=O ;;
        6) label=P ;;
        *) label="$workspace" ;;
    esac
    sketchybar --set "$NAME" label="$label"
fi
