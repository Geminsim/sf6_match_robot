#!/usr/bin/env bash
# Run the SF6 Match Robot bot.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -d .venv ]; then
    # shellcheck source=/dev/null
    source .venv/bin/activate
fi

exec python main.py
