#!/bin/bash

# clone dotfiles
mkdir -p ~/git/dotfiles/
cd "$HOME/git/dotfiles" || {
  echo "Directory $HOME/git/dotfiles/ not found!"
  exit 1
}
git clone https://github.com/wndrlxx/dotfiles.git || {
  echo "Failed to clone dotfiles!"
  exit 1
}

# run GNU Stow
if [[ "$OSTYPE" == "darwin"* ]]; then
  stow -t ~ aerospace
  stow -t ~ karabiner
  stow -t ~ sketchybar
else
  stow -t ~ run-or-raise
fi

stow -t ~ bat
stow -t ~ btop
stow -t ~ gh
stow -t ~ git
stow -t ~ ghostty
stow -t ~ herdr
stow -t ~ nvim
stow -t ~ pi
stow -t ~ starship
stow -t ~ zsh

source "$HOME/.config/zsh/.zshrc"
