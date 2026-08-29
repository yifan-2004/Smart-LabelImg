#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv-web/bin/python ]; then
  ./setup_web.sh
fi

ARGS=()
if [ "${1:-}" != "" ]; then
  ARGS+=(--dataset "$1")
fi
.venv-web/bin/python -m smart_labelimg.web_app "${ARGS[@]}"
