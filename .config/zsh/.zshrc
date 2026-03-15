typeset -U PATH path

# History management
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt SHARE_HISTORY
unsetopt correct

# p10k instant prompt
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# fzf configuration
# Set up fzf key bindings and fuzzy completion
if type rg &> /dev/null; then
  export FZF_DEFAULT_COMMAND='rg --hidden -g "!tmp/" -g "!.git/" -g "!node_modules" -l ""'
  export FZF_DEFAULT_OPTS=" \
    --height 80% --border
    --layout reverse \
    --color=bg+:#414559,bg:#303446,spinner:#f2d5cf,hl:#e78284 \
    --color=fg:#c6d0f5,header:#e78284,info:#ca9ee6,pointer:#f2d5cf \
    --color=marker:#f2d5cf,fg+:#c6d0f5,prompt:#ca9ee6,hl+:#e78284"
  fi
  export FZF_CTRL_T_OPTS="
    --walker-skip .git,node_modules,target
    --preview 'fzf-preview.sh {}' \
    --bind 'ctrl-/:change-preview-window(down|hidden|)'"
source <(fzf --zsh)

source "$(brew --prefix)/share/powerlevel10k/powerlevel10k.zsh-theme"

# ZSH configuration
PROMPT_EOL_MARK=''
ENABLE_CORRECTION="false"
COMPLETION_WAITING_DOTS="true"

# Plugins
plugins=(
  bundler
  colored-man-pages
  git
  you-should-use
  zsh-autosuggestions
  zsh-syntax-highlighting
  zsh-vi-mode
)

source $ZSH/oh-my-zsh.sh

# User configuration
export BAT_THEME="Catppuccin-frappe"

# Load nvm
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Load p10k configuration
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# My custom aliases - organized by category
# Make commands interactive
alias cp="cp -iv"
# alias ls="ls -FGh"
alias ls="eza -snew --icons --group-directories-first --color=always"
alias mv="mv -iv"
alias rm="rm -iv"

# Ruby/Rails aliases
alias be="bundle exec"
alias br="bin/rails"
alias bi="bundle install"

# Navigation/System aliases
alias e="exit"
alias ..="cd .."
alias ...="cd ../.."

# Apps
# alias j="z"
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

# export CARAPACE_BRIDGES='zsh,fish,bash,inshellisense' # optional
# zstyle ':completion:*' format $'\e[2;37mCompleting %d\e[m'
# zstyle ':completion:*:git:*' group-order 'main commands' 'alias commands' 'external commands'
# source <(carapace _carapace)

# Initialize tools
. "$HOME/.atuin/bin/env"
eval "$(atuin init zsh)"
eval "$("$(brew --prefix)/bin/brew" shellenv)"
eval "$(rbenv init - zsh)"
eval "$(pyenv init - zsh)"
eval "$(zoxide init zsh --cmd j)"
eval "$(thefuck --alias)"
eval "$(thefuck --alias fk)"
