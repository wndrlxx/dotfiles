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

brew install --cask nikitabobko/tap/aerospace &&
  brew install --cask antinote &&
  brew install --cask bitwarden &&
  brew install --cask google-chrome &&
  brew install --cask ghostty &&
  brew install --cask helium-browser &&
  brew install --cask karabiner-elements

brew tap FelixKratz/formulae
brew install sketchybar

brew install bat &&
  brew install btop &&
  brew install eza &&
  brew install ffmpeg &&
  brew install fzf &&
  brew install gh &&
  brew install imagemagick &&
  brew install jq &&
  brew install lazygit &&
  brew install mitmproxy &&
  brew install neofetch &&
  brew install nvm &&
  brew install pnpm &&
  brew install pyenv &&
  brew install sqlite &&
  brew install starship &&
  brew install stow &&
  brew install terraform &&
  brew install wget &&
  brew install yt-dlp &&
  brew install zoxide

brew doctor
# expect "Your system is ready to brew."

# TODO: clone dotfiles
# TODO: run stow with target

exit 0
