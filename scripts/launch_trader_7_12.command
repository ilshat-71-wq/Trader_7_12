#!/bin/zsh
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="${PWD}/Program"
exec python3 "${PWD}/Program/main.py"
