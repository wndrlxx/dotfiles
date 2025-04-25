typeset -U PATH path

# History management
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt SHARE_HISTORY

# Initialize tools
eval "$("$(brew --prefix)/bin/brew" shellenv)"
eval "$(rbenv init - zsh)"
eval "$(pyenv init -)"

# p10k instant prompt
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# autojump configuration
AUTOJUMP_SH="$(brew --prefix)/etc/profile.d/autojump.sh"
[ -f "$AUTOJUMP_SH" ] && . "$AUTOJUMP_SH"

# fzf configuration
if type rg &> /dev/null; then
  export FZF_DEFAULT_COMMAND='rg --hidden -g "!tmp/" -g "!.git/" -g "!node_modules" -l ""'
  export FZF_DEFAULT_OPTS=" \
    --height 70% --border
    --color=bg+:#414559,bg:#303446,spinner:#f2d5cf,hl:#e78284 \
    --color=fg:#c6d0f5,header:#e78284,info:#ca9ee6,pointer:#f2d5cf \
    --color=marker:#f2d5cf,fg+:#c6d0f5,prompt:#ca9ee6,hl+:#e78284"
fi

source "$(brew --prefix)/share/powerlevel10k/powerlevel10k.zsh-theme"

# ZSH configuration
PROMPT_EOL_MARK=''
ENABLE_CORRECTION="true"
COMPLETION_WAITING_DOTS="true"

# Plugins
plugins=(
  git
  macos
  zsh-autosuggestions
  zsh-syntax-highlighting
  bundler
  rbenv
  fzf
)

source $ZSH/oh-my-zsh.sh

# User configuration
export BAT_THEME="Catppuccin-frappe"

# Load nvm
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Load p10k configuration
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# My custom aliases - organized by category
# Ruby/Rails aliases
alias be="bundle exec"
alias br="bin/rails"
alias bi="bundle install"
alias seeing_is_believing="andyw8_seeing_is_believing"

# Navigation/System aliases
alias e="exit"
alias ..="cd .."
alias ...="cd ../.."
alias ls="ls -G"
alias ll="ls -la"

# Editor aliases
alias vi='nvim'
alias viv="nvim ~/.config/nvim/init.vim"
alias viz="nvim ~/.zshrc"
alias vize="nvim ~/.zshenv"
alias vit="nvim ~/.tmux.conf"
alias via="nvim ~/.aerospace.toml"
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

eval "$(zoxide init zsh)"
