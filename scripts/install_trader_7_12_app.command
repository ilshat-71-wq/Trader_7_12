#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Applications/Trader_7_12 Pro.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
KEYCHAIN_SERVICE="Trader_7_12 BCS Refresh Token"

# Keep the BCS refresh token outside Git and outside the app bundle.
# Prefer the current shell environment, then the existing local credential file.
TOKEN="${BCS_REFRESH_TOKEN:-}"
if [[ -z "$TOKEN" && -f "$HOME/.trader_7_12_env" ]]; then
    source "$HOME/.trader_7_12_env"
    TOKEN="${BCS_REFRESH_TOKEN:-}"
fi

if [[ -z "$TOKEN" ]]; then
    echo "ERROR: BCS_REFRESH_TOKEN is not available."
    echo "Set it in the shell or in ~/.trader_7_12_env, then run this installer again."
    exit 1
fi

# Store/update the credential in macOS Keychain. The token is never written to Git
# and is never copied into the .app bundle.
security add-generic-password \
    -a "$USER" \
    -s "$KEYCHAIN_SERVICE" \
    -w "$TOKEN" \
    -U >/dev/null

unset TOKEN

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"

cat > "$RESOURCES/launch_trader_7_12.sh" <<LAUNCHER
#!/bin/zsh
set -euo pipefail
ROOT="$ROOT"
KEYCHAIN_SERVICE="$KEYCHAIN_SERVICE"
cd "\$ROOT"
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"
export PYTHONPATH="\$ROOT/Program"

# Load the BCS refresh token from macOS Keychain for this process only.
# It is intentionally not stored in the app bundle, Git repository, or plist.
BCS_TOKEN="$(security find-generic-password -a "\$USER" -s "\$KEYCHAIN_SERVICE" -w 2>/dev/null || true)"
if [[ -n "\$BCS_TOKEN" ]]; then
    export BCS_REFRESH_TOKEN="\$BCS_TOKEN"
    unset BCS_TOKEN
else
    echo "WARNING: BCS refresh token was not found in macOS Keychain." >&2
fi

exec /usr/bin/env python3 "\$ROOT/Program/main.py"
LAUNCHER
chmod +x "$RESOURCES/launch_trader_7_12.sh"

CLANG="/usr/bin/clang"
if [[ ! -x "$CLANG" ]]; then
    CLANG="$(xcrun --find clang 2>/dev/null || true)"
fi
if [[ -z "$CLANG" || ! -x "$CLANG" ]]; then
    echo "ERROR: clang is required to build the native macOS launcher."
    echo "Install Xcode Command Line Tools with: xcode-select --install"
    exit 1
fi

"$CLANG" -O2 -Wall -Wextra \
    "$ROOT/scripts/macos_app_launcher.c" \
    -o "$MACOS/Trader_7_12 Pro"
chmod +x "$MACOS/Trader_7_12 Pro"

# Build the branded macOS icon from the existing MeltingClocksWidget.
# This keeps the icon visually identical to the scanner splash, but uses one
# large melting clock and no text. Nothing is added to the repository.
ICONSET="$RESOURCES/Trader_7_12_Pro.iconset"
ICNS="$RESOURCES/Trader_7_12_Pro.icns"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

PYTHONPATH="$ROOT/Program" \
ROOT="$ROOT" ICONSET="$ICONSET" \
python3 - <<'PY'
import math
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import (
    QColor, QImage, QLinearGradient, QPainter, QPainterPath,
    QRadialGradient, QPen
)
from PySide6.QtWidgets import QApplication

root = Path(os.environ["ROOT"])
iconset = Path(os.environ["ICONSET"])

# The installer already depends on the project's PySide6 runtime.
app = QApplication.instance() or QApplication(sys.argv)

SIZE = 1024
image = QImage(SIZE, SIZE, QImage.Format_ARGB32_Premultiplied)
image.fill(QColor("#11161b"))

p = QPainter(image)
p.setRenderHint(QPainter.Antialiasing, True)

# Existing scanner splash palette.
bg = QLinearGradient(0, 0, 0, SIZE)
bg.setColorAt(0, QColor("#11161b"))
bg.setColorAt(0.55, QColor("#171c21"))
bg.setColorAt(1, QColor("#0f1418"))
p.fillRect(0, 0, SIZE, SIZE, bg)

# Existing scanner green glow.
halo = QRadialGradient(SIZE * 0.50, SIZE * 0.48, SIZE * 0.48)
halo.setColorAt(0, QColor(190, 214, 120, 34))
halo.setColorAt(0.55, QColor(190, 214, 120, 12))
halo.setColorAt(1, QColor(190, 214, 120, 0))
p.fillRect(0, 0, SIZE, SIZE, halo)

# One large clock, using the same visual language as MeltingClocksWidget.
x = SIZE * 0.50
y = SIZE * 0.43
r = SIZE * 0.32
melt = 0.62
angle = 28

p.save()
p.translate(x, y)

clock_halo = QRadialGradient(0, 0, r * 1.35)
clock_halo.setColorAt(0, QColor(205, 218, 154, 42))
clock_halo.setColorAt(1, QColor(205, 218, 154, 0))
p.setPen(Qt.NoPen)
p.setBrush(clock_halo)
p.drawEllipse(QPointF(0, 0), r * 1.35, r * 1.35)

face = QRadialGradient(-r * 0.25, -r * 0.30, r * 1.15)
face.setColorAt(0, QColor("#f1e7c8"))
face.setColorAt(0.72, QColor("#d8c99f"))
face.setColorAt(1, QColor("#a99972"))
p.setBrush(face)
p.setPen(QPen(QColor("#806f4d"), max(3, r * 0.045)))
p.drawEllipse(QPointF(0, 0), r, r)

melt_gradient = QLinearGradient(0, r * 0.50, 0, r * 1.72)
melt_gradient.setColorAt(0, QColor("#d8c99f"))
melt_gradient.setColorAt(1, QColor("#8f7e58"))
p.setBrush(melt_gradient)
p.setPen(Qt.NoPen)
p.drawRoundedRect(-r * 0.46, r * 0.55, r * 0.92, r * (0.72 + melt), r * 0.18, r * 0.18)
p.drawEllipse(QPointF(-r * 0.24, r * 1.18), r * 0.16, r * 0.25)
p.drawEllipse(QPointF(r * 0.22, r * 1.34), r * 0.13, r * 0.21)

p.setPen(QPen(QColor("#6c6046"), max(2, r * 0.025)))
for i in range(12):
    a = math.radians(i * 30 - 90)
    p.drawLine(
        QPointF(math.cos(a) * r * 0.78, math.sin(a) * r * 0.78),
        QPointF(math.cos(a) * r * 0.88, math.sin(a) * r * 0.88),
    )

a = math.radians(angle)
p.setPen(QPen(QColor("#3e392d"), max(3, r * 0.035), Qt.SolidLine, Qt.RoundCap))
p.drawLine(QPointF(0, 0), QPointF(math.cos(a) * r * 0.54, math.sin(a) * r * 0.54))

a2 = math.radians(angle * 12)
p.setPen(QPen(QColor("#514a3a"), max(2, r * 0.025), Qt.SolidLine, Qt.RoundCap))
p.drawLine(QPointF(0, 0), QPointF(math.cos(a2) * r * 0.72, math.sin(a2) * r * 0.72))

p.setBrush(QColor("#514a3a"))
p.setPen(Qt.NoPen)
p.drawEllipse(QPointF(0, 0), r * 0.06, r * 0.06)
p.restore()
p.end()

# macOS-style rounded icon silhouette.
rounded = QImage(SIZE, SIZE, QImage.Format_ARGB32_Premultiplied)
rounded.fill(Qt.transparent)
p = QPainter(rounded)
p.setRenderHint(QPainter.Antialiasing, True)
path = QPainterPath()
path.addRoundedRect(8, 8, SIZE - 16, SIZE - 16, 210, 210)
p.setClipPath(path)
p.drawImage(0, 0, image)
p.end()

sizes = [
    (16, "16x16"), (32, "16x16@2x"),
    (32, "32x32"), (64, "32x32@2x"),
    (128, "128x128"), (256, "128x128@2x"),
    (256, "256x256"), (512, "256x256@2x"),
    (512, "512x512"), (1024, "512x512@2x"),
]

for size, name in sizes:
    scaled = rounded.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    output = iconset / f"icon_{name}.png"
    if not scaled.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to save icon: {output}")
PY

if ! command -v iconutil >/dev/null 2>&1; then
    echo "ERROR: iconutil is required to build the macOS application icon."
    exit 1
fi

iconutil -c icns "$ICONSET" -o "$ICNS"
rm -rf "$ICONSET"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>ru</string>
	<key>CFBundleDisplayName</key>
	<string>Trader_7_12 Pro</string>
	<key>CFBundleExecutable</key>
	<string>Trader_7_12 Pro</string>
	<key>CFBundleIconFile</key>
	<string>Trader_7_12_Pro.icns</string>
	<key>CFBundleIdentifier</key>
	<string>com.trader712.pro</string>
	<key>CFBundleName</key>
	<string>Trader_7_12 Pro</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>1.4</string>
	<key>CFBundleVersion</key>
	<string>1.4</string>
	<key>LSUIElement</key>
	<false/>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
PLIST

plutil -lint "$CONTENTS/Info.plist"

touch "$APP"

echo "Installed: $APP"
echo "Native macOS launcher: OK"
echo "Branded one-clock icon: OK"
echo "BCS credential: stored in macOS Keychain"
echo "Launch Trader_7_12 Pro from Finder or Dock."
