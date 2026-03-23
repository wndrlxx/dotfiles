typeset -U PATH path

# History management
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt SHARE_HISTORY

# fzf configuration
# Set up fzf key bindings and fuzzy completion
if type rg &> /dev/null; then
  export FZF_DEFAULT_COMMAND='rg --hidden -g "!tmp/" -g "!.git/" -g "!node_modules" -l ""'
  export FZF_DEFAULT_OPTS=" \
    --height 80% --border
    --layout reverse"
  fi
  export FZF_CTRL_T_OPTS="
    --walker-skip .git,node_modules,target
    --preview 'fzf-preview.sh {}' \
    --bind 'ctrl-/:change-preview-window(down|hidden|)'"
source <(fzf --zsh)

# ZSH configuration
PROMPT_EOL_MARK=''

# Define a specific, hidden location for completion dumps
export ZSH_COMPDUMP="${ZDOTDIR:-$HOME}/.cache/zcompdump"
# Ensure the directory exists
mkdir -p "$(dirname "$ZSH_COMPDUMP")"

# Antidote configuration
source $(brew --prefix)/opt/antidote/share/antidote/antidote.zsh
antidote load ~/.zsh_plugins.txt ~/.zsh_plugins.zsh

# Starship configuration
export STARSHIP_CONFIG=~/.config/starship/starship.toml

# User configuration
# export BAT_THEME="Catppuccin-frappe"
export MANPAGER="sh -c 'col -bx | bat -l man -p'"

# Load nvm
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# My custom aliases - organized by category
# Make commands interactive
alias cp="cp -iv"
alias l="ls -lah"
alias ls="eza -snew --icons --group-directories-first --color=always"
alias mv="mv -iv"
alias rm="rm -iv"

# Git aliases
alias g='git'
alias gst='git status'
alias gl='git pull'
alias gp='git push'
alias gco='git checkout'
alias gcb='git checkout -b'
# alias ga='git add'
alias gaa='git add --all'
alias gcm='git commit -m'

# Ruby/Rails aliases
alias be="bundle exec"
alias br="bin/rails"
alias bi="bundle install"

# Navigation/System aliases
alias e="exit"
alias ..="cd .."
alias ...="cd ../.."

# Apps
alias ff="fastfetch"
alias news="newsboat"
alias y="yazi"

# Editor aliases
alias n="nvim"
alias vi="nvim"
alias viv="nvim ~/.config/nvim"
alias vin="nvim ~/.config/nvim"
alias viz="nvim ~/.zshrc"
alias vize="nvim ~/.zshenv"
alias vit="nvim ~/.config/tmux/tmux.conf"
alias via="nvim ~/.config/aerospace/aerospace.toml"
alias vis="nvim ~/.config/sketchybar/sketchybarrc"
alias vig="nvim ~/.config/ghostty/config"
alias lg="lazygit"

# Project-specific aliases
alias h2='$(npm prefix -s)/node_modules/.bin/shopify hydrogen'

# gcloud CLI
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"

# pnpm
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# Terraform completion
autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C "$(brew --prefix)/bin/terraform" terraform

# Carapace configuration
autoload -U compinit && compinit
export CARAPACE_BRIDGES='zsh,fish,bash,inshellisense' # optional
zstyle ':completion:*' format $'\e[2;37mCompleting %d\e[m'
source <(carapace _carapace)

# Initialize tools
. "$HOME/.atuin/bin/env"
eval "$(atuin init zsh)"
eval "$("$(brew --prefix)/bin/brew" shellenv)"
eval "$(rbenv init - zsh)"
eval "$(pyenv init - zsh)"
eval "$(zoxide init zsh --cmd j)"
eval "$(thefuck --alias)"
eval "$(thefuck --alias fk)"
eval "$(starship init zsh)"
