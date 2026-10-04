#!/bin/bash
set -euo pipefail

# setup 6 workspaces + keybindings
gsettings set org.gnome.mutter dynamic-workspaces false
gsettings set org.gnome.desktop.wm.preferences num-workspaces 6

# workspace 1 binded to "n"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-1 "['<Super>n']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-1 "['<Super><Shift>n']"

# workspace 2 binded to "m"
# remap message tray keybinding (default is <Super>v and <Super>m)
gsettings set org.gnome.shell.keybindings toggle-message-tray "['<Super>comma']"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-2 "['<Super>m']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-2 "['<Super><Shift>m']"

# workspace 3 binded to "u"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-3 "['<Super>u']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-3 "['<Super><Shift>u']"

# workspace 4 binded to "i"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-4 "['<Super>i']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-4 "['<Super><Shift>i']"

# workspace 5 binded to "o"
# replace default <Super>o binding
gsettings set org.gnome.settings-daemon.plugins.media-keys rotate-video-lock-static "['XF86RotationLockToggle']"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-5 "['']"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-5 "['<Super>o']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-5 "['<Super><Shift>o']"

# workspace 6 binded to "p"
# replace default <Super>p binding
gsettings set org.gnome.mutter.keybindings switch-monitor "['XF86Display']"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-6 "['']"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-6 "['<Super>p']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-6 "['<Super><Shift>p']"
