#!/usr/bin/env bash
# Sprint 0: reproducible environment setup.
# Creates a virtual environment, installs pinned dependencies, and runs the
# smoke test to confirm DEVSIM works before any device-level code is used.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Environment ready. Running Sprint 0 smoke test..."
python simulations/sprint0_smoke_test/smoke_test.py
