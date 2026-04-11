#!/bin/bash

# Check if the command line tools are already installed
if xcode-select -p &>/dev/null; then
  echo "Xcode Command Line Tools are already installed."
else
  echo "Installing Xcode Command Line Tools..."
  xcode-select --install

  until command -v xcrun >/dev/null 2>&1; do
    sleep 2
  done
fi

if command -v brew &>/dev/null; then
  echo "Homebrew already installed."
else
  echo "Installing Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  until command -v brew >/dev/null 2>&1; do
    sleep 2
  done
fi

# move windows by holding ctrl + cmd and dragging any part of the window
defaults write -g NSWindowShouldDragOnGesture -bool true

# disable windows opening animations
defaults write -g NSAutomaticWindowAnimationsEnabled -bool false

./brew_install.sh

./mise_install.sh

./load_dotfiles.sh

exit 0
