# environment variables
export TERM=xterm-256color
export LANG=en_US.UTF-8
export ZSH="$HOME/.oh-my-zsh"
export UPDATE_ZSH_DAYS=2
export SPARK_HOME="/opt/homebrew/Cellar/apache-spark/3.5.0/libexec"
export PYTHONPATH="${SPARK_HOME}/python/:$PYTHONPATH"
export PYTHONPATH="${SPARK_HOME}/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk/"
export NVM_DIR="$HOME/.nvm"
export PNPM_HOME="$HOME/Library/pnpm"

# PATH modifications
export PATH="$JAVA_HOME:$PATH"
export PATH="$SPARK_HOME/bin/:$PATH"
export PATH="/opt/homebrew/bin:$PATH"
export PATH="$HOME/.rbenv/bin:$PATH"
export PATH="$PATH:$HOME/.local/bin"
export PATH="/opt/homebrew/opt/sqlite/bin:$PATH"

