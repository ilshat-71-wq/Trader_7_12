#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Applications/Trader_7_12 Pro.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RES="$CONTENTS/Resources"

mkdir -p "$MACOS" "$RES"

cat > "$MACOS/Trader_7_12 Pro" <<EOF
#!/bin/zsh
set -euo pipefail
ROOT="$ROOT"
cd "\$ROOT"
export PYTHONPATH="\$ROOT/Program"
exec /usr/bin/env python3 "\$ROOT/Program/main.py"
EOF
chmod +x "$MACOS/Trader_7_12 Pro"

cat > "$CONTENTS/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key><string>ru</string>
  <key>CFBundleDisplayName</key><string>Trader_7_12 Pro</string>
  <key>CFBundleExecutable</key><string>Trader_7_12 Pro</string>
  <key>CFBundleIdentifier</key><string>com.trader712.pro</string>
  <key>CFBundleName</key><string>Trader_7_12 Pro</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
</dict>
</plist>
EOF

open "$APP"
echo "Installed: $APP"
