#!/usr/bin/env bash
# One-time setup: create a virtualenv and install dependencies.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
    python -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from template. Fill in DISCORD_TOKEN before running the bot."
fi

echo "Setup complete. Activate the venv with: source .venv/bin/activate"
