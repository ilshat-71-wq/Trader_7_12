#!/bin/zsh
# macOS app build script for Trader_7_12 Pro.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT_DIR="$(pwd)"

APP_NAME="Trader_7_12 Pro.app"
DIST_DIR="dist"
BUILD_DIR="build"
SPEC="scripts/Trader_7_12_Pro.spec"
APP_VERSION="2.4.3"
PUBLISHED_APP="${ROOT_DIR}/${DIST_DIR}/${APP_NAME}"
BUILD_MODE="${TRADER_BUILD_MODE:-adhoc}"
APPLE_CODESIGN_IDENTITY="${APPLE_CODESIGN_IDENTITY:-}"
APP_STORE_PROVISIONING_PROFILE="${APP_STORE_PROVISIONING_PROFILE:-}"
STORE_ENTITLEMENTS="${ROOT_DIR}/AppStore/Trader_7_12_Pro.entitlements"

if [[ "${BUILD_MODE}" == "store" ]]; then
    [[ -n "${APPLE_CODESIGN_IDENTITY}" ]] || { echo "ERROR: APPLE_CODESIGN_IDENTITY is required for Store build."; exit 1; }
    [[ -f "${APP_STORE_PROVISIONING_PROFILE}" ]] || { echo "ERROR: APP_STORE_PROVISIONING_PROFILE is required for Store/TestFlight build."; exit 1; }
    [[ -f "${STORE_ENTITLEMENTS}" ]] || { echo "ERROR: Store entitlements are missing."; exit 1; }
elif [[ "${BUILD_MODE}" != "adhoc" ]]; then
    echo "ERROR: TRADER_BUILD_MODE must be adhoc or store."
    exit 1
fi

printf '%s\n' "=== TRADER_7_12 PRO • macOS APP BUILD ==="
printf '%s\n' "Repository: $(pwd)" "Branch: $(git branch --show-current 2>/dev/null || echo unknown)" "Commit: $(git rev-parse HEAD)"

[[ "$(git branch --show-current 2>/dev/null)" == "main" ]] || { echo "ERROR: build must run from main branch."; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo "ERROR: local working tree is not clean."; git status --short; exit 1; }
[[ "$(uname -s)" == "Darwin" ]] || { echo "ERROR: this build is for macOS only."; exit 1; }
PYTHON_BIN="$(command -v python3)"
[[ -n "${PYTHON_BIN}" ]] || { echo "ERROR: python3 not found."; exit 1; }
"${PYTHON_BIN}" -c 'import PyInstaller' >/dev/null 2>&1 || { echo "ERROR: PyInstaller is not installed."; exit 1; }
command -v codesign >/dev/null 2>&1 || { echo "ERROR: codesign is required."; exit 1; }
${PYTHON_BIN} -c 'import websocket' >/dev/null 2>&1 || { echo "ERROR: websocket-client is required for BCS realtime BOOK/TAPE. Install with: ${PYTHON_BIN} -m pip install websocket-client"; exit 1; }

"${PYTHON_BIN}" -m compileall -q Program
PYTHONPATH=Program "${PYTHON_BIN}" -m pytest -q Program
rm -rf "${DIST_DIR}/${APP_NAME}" "${DIST_DIR}/Trader_7_12_Pro" "${BUILD_DIR}/Trader_7_12_Pro"
mkdir -p "${BUILD_DIR}"

ICONSET="${BUILD_DIR}/Trader_7_12_Pro.iconset"
ICNS="${BUILD_DIR}/Trader_7_12_Pro.icns"
rm -rf "${ICONSET}" "${ICNS}"
mkdir -p "${ICONSET}"

ROOT="$(pwd)" ICONSET="${ICONSET}" "${PYTHON_BIN}" - <<'PY'
import math, os, sys
from pathlib import Path
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication

iconset = Path(os.environ["ICONSET"])
app = QApplication.instance() or QApplication(sys.argv)
S = 1024
image = QImage(S, S, QImage.Format_ARGB32_Premultiplied)
image.fill(QColor("#061416"))
p = QPainter(image); p.setRenderHint(QPainter.Antialiasing, True)

bg = QRadialGradient(S*.50, S*.46, S*.56)
bg.setColorAt(0, QColor("#0e5552")); bg.setColorAt(.62, QColor("#073b3b")); bg.setColorAt(1, QColor("#061416"))
p.fillRect(0, 0, S, S, bg)

cx, cy, r = S*.50, S*.48, S*.34
halo = QRadialGradient(cx, cy, r*1.28)
halo.setColorAt(0, QColor(42, 220, 204, 70)); halo.setColorAt(1, QColor(42, 220, 204, 0))
p.setPen(Qt.NoPen); p.setBrush(halo); p.drawEllipse(QPointF(cx,cy), r*1.28, r*1.28)
p.setBrush(QColor("#08736e")); p.setPen(QPen(QColor("#d8b85b"), 20)); p.drawEllipse(QPointF(cx,cy), r, r)
p.setPen(QPen(QColor("#f2d47b"), 5)); p.drawEllipse(QPointF(cx,cy), r*.91, r*.91)

p.setPen(QPen(QColor("#f2d47b"), 13, Qt.SolidLine, Qt.RoundCap))
for i in range(12):
    a=math.radians(i*30-90); outer=r*.82; inner=r*(.69 if i%3 else .64)
    p.drawLine(QPointF(cx+math.cos(a)*inner,cy+math.sin(a)*inner),QPointF(cx+math.cos(a)*outer,cy+math.sin(a)*outer))

for angle,length,width in ((138,r*.50,25),(18,r*.66,18)):
    a=math.radians(angle-90); p.setPen(QPen(QColor("#f4d47a"),width,Qt.SolidLine,Qt.RoundCap))
    p.drawLine(QPointF(cx,cy),QPointF(cx+math.cos(a)*length,cy+math.sin(a)*length))
a=math.radians(-90)
p.setPen(QPen(QColor("#d4ad4d"),9,Qt.SolidLine,Qt.RoundCap))
p.drawLine(QPointF(cx,cy),QPointF(cx+math.cos(a)*r*.76,cy+math.sin(a)*r*.76))
p.setBrush(QColor("#f3d477")); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(cx,cy),25,25)
p.setBrush(QColor("#08736e")); p.drawEllipse(QPointF(cx,cy),10,10)
p.end()

rounded=QImage(S,S,QImage.Format_ARGB32_Premultiplied); rounded.fill(Qt.transparent)
p=QPainter(rounded); p.setRenderHint(QPainter.Antialiasing,True)
p.setBrush(Qt.NoBrush)
from PySide6.QtGui import QPainterPath
path=QPainterPath(); path.addRoundedRect(8,8,S-16,S-16,210,210); p.setClipPath(path); p.drawImage(0,0,image); p.end()

sizes=[(16,"16x16"),(32,"16x16@2x"),(32,"32x32"),(64,"32x32@2x"),(128,"128x128"),(256,"128x128@2x"),(256,"256x256"),(512,"256x256@2x"),(512,"512x512"),(1024,"512x512@2x")]
for size,name in sizes:
    if not rounded.scaled(size,size,Qt.IgnoreAspectRatio,Qt.SmoothTransformation).save(str(iconset/f"icon_{name}.png"),"PNG"):
        raise RuntimeError(f"failed to save {name}")
PY

command -v iconutil >/dev/null 2>&1 || { echo "ERROR: iconutil is required."; exit 1; }
iconutil -c icns "${ICONSET}" -o "${ICNS}"
rm -rf "${ICONSET}"
xattr -cr "${ICNS}" 2>/dev/null || true
export TRADER_BUILD_COMMIT="$(git rev-parse HEAD)"

# Build the PyInstaller payload outside the repository/File Provider tree.
STAGE_DIR="$(mktemp -d /tmp/trader712-build.XXXXXX)"
trap 'rm -rf "${STAGE_DIR}"' EXIT
STAGE_DIST="${STAGE_DIR}/dist"
STAGE_WORK="${STAGE_DIR}/build"
mkdir -p "${STAGE_DIST}" "${STAGE_WORK}"

PYINSTALLER_SIGN_ARGS=()
if [[ "${BUILD_MODE}" == "store" ]]; then
    PYINSTALLER_SIGN_ARGS+=(--codesign-identity "${APPLE_CODESIGN_IDENTITY}")
    PYINSTALLER_SIGN_ARGS+=(--osx-entitlements-file "${STORE_ENTITLEMENTS}")
fi

"${PYTHON_BIN}" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "${STAGE_DIST}" \
    --workpath "${STAGE_WORK}" \
    "${PYINSTALLER_SIGN_ARGS[@]}" \
    "${SPEC}"

STAGE_APP="${STAGE_DIST}/${APP_NAME}"
[[ -d "${STAGE_APP}" ]] || { echo "ERROR: staged app bundle was not created."; exit 1; }
[[ -x "${STAGE_APP}/Contents/MacOS/Trader_7_12_Pro" ]] || { echo "ERROR: staged app executable is missing."; exit 1; }
BUNDLE_COMMIT="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleSourceCommit' "${STAGE_APP}/Contents/Info.plist")"
BUNDLE_VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "${STAGE_APP}/Contents/Info.plist")"
ICON_FILE="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIconFile' "${STAGE_APP}/Contents/Info.plist")"
[[ "${BUNDLE_COMMIT}" == "${TRADER_BUILD_COMMIT}" ]] || { echo "ERROR: bundle provenance mismatch."; exit 1; }
[[ "${BUNDLE_VERSION}" == "${APP_VERSION}" ]] || { echo "ERROR: bundle version mismatch."; exit 1; }
[[ "${ICON_FILE}" == "Trader_7_12_Pro.icns" && -f "${STAGE_APP}/Contents/Resources/Trader_7_12_Pro.icns" ]] || { echo "ERROR: turquoise-gold app icon is missing."; exit 1; }

if xattr -lr "${STAGE_APP}" 2>/dev/null | grep -E 'com\.apple\.(FinderInfo|ResourceFork)|com\.apple\.fileprovider\.' >/dev/null; then
    echo "ERROR: staged app still contains macOS metadata before final signing."
    xattr -lr "${STAGE_APP}" 2>/dev/null | head -80
    exit 1
fi

if [[ "${BUILD_MODE}" == "store" ]]; then
    # Embed the Mac App Store distribution profile before the final outer signature.
    ditto "${APP_STORE_PROVISIONING_PROFILE}" "${STAGE_APP}/Contents/embedded.provisionprofile"
    # PyInstaller has already signed nested Mach-O code with the distribution identity.
    # Sign the outer app last; Apple recommends signing inside-out rather than using --deep.
    codesign --force --options runtime --timestamp \
        --entitlements "${STORE_ENTITLEMENTS}" \
        --sign "${APPLE_CODESIGN_IDENTITY}" "${STAGE_APP}"
else
    codesign --force --deep --sign - --timestamp=none "${STAGE_APP}"
fi
codesign --verify --deep --strict --verbose=2 "${STAGE_APP}"

# The repository lives under Documents, where macOS/File Provider can attach
# FinderInfo/FileProvider metadata to published bundle directories.
# dist/ is therefore a visibility/copy artifact, not the canonical signed app.
# The canonical signed application is installed under ~/Applications.
INSTALL_DIR="${HOME}/Applications"
INSTALLED_APP="${INSTALL_DIR}/${APP_NAME}"

mkdir -p "${ROOT_DIR}/dist" "${INSTALL_DIR}"
rm -rf "${PUBLISHED_APP}" "${INSTALLED_APP}"

ditto --norsrc --noextattr --noqtn "${STAGE_APP}" "${PUBLISHED_APP}"
ditto --norsrc --noextattr --noqtn "${STAGE_APP}" "${INSTALLED_APP}"

xattr -cr "${PUBLISHED_APP}" 2>/dev/null || true
xattr -cr "${INSTALLED_APP}" 2>/dev/null || true

# Documents may reattach FinderInfo after publication, so never use dist/
# for the final codesign verification.
codesign --verify --deep --strict --verbose=2 "${INSTALLED_APP}"

printf '%s\n' ""     "=== APP BUILD OK ==="     "Build artifact: ${PUBLISHED_APP}"     "Signed install: ${INSTALLED_APP}"     "Bundle version: ${BUNDLE_VERSION}"     "Bundle source commit: ${BUNDLE_COMMIT}"     "Bundle icon: turquoise-gold watch dial"     "Code signing: ${BUILD_MODE}"     "Packaging: PyInstaller onedir + macOS .app"     "Single-window dashboard: SPOT + Futures OI"
