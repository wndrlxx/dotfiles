# Use ~/.config as the base directory for XDG-compatible app configuration
export XDG_CONFIG_HOME="$HOME/.config"

# Homebrew
export PATH="/opt/homebrew/bin:$PATH"

# Go
# [ -s "$HOME/.config/envman/load.sh" ] && source "$HOME/.config/envman/load.sh"
export PATH=$PATH:$HOME/go/bin

# Java
export JAVA_HOME="/opt/homebrew/opt/openjdk/"
export PATH="$JAVA_HOME/bin:$PATH"

# Spark
export SPARK_HOME="/opt/homebrew/Cellar/apache-spark/3.5.0/libexec"
export PATH="$SPARK_HOME/bin:$PATH"
export PYTHONPATH="${SPARK_HOME}/python/:$PYTHONPATH"
export PYTHONPATH="${SPARK_HOME}/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH"

# Ruby
export PATH="$HOME/.rbenv/bin:$PATH"

# pnpm
export PNPM_HOME="$HOME/Library/pnpm"
export PATH="$PNPM_HOME:$PATH"

# Misc
export PATH="$PATH:$HOME/.local/bin"

# SQLite
export PATH="/opt/homebrew/opt/sqlite/bin:$PATH"

# Cargo
. "$HOME/.cargo/env"
