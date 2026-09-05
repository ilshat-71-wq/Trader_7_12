# PyInstaller spec for the read-only Trader_7_12 Pro macOS GUI.
# Build from repository root with scripts/build_mac_app.sh.

from PyInstaller.utils.hooks import collect_submodules


hiddenimports = [
    "api.bcs_api",
    "services.market_attention_scanner_service",
    "services.spot_universe_service",
    "services.history_candle_service",
    "services.market_session_service",
    "services.relative_strength_service",
]

# Keep package discovery deterministic for modules loaded by the scanner.
hiddenimports += collect_submodules("api")
hiddenimports += collect_submodules("services")


a = Analysis(
    ["Program/main.py"],
    pathex=["Program"],
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
    icon=None,
    bundle_identifier="com.ilshat.trader712pro",
    info_plist={
        "CFBundleDisplayName": "Trader_7_12 Pro",
        "CFBundleName": "Trader_7_12 Pro",
        "CFBundleShortVersionString": "2.2",
        "CFBundleVersion": "2.2",
        "LSMinimumSystemVersion": "12.0",
    },
)
