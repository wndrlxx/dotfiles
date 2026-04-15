if [[ "$OSTYPE" == "darwin"* ]]; then
    eval "$("$(brew --prefix)/bin/brew" shellenv)"
fi

if [[ "$OSTYPE" == "linux"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# remove duplicate PATH entries
typeset -U PATH path

# History management
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_FIND_NO_DUPS
setopt SHARE_HISTORY
setopt autocd # change directory without typing cd
setopt glob_dots # include dotfiles in globbing

# zsh config
PROMPT_EOL_MARK=''
# Completion dump location
export ZSH_COMPDUMP="${ZDOTDIR:-$HOME}/.cache/zcompdump"
# Completions — single compinit call with 24hr cache guard
autoload -Uz compinit
if [[ -n ${ZSH_COMPDUMP}(#qN.mh+24) ]]; then
    compinit -d "$ZSH_COMPDUMP"
else
    compinit -C -d "$ZSH_COMPDUMP"
fi
autoload -U +X bashcompinit && bashcompinit
if [[ "$OSTYPE" == "darwin"* ]]; then
    complete -o nospace -C "$(brew --prefix)/bin/terraform" terraform
fi

# initialize mise before fzf
eval "$(~/.local/bin/mise activate zsh)"

# fzf config
source <(fzf --zsh)
export FZF_DEFAULT_OPTS=" \
  --height 80% --border \
  --layout reverse \
  --preview-window=right:70%"
export FZF_DEFAULT_COMMAND=' \
  rg --hidden \
  -g "!.git/" -g "!node_modules/" -g "!tmp/" \
  -l ""'
export FZF_CTRL_T_OPTS=" \
  --walker-skip .git,node_modules,target \
  --preview 'fzf-preview.sh {}' \
  --bind 'ctrl-/:change-preview-window(down|hidden|)'"
export FORGIT_FZF_DEFAULT_OPTS="--preview-window=right:75%"

# Git/delta theme — switch based on OS light/dark mode
if [[ "$OSTYPE" == "darwin"* ]]; then
    INTERFACE_STYLE=$(
        defaults read -g AppleInterfaceStyle &>/dev/null && echo "Dark" || echo "Light"
    )
else
    INTERFACE_STYLE=$(
        [[ $(gsettings get org.gnome.desktop.interface color-scheme) == *dark* ]] \
        && echo "Dark" || echo "Light"
    )
fi
if [[ "$INTERFACE_STYLE" == "Dark" ]]; then
    export BAT_THEME="tokyonight_night"
    export DELTA_FEATURES="dark-mode"
    export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS \
        --color=fg:#c0caf5,bg:#1a1b26,hl:#bb9af7 \
        --color=fg+:#c0caf5,bg+:#1a1b26,hl+:#7dcfff \
        --color=info:#7aa2f7,prompt:#7dcfff,pointer:#7dcfff  \
        --color=marker:#9ece6a,spinner:#9ece6a,header:#9ece6a"
else
    export BAT_THEME="rose-pine-dawn"
    export DELTA_FEATURES="light-mode"
    export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS \
        --color=fg:#797593,bg:#faf4ed,hl:#d7827e \
        --color=fg+:#575279,bg+:#f2e9e1,hl+:#d7827e \
        --color=border:#dfdad9,header:#286983,gutter:#faf4ed \
        --color=spinner:#ea9d34,info:#56949f \
        --color=pointer:#907aa9,marker:#b4637a,prompt:#797593"
fi
bindkey -e  # force emacs mode; overrides vi mode set by fzf via $EDITOR

# zsh hooks
chpwd() {
  eza -larh --icons --group-directories-first --color=always
}

diff() {
  command diff -u "$@" | delta --side-by-side --line-numbers
}

# Suffix aliases
alias -s go="$EDITOR"
alias -s js="$EDITOR"
alias -s json="jless"
alias -s md="bat"
alias -s py="$EDITOR"
alias -s rb="$EDITOR"
alias -s ts="$EDITOR"
alias -s yaml="bat --language=yaml"

# Make commands interactive
alias cp="cp -iv"
alias l="ls -larh"
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
alias gaa='git add --all'
alias gcm='git commit -m'

# Ruby/Rails aliases
alias be="bundle exec"
alias br="bin/rails"
alias bi="bundle install"

# Navigation/System aliases
alias ..="cd .."
alias ...="cd ../.."
alias e="exit"
alias j="cd"
alias sz="source ~/.config/zsh/.zshrc"

# Apps
alias ff="fastfetch"
alias news="newsboat"
alias y="yazi"

# Editor aliases
alias n="nvim"
alias vi="nvim"
alias viv="nvim ~/.config/nvim"
alias vin="nvim ~/.config/nvim"
alias viz="nvim ~/.config/zsh/.zshrc"
alias vize="nvim ~/.zshenv"
alias vigc="nvim ~/.config/git/config"
alias vigi="nvim ~/.config/git/ignore"
alias vit="nvim ~/.config/tmux/tmux.conf"
alias via="nvim ~/.config/aerospace/aerospace.toml"
alias vis="nvim ~/.config/sketchybar/sketchybarrc"
alias vig="nvim ~/.config/ghostty/config"
alias lg="lazygit"

# Project-specific aliases
alias h2='$(npm prefix -s)/node_modules/.bin/shopify hydrogen'

# Lazy load tools
if [[ "$OSTYPE" == "darwin"* ]]; then
	gcloud() {
	    unset -f gcloud
	    source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
	    source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"
	    gcloud "$@"
	}
fi

fuck() {
    unset -f fuck fk
    eval "$(thefuck --alias)"
    eval "$(thefuck --alias fk)"
    fuck "$@"
}
fk() { fuck "$@"; }
pyenv() {
    unset -f pyenv
    eval "$(pyenv init - zsh)"
    pyenv "$@"
}

# Antidote zsh plugin manager config
if [[ "$OSTYPE" == "darwin"* ]]; then
	source $(brew --prefix)/opt/antidote/share/antidote/antidote.zsh
else
  source "$HOME/.antidote/antidote.zsh"
fi
antidote load ~/.config/zsh/.zsh_plugins.txt ~/.config/zsh/.zsh_plugins.zsh

# Initialize tools
source "$HOME/.atuin/bin/env"
eval "$(atuin init zsh)"
eval "$(rbenv init - zsh)"
eval "$(zoxide init zsh --cmd cd)"

# Starship prompt — must be last
eval "$(starship init zsh)"
