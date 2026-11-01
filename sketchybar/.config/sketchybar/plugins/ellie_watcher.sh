#!/bin/bash
set -euo pipefail

plugin_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cache_dir="${TMPDIR:-/tmp}/sketchybar-ellie-$(id -u)"
if [ -L "$cache_dir" ]; then exit 1; fi
mkdir -p -m 700 "$cache_dir"
if [ ! -O "$cache_dir" ]; then exit 1; fi
chmod 700 "$cache_dir"

source_file="$plugin_dir/ellie_watcher.swift"
binary="$cache_dir/ellie-watcher"
if [ ! -x "$binary" ] || [ "$source_file" -nt "$binary" ]; then
  # Build once, not at every reload. Keep generated files out of the dotfiles.
  build_file=$(mktemp "$cache_dir/ellie-watcher-build.XXXXXX")
  trap 'rm -f "$build_file"' EXIT
  /usr/bin/swiftc -O -module-cache-path "$cache_dir/swift-modules" "$source_file" -o "$build_file"
  chmod 700 "$build_file"
  mv -f "$build_file" "$binary"
  trap - EXIT
fi

bar_pid="${1:-$(pgrep -o -u "$(id -u)" -x sketchybar)}"
bar_executable=$(command -v sketchybar)
exec "$binary" "$cache_dir/app.json" "$bar_pid" "$bar_executable" com.electron.ellie
