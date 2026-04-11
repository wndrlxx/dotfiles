#!/bin/bash

# gnome-extensions
pipx install gnome-extensions-cli --system-site-packages
gext install run-or-raise@edvard.cz
gnome-extensions enable just-perfection-desktop@just-perfection
gext install instantworkspaceswitcher@amalantony.net
# removes animation when switching workspaces
gnome-extensions enable instantworkspaceswitcher@amalantony.net
# launch or focus apps with keybindings
gext install run-or-raise@edouard.pinaud.gmail.com
gnome-extensions enable run-or-raise@edouard.pinaud.gmail.com
