#!/bin/bash

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
  wget \
  zoxide \
  zsh

# snaps
sudo snap install bitwarden
sudo snap install ghostty --classic
sudo snap install newsboat
