import os
from pathlib import Path

# BCS credentials are local-only. Never commit the refresh token to Git.
#
# Development / non-sandbox builds keep the historical location for backward
# compatibility. Mac App Store builds use QStandardPaths after QApplication
# has initialized, so the credential is stored inside the app's sandbox
# container.
LEGACY_BCS_TOKEN_FILE = Path.home() / ".config" / "Trader_7_12" / "bcs_refresh_token"


def _sandbox_token_file():
    try:
        from PySide6.QtCore import QCoreApplication, QStandardPaths

        app = QCoreApplication.instance()
        if app is not None:
            app_data = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            if app_data:
                return Path(app_data) / "bcs_refresh_token"
    except Exception:
        pass
    return None


def _token_file():
    sandbox_file = _sandbox_token_file()
    if sandbox_file is not None:
        return sandbox_file
    return LEGACY_BCS_TOKEN_FILE


# Backward-compatible public name for code/tests that inspect the path.
BCS_TOKEN_FILE = LEGACY_BCS_TOKEN_FILE


def get_refresh_token():
    token = os.getenv("BCS_REFRESH_TOKEN", "").strip()
    if token:
        return token
    try:
        return _token_file().read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def save_refresh_token(token):
    token = str(token or "").strip()
    if not token:
        return False
    try:
        token_file = _token_file()
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(token + "\n", encoding="utf-8")
        token_file.chmod(0o600)
        return True
    except OSError:
        return False


# Backward-compatible value for code that imports REFRESH_TOKEN directly.
REFRESH_TOKEN = get_refresh_token()
