#!/bin/bash
set -euo pipefail

# NOTE: mise replaces fnm, nvm, pyenv, and rbenv
curl -fsSL https://mise.run | sh
export PATH="$HOME/.local/bin:$PATH"

mise use -g atuin@latest \
  delta@latest \
  fastfetch@latest \
  fzf@latest \
  go@latest \
  herdr@latest \
  jless@latest \
  lazygit@latest \
  neovim@latest \
  node@latest \
  pipx@latest \
  pnpm@latest \
  ripgrep@latest \
  ruby@latest \
  rust@latest \
  starship@latest \
  terraform@latest \
  yazi@latest \
  yt-dlp@latest
