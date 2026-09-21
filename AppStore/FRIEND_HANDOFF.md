# Trader_7_12 Pro — Six-Step Apple Release Handoff

This is the operational handoff for the Apple Developer account holder.

## 1. Sandbox-compatible credentials

Already implemented in `Program/config.py`.

Development builds keep the legacy token path. When a QApplication exists, the app uses Qt's `QStandardPaths.AppDataLocation`, which is appropriate for application data inside the sandbox container.

Apple requires App Sandbox for Mac App Store distribution and gives the sandboxed app full read/write access to its own container.

No token is committed to Git.

## 2. Store candidate build

Use the repository `main` branch and an Apple-supported Xcode/macOS toolchain.

The existing build script now has two modes:

Development:
```bash
bash scripts/build_mac_app.sh
```

Store/TestFlight candidate:
```export APPLE_CODESIGN_IDENTITY="YOUR APP STORE DISTRIBUTION IDENTITY"
export APP_STORE_PROVISIONING_PROFILE="/absolute/path/to/Mac_App_Store_Connect.provisionprofile"
export TRADER_BUILD_MODE=store

bash scripts/build_mac_app.sh
```

Optional architecture:
```export TRADER_TARGET_ARCH=arm64
```

or, if the installed universal2 Python/PyInstaller environment supports it:

```export TRADER_TARGET_ARCH=universal2
```

PyInstaller supports real macOS signing identities and an entitlements file during collection.

The script:
- runs tests;
- checks a clean Git tree;
- builds the same PyInstaller onedir app;
- signs collected code with the distribution identity;
- embeds the App Store provisioning profile before the final outer signature;
- signs the outer app;
- verifies recursively with `codesign --verify --deep --strict`.

Apple documents `Contents/embedded.provisionprofile` for macOS provisioning profiles and requires re-signing after the profile is embedded.

## 3. Distribution signing

The account holder must create/select:
- explicit App ID matching `com.ilshat.trader712pro`;
- Mac App Store Connect distribution profile;
- distribution certificate.

Apple's current workflow allows the account holder to create a Mac App Store Connect provisioning profile tied to the explicit App ID and distribution certificate.

Do not send private keys or certificates to the project owner.

Verify after build:

```bash
codesign -dvvv "dist/Trader_7_12 Pro.app" 2>&1 | grep -E "Identifier=|TeamIdentifier=|Authority=|Signature="

codesign -d --entitlements :- "dist/Trader_7_12 Pro.app"

codesign --verify --deep --strict --verbose=2 "dist/Trader_7_12 Pro.app"
```

Apple recommends signing nested code from the inside out and specifically advises against using `codesign --deep` for the signing operation; `--deep` is appropriate for recursive verification.

## 4. Clean Mac test

Before TestFlight:
- copy the signed app to `/Applications`;
- launch it;
- confirm Activity Monitor reports Sandbox = Yes;
- connect to BCS;
- confirm MOEX data;
- run Market Radar;
- run Futures OI;
- verify incomplete-data behavior;
- verify no token is written to `~/.config/Trader_7_12`;
- verify the token is stored under the app's sandbox application-data location;
- inspect Console for sandbox denials.

Apple documents Activity Monitor and `codesign -dvvv --entitlements -` as ways to verify App Sandbox.

## 5. TestFlight

Create the App Store Connect app record using:
- Name: Trader_7_12 Pro
- Bundle ID: com.ilshat.trader712pro
- SKU: TRADER712PRO-MAC

Upload the Store candidate through the supported Apple workflow.

TestFlight builds must have the appropriate provisioning profile. Apple's current provisioning-profile documentation states that TestFlight requires a profile even on macOS.

Test on a clean Mac with no development files or credentials.

Record:
- launch result;
- sandbox result;
- BCS authentication;
- Market Radar;
- Futures OI;
- network failures;
- incomplete data;
- quit/relaunch token persistence.

## 6. App Review

Before submission, complete:
- privacy policy URL;
- App Store metadata;
- age rating;
- export compliance;
- screenshots;
- support URL;
- review contact;
- review notes;
- pricing and availability;
- EU DSA trader information where applicable.

Apple requires a privacy policy URL for macOS apps.

Mac screenshots must use Apple's accepted Mac sizes; current App Store Connect documentation lists 1280×800, 1440×900, 2560×1600, or 2880×1800 at 16:10. One to ten screenshots can be uploaded.

### Critical financial-app gate

Apple's current App Review Guidelines say apps used for financial trading, investing, or money management should be submitted by the financial institution performing the service and have the necessary licensing and permissions. Apple also says apps facilitating derivatives/FOREX/CFD trading must be properly licensed where available.

Trader_7_12 Pro is read-only and does not execute orders, but it does present trading-oriented futures intelligence and Long/Short analytical signals. The submitting legal entity must therefore resolve this eligibility question with Apple before submission.

Do not misrepresent the product's functionality in App Store metadata or review notes.

## Final submission package

Send the account holder:
1. GitHub repository access or the repository archive.
2. This `AppStore/` directory.
3. The exact source commit used for the release.
4. Final screenshots captured from the real app.
5. Legal/support/privacy URLs and contact details.
6. Approved BCS review access if needed.

Never send:
- Apple private keys;
- Apple certificates with private keys;
- BCS production refresh tokens;
- personal passwords.
