#!/bin/bash

# add wezterm APT repo
curl -fsSL https://apt.fury.io/wez/gpg.key | sudo gpg --yes --dearmor -o /usr/share/keyrings/wezterm-fury.gpg
echo 'deb [signed-by=/usr/share/keyrings/wezterm-fury.gpg] https://apt.fury.io/wez/ * *' | sudo tee /etc/apt/sources.list.d/wezterm.list
sudo chmod 644 /usr/share/keyrings/wezterm-fury.gpg

sudo apt update
sudo apt install bat \
  btop \
  eza \
  ffmpeg \
  gh \
  git \
  imagemagick \
  jq \
  libsqlite3-dev \
  mitmproxy \
  sqlite3 \
  stow \
  thefuck \
  wezterm \
  wget \
  zoxide \
  zsh

# snaps
sudo snap install bitwarden
sudo snap install ghostty --classic
sudo snap install newsboat
