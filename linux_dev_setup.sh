#!/bin/bash

./apt_install.sh

./mise_install.sh

./gnome_extensions_install.sh

./linux_workspace_keybindings.sh

./load_dotfiles.sh

# symlink batcat as bat
mkdir -p ~/.local/bin
ln -s /usr/bin/batcat ~/.local/bin/bat
# NOTE: must run after "stow -t ~ bat" to detect .config/bat/themes
bat cache --build

exit 0
