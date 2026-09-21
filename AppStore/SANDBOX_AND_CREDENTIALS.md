# Trader_7_12 Pro — App Sandbox Migration

## Current issue

The development configuration stores the BCS refresh token at:

`~/.config/Trader_7_12/bcs_refresh_token`

That path is not suitable for a Mac App Store sandboxed build.

The App Store build must store application data inside the app's sandbox container. Apple states that a sandboxed app has unrestricted read/write access to its own container and is otherwise restricted by entitlements.

## Required production change

Migrate BCS credential storage to an application-data location inside the sandbox container.

Preferred implementation:
- use a macOS application-data API such as Qt/PySide6 QStandardPaths with the application-data location;
- keep the existing BCS token semantics;
- preserve 0600-style protection where applicable;
- do not write refresh tokens to arbitrary home-directory paths;
- do not commit credentials.

A future hardening pass may move the refresh token to the macOS Keychain, but that is not required to establish the basic sandbox-compatible storage model.

## Required entitlements

Minimum expected App Store entitlements:

- `com.apple.security.app-sandbox = true`
- `com.apple.security.network.client = true`

Do not request broad file-system permissions unless a real product feature requires them.

The application does not need access to:
- Contacts
- Calendar
- Camera
- Microphone
- Location
- Photos
- Music
- Movies
- Downloads
- Full disk access

unless a future feature explicitly adds such a requirement.

## Network

Trader_7_12 Pro requires outbound HTTPS/TCP access to its configured market-data services. Apple documents `com.apple.security.network.client` for outgoing network connections.

## Validation

After the Store build is signed:

```bash
codesign --verify --deep --strict --verbose=2 "Trader_7_12 Pro.app"
codesign -d --entitlements :- "Trader_7_12 Pro.app"
```

Then launch the signed app and verify:
- token can be saved;
- token can be read on the next launch;
- BCS requests work;
- MOEX requests work;
- no sandbox denial prevents normal operation.
