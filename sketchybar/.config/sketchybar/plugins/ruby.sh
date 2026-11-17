#!/bin/sh
# Resolve the user's mise Ruby without requiring interactive shell activation.
mise_bin="$HOME/.local/bin/mise"
if [ ! -x "$mise_bin" ]; then
  mise_bin=$(command -v mise) || {
    echo 'SketchyBar: mise not found; install mise and configure Ruby.' >&2
    exit 127
  }
fi

# Use the user's configuration, independent of the service's working directory.
ruby_bin=$("$mise_bin" -C "$HOME" which ruby) || exit "$?"
if [ ! -x "$ruby_bin" ]; then
  echo 'SketchyBar: mise did not resolve an executable Ruby; run mise install ruby.' >&2
  exit 127
fi
exec "$ruby_bin" "$@"
