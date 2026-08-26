#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Applications/Trader_7_12 Pro.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"

cat > "$MACOS/Trader_7_12 Pro" <<LAUNCHER
#!/bin/zsh
set -euo pipefail
ROOT="$ROOT"
cd "\$ROOT"
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"
export PYTHONPATH="\$ROOT/Program"

if [[ -z "\${BCS_REFRESH_TOKEN:-}" ]]; then
    if [[ -f "\$HOME/.trader_7_12_env" ]]; then
        source "\$HOME/.trader_7_12_env"
    fi
fi

exec /usr/bin/env python3 "\$ROOT/Program/main.py"
LAUNCHER
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
	<string>1.2</string>
	<key>CFBundleVersion</key>
	<string>1.2</string>
	<key>LSUIElement</key>
	<false/>
</dict>
</plist>
PLIST

plutil -lint "$CONTENTS/Info.plist"

echo "Installed: $APP"
echo "Launch Trader_7_12 Pro from Finder or Dock."
