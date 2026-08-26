import os

# BCS credentials are local-only. Never commit the refresh token to Git.
REFRESH_TOKEN = os.getenv("BCS_REFRESH_TOKEN", "")
