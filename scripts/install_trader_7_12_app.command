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

echo "Installed: $APP"
echo "Native macOS launcher: OK"
echo "BCS credential: stored in macOS Keychain"
echo "Launch Trader_7_12 Pro from Finder or Dock."
