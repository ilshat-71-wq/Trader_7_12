#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="Trader_7_12 Pro.app"
DIST_DIR="dist"
BUILD_DIR="build"
SPEC="scripts/Trader_7_12_Pro.spec"

printf '%s\n' "=== TRADER_7_12 PRO • macOS APP BUILD ==="
printf '%s\n' "Repository: $(pwd)"
printf '%s\n' "Branch: $(git branch --show-current 2>/dev/null || echo unknown)"

if [[ "$(git branch --show-current 2>/dev/null)" != "main" ]]; then
  echo "ERROR: build must run from main branch."
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: local working tree is not clean. Commit or stash local changes first."
  git status --short
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: this build is for macOS only."
  exit 1
fi

PYTHON_BIN="$(command -v python3)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "ERROR: python3 not found."
  exit 1
fi

if ! "${PYTHON_BIN}" -c 'import PyInstaller' >/dev/null 2>&1; then
  echo "ERROR: PyInstaller is not installed for ${PYTHON_BIN}."
  echo "Install it once with:"
  echo "  ${PYTHON_BIN} -m pip install pyinstaller"
  exit 1
fi

"${PYTHON_BIN}" -m compileall -q Program
PYTHONPATH=Program "${PYTHON_BIN}" -m pytest -q Program

rm -rf "${DIST_DIR}/${APP_NAME}" "${BUILD_DIR}/Trader_7_12_Pro"

"${PYTHON_BIN}" -m PyInstaller \
  --noconfirm \
  --clean \
  "${SPEC}"

APP_PATH="${DIST_DIR}/${APP_NAME}"
if [[ ! -d "${APP_PATH}" ]]; then
  echo "ERROR: expected app bundle was not created: ${APP_PATH}"
  exit 1
fi

if [[ ! -x "${APP_PATH}/Contents/MacOS/Trader_7_12_Pro" ]]; then
  echo "ERROR: app executable is missing."
  exit 1
fi

printf '%s\n' ""
printf '%s\n' "=== APP BUILD OK ==="
printf '%s\n' "${APP_PATH}"
printf '%s\n' "Bundle identifier: com.ilshat.trader712pro"
printf '%s\n' ""
printf '%s\n' "Next: double-click '${APP_PATH}' in Finder."
printf '%s\n' "For a terminal-visible launch, use:"
printf '%s\n' "  open -a \"$(pwd)/${APP_PATH}\""
