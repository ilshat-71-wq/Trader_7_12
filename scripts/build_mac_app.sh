#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="Trader_7_12 Pro.app"
DIST_DIR="dist"
BUILD_DIR="build"
SPEC="scripts/Trader_7_12_Pro.spec"
APP_VERSION="2.2.3"

printf '%s\n' "=== TRADER_7_12 PRO • macOS APP BUILD ==="
printf '%s\n' "Repository: $(pwd)"
printf '%s\n' "Branch: $(git branch --show-current 2>/dev/null || echo unknown)"
printf '%s\n' "Commit: $(git rev-parse HEAD)"

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
mkdir -p "${BUILD_DIR}"

# Restore the original Trader_7_12 Pro one-clock icon used by the old app.
# It is generated locally so no binary icon is stored in Git.
ICONSET="${BUILD_DIR}/Trader_7_12_Pro.iconset"
ICNS="${BUILD_DIR}/Trader_7_12_Pro.icns"
rm -rf "${ICONSET}" "${ICNS}"
mkdir -p "${ICONSET}"

ROOT="$(pwd)" ICONSET="${ICONSET}" "${PYTHON_BIN}" - <<'PY'
import math
import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QRadialGradient, QPen
from PySide6.QtWidgets import QApplication

iconset = Path(os.environ["ICONSET"])
app = QApplication.instance() or QApplication(sys.argv)
S = 1024
image = QImage(S, S, QImage.Format_ARGB32_Premultiplied)
image.fill(QColor("#11161b"))
p = QPainter(image)
p.setRenderHint(QPainter.Antialiasing, True)

bg = QLinearGradient(0, 0, 0, S)
bg.setColorAt(0, QColor("#11161b")); bg.setColorAt(.55, QColor("#171c21")); bg.setColorAt(1, QColor("#0f1418"))
p.fillRect(0, 0, S, S, bg)
halo = QRadialGradient(S*.50, S*.48, S*.48)
halo.setColorAt(0, QColor(190,214,120,34)); halo.setColorAt(.55, QColor(190,214,120,12)); halo.setColorAt(1, QColor(190,214,120,0))
p.fillRect(0, 0, S, S, halo)

x, y, r = S*.50, S*.43, S*.32
p.save(); p.translate(x, y)
clock_halo = QRadialGradient(0, 0, r*1.35)
clock_halo.setColorAt(0, QColor(205,218,154,42)); clock_halo.setColorAt(1, QColor(205,218,154,0))
p.setPen(Qt.NoPen); p.setBrush(clock_halo); p.drawEllipse(QPointF(0,0), r*1.35, r*1.35)
face = QRadialGradient(-r*.25, -r*.30, r*1.15)
face.setColorAt(0, QColor("#f1e7c8")); face.setColorAt(.72, QColor("#d8c99f")); face.setColorAt(1, QColor("#a99972"))
p.setBrush(face); p.setPen(QPen(QColor("#806f4d"), max(3, r*.045))); p.drawEllipse(QPointF(0,0), r, r)
melt = QLinearGradient(0, r*.50, 0, r*1.72)
melt.setColorAt(0, QColor("#d8c99f")); melt.setColorAt(1, QColor("#8f7e58"))
p.setBrush(melt); p.setPen(Qt.NoPen)
p.drawRoundedRect(-r*.46, r*.55, r*.92, r*1.34, r*.18, r*.18)
p.drawEllipse(QPointF(-r*.24, r*1.18), r*.16, r*.25)
p.drawEllipse(QPointF(r*.22, r*1.34), r*.13, r*.21)
p.setPen(QPen(QColor("#6c6046"), max(2, r*.025)))
for i in range(12):
    a = math.radians(i*30-90)
    p.drawLine(QPointF(math.cos(a)*r*.78, math.sin(a)*r*.78), QPointF(math.cos(a)*r*.88, math.sin(a)*r*.88))
a = math.radians(28)
p.setPen(QPen(QColor("#3e392d"), max(3, r*.035), Qt.SolidLine, Qt.RoundCap))
p.drawLine(QPointF(0,0), QPointF(math.cos(a)*r*.54, math.sin(a)*r*.54))
a2 = math.radians(336)
p.setPen(QPen(QColor("#514a3a"), max(2, r*.025), Qt.SolidLine, Qt.RoundCap))
p.drawLine(QPointF(0,0), QPointF(math.cos(a2)*r*.72, math.sin(a2)*r*.72))
p.setBrush(QColor("#514a3a")); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(0,0), r*.06, r*.06)
p.restore(); p.end()

rounded = QImage(S, S, QImage.Format_ARGB32_Premultiplied); rounded.fill(Qt.transparent)
p = QPainter(rounded); p.setRenderHint(QPainter.Antialiasing, True)
path = QPainterPath(); path.addRoundedRect(8, 8, S-16, S-16, 210, 210); p.setClipPath(path); p.drawImage(0,0,image); p.end()

sizes = [(16,"16x16"),(32,"16x16@2x"),(32,"32x32"),(64,"32x32@2x"),(128,"128x128"),(256,"128x128@2x"),(256,"256x256"),(512,"256x256@2x"),(512,"512x512"),(1024,"512x512@2x")]
for size, name in sizes:
    scaled = rounded.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    if not scaled.save(str(iconset / f"icon_{name}.png"), "PNG"):
        raise RuntimeError(f"failed to save {name}")
PY

if ! command -v iconutil >/dev/null 2>&1; then
  echo "ERROR: iconutil is required to build the macOS application icon."
  exit 1
fi
iconutil -c icns "${ICONSET}" -o "${ICNS}"
rm -rf "${ICONSET}"

export TRADER_BUILD_COMMIT="$(git rev-parse HEAD)"
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

BUNDLE_COMMIT="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleSourceCommit' "${APP_PATH}/Contents/Info.plist")"
BUNDLE_VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "${APP_PATH}/Contents/Info.plist")"
ICON_FILE="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIconFile' "${APP_PATH}/Contents/Info.plist")"
if [[ "${BUNDLE_COMMIT}" != "${TRADER_BUILD_COMMIT}" ]]; then
  echo "ERROR: bundle provenance mismatch."
  exit 1
fi
if [[ "${BUNDLE_VERSION}" != "${APP_VERSION}" ]]; then
  echo "ERROR: bundle version mismatch."
  exit 1
fi
if [[ "${ICON_FILE}" != "Trader_7_12_Pro.icns" || ! -f "${APP_PATH}/Contents/Resources/Trader_7_12_Pro.icns" ]]; then
  echo "ERROR: one-clock app icon is missing from the bundle."
  exit 1
fi

printf '%s\n' "" "=== APP BUILD OK ===" "${APP_PATH}" \
  "Bundle identifier: com.ilshat.trader712pro" \
  "Bundle version: ${BUNDLE_VERSION}" \
  "Bundle source commit: ${BUNDLE_COMMIT}" \
  "Bundle icon: original one-clock" "" \
  "Next: double-click '${APP_PATH}' in Finder." \
  "For a terminal-visible launch, use:" \
  "  open \"$(pwd)/${APP_PATH}\"" \
  "Direct executable for diagnostics:" \
  "  \"$(pwd)/${APP_PATH}/Contents/MacOS/Trader_7_12_Pro\""
