typeset -U PATH path

# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

[ -f /opt/homebrew/etc/profile.d/autojump.sh ] && . /opt/homebrew/etc/profile.d/autojump.sh

#jdk() {
        #version=$1
        #export JAVA_HOME=$(/usr/libexec/java_home -v"$version");
        #java -version
# }

if type rg &> /dev/null; then
  export FZF_DEFAULT_COMMAND='rg --hidden -g "!tmp/" -g "!.git/" -g "!node_modules" -l ""'
  export FZF_DEFAULT_OPTS=" \
    --height 70% --border
    --color=bg+:#414559,bg:#303446,spinner:#f2d5cf,hl:#e78284 \
    --color=fg:#c6d0f5,header:#e78284,info:#ca9ee6,pointer:#f2d5cf \
    --color=marker:#f2d5cf,fg+:#c6d0f5,prompt:#ca9ee6,hl+:#e78284"
fi

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

source /opt/homebrew/share/powerlevel10k/powerlevel10k.zsh-theme

# Uncomment the following line to change how often to auto-update (in days).
export UPDATE_ZSH_DAYS=2

# Hide '%' prompt indicator when file doesn't end with newline character.
PROMPT_EOL_MARK=''

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS=true

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

plugins=(git macos zsh-autosuggestions)

source $ZSH/oh-my-zsh.sh

# User configuration
export BAT_THEME="Catppuccin-frappe"
export TERM=xterm-256color

# You may need to manually set your language environment
export LANG=en_US.UTF-8

export NVM_DIR="$HOME/.nvm"
[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"  # This loads nvm
[ -s "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" ] && \. "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm"  # This loads nvm bash_completion

# place this after nvm initialization!
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
load-nvmrc

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh


export PATH="$HOME/.rbenv/bin:$PATH"
export SPARK_HOME=/opt/homebrew/Cellar/apache-spark/3.5.0/libexec
export PATH="$SPARK_HOME/bin/:$PATH"
export PYTHONPATH="${SPARK_HOME}/python/:$PYTHONPATH"
export PYTHONPATH="${SPARK_HOME}/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH"
export PATH="$PATH:$HOME/.local/bin"
export PATH="/opt/homebrew/opt/sqlite/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk/"
export PATH="$JAVA_HOME:$PATH"

eval $(/opt/homebrew/bin/brew shellenv)
eval "$(rbenv init - zsh)"
eval "$(pyenv init -)"

# My custom aliases
alias seeing_is_believing="andyw8_seeing_is_believing"
alias be="bundle exec"
alias br="bin/rails"
alias lg="lazygit"
alias e="exit"
alias vi='nvim'
alias viv="vim ~/.config/nvim/init.vim"
alias viz="vim ~/.zshrc"
alias vit="vim ~/.tmux.conf"

# gcloud CLI
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"

# pnpm
export PNPM_HOME="/Users/alm2/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end

autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C /opt/homebrew/bin/terraform terraform

PATH=~/.console-ninja/.bin:$PATH
