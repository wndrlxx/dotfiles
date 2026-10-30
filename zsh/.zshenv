export EDITOR="nvim"
export PAGER="less"
export MANPAGER="sh -c 'col -bx | bat -l man -p'"
if [[ "$OSTYPE" == "linux"* ]]; then
  # MANROFFOPT="-c" ensures 'man' outputs plain text instead of legacy
  # SGR/terminal escape sequences. This prevents "junk" characters
  # from appearing when piping man pages into 'bat'.
  export MANROFFOPT="-c"
fi
export ZDOTDIR="$HOME/.config/zsh"

# Make Mise tools available before interactive hooks run (e.g. to Herdr plugins).
export PATH="$HOME/.local/share/mise/shims:$PATH"
export LANG=en_US.UTF-8
export STARSHIP_CONFIG=~/.config/starship/starship.toml
