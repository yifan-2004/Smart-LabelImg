#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' || {
  echo "Smart Label Web requires Python 3.11." >&2
  exit 1
}

"$PYTHON_BIN" -m venv .venv-web
.venv-web/bin/python -m pip install --upgrade pip
.venv-web/bin/python -m pip install -r requirements-web.txt -r requirements-ai.txt
echo "Setup complete. Run ./run_web.sh"
