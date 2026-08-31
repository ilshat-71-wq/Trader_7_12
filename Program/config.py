import os
from pathlib import Path

# BCS credentials are local-only. Never commit the refresh token to Git.
# Priority: explicit environment variable, then a user-local secure file.
BCS_TOKEN_FILE = Path.home() / ".config" / "Trader_7_12" / "bcs_refresh_token"


def get_refresh_token():
    token = os.getenv("BCS_REFRESH_TOKEN", "").strip()
    if token:
        return token
    try:
        return BCS_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def save_refresh_token(token):
    token = str(token or "").strip()
    if not token:
        return False
    try:
        BCS_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        BCS_TOKEN_FILE.write_text(token + "\n", encoding="utf-8")
        BCS_TOKEN_FILE.chmod(0o600)
        return True
    except OSError:
        return False


# Backward-compatible value for code that imports REFRESH_TOKEN directly.
REFRESH_TOKEN = get_refresh_token()
