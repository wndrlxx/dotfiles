#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# run GNU Stow
if [[ "$OSTYPE" == "darwin"* ]]; then
  stow --ignore='\.DS_Store$' -t ~ aerospace
  stow --ignore='\.DS_Store$' -t ~ karabiner
  stow --ignore='\.DS_Store$' -t ~ sketchybar
  ghostty_ignore='linux\.conf$'
else
  stow --ignore='\.DS_Store$' -t ~ run-or-raise
  ghostty_ignore='macos\.conf$'
fi

# Unstow without platform exclusions to remove legacy folded and cross-platform links.
stow --delete --ignore='\.DS_Store$' -t "$HOME" ghostty
stow --ignore='\.DS_Store$' -t "$HOME" --no-folding --ignore="$ghostty_ignore" ghostty

stow --ignore='\.DS_Store$' -t ~ bat
stow --ignore='\.DS_Store$' -t ~ btop
stow --ignore='\.DS_Store$' -t ~ gh
stow --ignore='\.DS_Store$' -t ~ git
stow --ignore='\.DS_Store$' -t ~ herdr
stow --ignore='\.DS_Store$' -t ~ lazygit
stow --ignore='\.DS_Store$' -t ~ nvim
stow --ignore='\.DS_Store$' -t ~ pi
stow --ignore='\.DS_Store$' -t ~ starship
stow --ignore='\.DS_Store$' -t ~ zsh

echo "Dotfiles installed. Start a new Zsh session to load the shell configuration."
