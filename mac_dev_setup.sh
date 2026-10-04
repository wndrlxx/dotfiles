#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"

# Check if the command line tools are already installed
if xcode-select -p &>/dev/null; then
  echo "Xcode Command Line Tools are already installed."
else
  echo "Installing Xcode Command Line Tools..."
  xcode-select --install

  until xcode-select -p >/dev/null 2>&1; do
    sleep 2
  done
fi

if command -v brew &>/dev/null; then
  echo "Homebrew already installed."
else
  echo "Installing Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  else
    echo "Homebrew installation did not provide a brew executable." >&2
    exit 1
  fi
fi

# move windows by holding ctrl + cmd and dragging any part of the window
defaults write -g NSWindowShouldDragOnGesture -bool true

# disable windows opening animations
defaults write -g NSAutomaticWindowAnimationsEnabled -bool false

"$SCRIPT_DIR/brew_install.sh"

"$SCRIPT_DIR/mise_install.sh"

"$SCRIPT_DIR/load_dotfiles.sh"

exit 0
