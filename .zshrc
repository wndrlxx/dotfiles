typeset -U PATH path

export EDITOR="nvim"

# History management
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt SHARE_HISTORY

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

# Path to oh-my-zsh installation
export ZSH="$HOME/.oh-my-zsh"

source "$(brew --prefix)/share/powerlevel10k/powerlevel10k.zsh-theme"

# ZSH configuration
export UPDATE_ZSH_DAYS=2
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
export TERM=xterm-256color
export LANG=en_US.UTF-8

# NVM - Lazy loading for better performance
export NVM_DIR="$HOME/.nvm"
# Replace the standard nvm loading with lazy loading
nvm() {
  unset -f nvm
  local nvm_prefix="$(brew --prefix nvm)"
  [ -s "$nvm_prefix/nvm.sh" ] && \. "$nvm_prefix/nvm.sh"
  [ -s "$nvm_prefix/etc/bash_completion.d/nvm" ] && \. "$nvm_prefix/etc/bash_completion.d/nvm"
  nvm "$@"
}

# Load nvmrc when changing directories
autoload -U add-zsh-hook
load-nvmrc() {
  local nvmrc_path="$(nvm_find_nvmrc)"

  if [ -n "$nvmrc_path" ]; then
    local nvmrc_node_version=$(nvm version "$(cat "${nvmrc_path}")")

    if [ "$nvmrc_node_version" = "N/A" ]; then
      nvm install
    elif [ "$nvmrc_node_version" != "$(nvm version)" ]; then
      nvm use
    fi
  elif [ -n "$(PWD=$OLDPWD nvm_find_nvmrc)" ] && [ "$(nvm version)" != "$(nvm version default)" ]; then
    echo "Reverting to nvm default version"
    nvm use default
  fi
}
add-zsh-hook chpwd load-nvmrc

# Load p10k configuration
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# PATH modifications
export PATH="$HOME/.rbenv/bin:$PATH"
export PATH="$PATH:$HOME/.local/bin"
export PATH="$(brew --prefix)/opt/sqlite/bin:$PATH"


# Java and Spark configuration
export JAVA_HOME="$(brew --prefix)/opt/openjdk/"
export PATH="$JAVA_HOME:$PATH"
export SPARK_HOME="$(brew --prefix)/Cellar/apache-spark/3.5.0/libexec"
export PATH="$SPARK_HOME/bin/:$PATH"
export PYTHONPATH="${SPARK_HOME}/python/:$PYTHONPATH"
export PYTHONPATH="${SPARK_HOME}/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH"

# Initialize tools
eval "$("$(brew --prefix)/bin/brew" shellenv)"
eval "$(rbenv init - zsh)"
eval "$(pyenv init -)"

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
alias vit="nvim ~/.tmux.conf"
alias lg="lazygit"

# Project-specific aliases
alias h2='$(npm prefix -s)/node_modules/.bin/shopify hydrogen'

# gcloud CLI
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"

# pnpm
export PNPM_HOME="/Users/alm2/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac

# Terraform completion
autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C "$(brew --prefix)/bin/terraform" terraform

