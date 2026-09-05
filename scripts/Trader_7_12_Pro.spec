# PyInstaller spec for the read-only Trader_7_12 Pro macOS GUI.
# Build from repository root with scripts/build_mac_app.sh.

import os

from PyInstaller.utils.hooks import collect_submodules


BUILD_COMMIT = os.environ.get("TRADER_BUILD_COMMIT", "unknown")
SPEC_DIR = os.path.abspath(SPECPATH)
PROJECT_ROOT = os.path.abspath(os.path.join(SPEC_DIR, ".."))
PROGRAM_DIR = os.path.join(PROJECT_ROOT, "Program")
MAIN_SCRIPT = os.path.join(PROGRAM_DIR, "main.py")
ICON_PATH = os.path.join(PROJECT_ROOT, "build", "Trader_7_12_Pro.icns")

hiddenimports = [
    "config",
    "api.bcs_api",
    "api.request_helper",
    "services.market_attention_scanner_service",
    "services.spot_universe_service",
    "services.history_candle_service",
    "services.market_session_service",
    "services.relative_strength_service",
]

hiddenimports += collect_submodules("api")
hiddenimports += collect_submodules("services")


a = Analysis(
    [MAIN_SCRIPT],
    pathex=[PROGRAM_DIR],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Trader_7_12_Pro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

app = BUNDLE(
    exe,
    name="Trader_7_12 Pro.app",
    icon=ICON_PATH,
    bundle_identifier="com.ilshat.trader712pro",
    info_plist={
        "CFBundleDisplayName": "Trader_7_12 Pro",
        "CFBundleName": "Trader_7_12 Pro",
        "CFBundleShortVersionString": "2.2.3",
        "CFBundleVersion": "2.2.3",
        "CFBundleSourceCommit": BUILD_COMMIT,
        "LSMinimumSystemVersion": "12.0",
    },
)
