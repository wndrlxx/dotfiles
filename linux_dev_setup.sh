#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"

"$SCRIPT_DIR/apt_install.sh"

"$SCRIPT_DIR/mise_install.sh"

"$SCRIPT_DIR/gnome_extensions_install.sh"

"$SCRIPT_DIR/linux_workspace_keybindings.sh"

"$SCRIPT_DIR/load_dotfiles.sh"

# symlink batcat as bat
mkdir -p ~/.local/bin
ln -sfn /usr/bin/batcat ~/.local/bin/bat
# NOTE: must run after "stow -t ~ bat" to detect .config/bat/themes
"$HOME/.local/bin/bat" cache --build

exit 0
