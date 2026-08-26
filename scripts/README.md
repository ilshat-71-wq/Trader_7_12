# macOS launcher

The project includes two local-only helpers:

- `launch_trader_7_12.command` — starts the current application from the repository.
- `install_trader_7_12_app.command` — creates `~/Applications/Trader_7_12 Pro.app` on the Mac.

BCS credentials are intentionally not stored in this repository. The app inherits `BCS_REFRESH_TOKEN` from the user's local environment.
