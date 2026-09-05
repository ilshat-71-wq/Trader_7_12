#!/bin/zsh
set -e
cd "$(dirname "$0")/.."

# Safe self-sync: update only when the local checkout has no changes.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [[ -z "$(git status --porcelain)" ]]; then
    git pull --ff-only
  else
    echo "⚠️ Локальные изменения обнаружены — автосинхронизация пропущена."
  fi
fi

export PYTHONPATH="${PWD}/Program"
exec python3 "${PWD}/Program/main.py"
