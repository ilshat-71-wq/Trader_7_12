#!/bin/bash
set -euo pipefail

REPO="$HOME/Documents/Trader_7_12"
PLIST="$HOME/Library/LaunchAgents/com.ilshat.trader712.cloud.plist"
PYTHON_BIN="$(command -v python3)"
if [ -z "$PYTHON_BIN" ]; then echo "python3 not found"; exit 1; fi
LOG_DIR="$REPO/Cloud/logs"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ilshat.trader712.cloud</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>Cloud.app:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8080</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Background</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/cloud.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/cloud.stderr.log</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

plutil -lint "$PLIST"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/com.ilshat.trader712.cloud"
launchctl kickstart -k "gui/$(id -u)/com.ilshat.trader712.cloud"

echo "=== TRADER_7_12 CLOUD AUTOSTART INSTALLED ==="
echo "Morning Radar schedule: 07:00 07:15 07:30 08:00 09:00 09:45 09:50 MSK"
echo "Health: http://127.0.0.1:8080/health"
echo "Morning Radar: http://127.0.0.1:8080/v1/morning-radar"
