#!/bin/bash
set -euo pipefail

curl -LsSf https://astral.sh/uv/install.sh | sh

export PATH="$HOME/.local/bin:$PATH"

uv python install --default
