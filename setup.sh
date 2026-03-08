#!/usr/bin/env bash
set -euo pipefail

# setup.sh — create a .venv and install requirements.txt into it
# Usage: ./setup.sh

cd "$(dirname "$0")"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3 not found in PATH. Please install Python 3." >&2
  exit 1
fi

echo "Creating virtual environment in .venv..."
$PY -m venv .venv

echo "Upgrading pip, setuptools, wheel..."
./.venv/bin/python -m pip install --upgrade pip setuptools wheel

if [ ! -f requirements.txt ]; then
  echo "requirements.txt not found in the project root." >&2
  echo "You can create one or run './.venv/bin/pip install <package>' manually."
  exit 1
fi

echo "Installing dependencies from requirements.txt..."
./.venv/bin/pip install -r requirements.txt

echo "Setup complete. Activate the virtualenv with: source .venv/bin/activate"
