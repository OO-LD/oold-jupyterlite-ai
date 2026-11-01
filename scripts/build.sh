#!/usr/bin/env bash
# Build the reference site. Everything it does is in oold-lite.toml; this exists so the
# command is the same one the other playgrounds in the monorepo answer to.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PY="${PY:-$ROOT/.venv/Scripts/python.exe}"
else
  PY="${PY:-$ROOT/.venv/bin/python}"
fi

exec "$PY" -m oold_jupyterlite_ai.cli build --config "$ROOT/oold-lite.toml" --output "$ROOT/_output" "$@"
