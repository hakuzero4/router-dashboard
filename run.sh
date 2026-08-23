#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="$ROOT/.venv/bin:$PATH"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "缺少 .venv，请先安装 Python 依赖"
  exit 1
fi

cd "$ROOT/backend"
exec uvicorn main:app --host 0.0.0.0 --port 8787
