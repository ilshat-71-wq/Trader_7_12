# Trader_7_12 Pro — App Store Build Environment

## Important current requirement

The Mac App Store build must be produced with a currently accepted Apple toolchain/SDK.

Apple's current App Store Connect release notes show support for macOS builds made with Xcode 26.x and later SDKs, and current 2026 submissions also support Xcode 27/macOS 27 SDK combinations.

The development Mac previously used for Trader_7_12 Pro reports:

```
Xcode 16.4
Build version 16F6
```

That toolchain is **not the target toolchain for the final 2026 App Store build**.

## Recommended release machine

Use the Apple Developer account holder's Mac with:
- Xcode 26.x or newer supported release;
- current macOS version compatible with that Xcode;
- current Python 3.x environment;
- PySide6;
- PyInstaller;
- the Trader_7_12 repository at the intended release commit.

Before building, verify:

```bash
xcodebuild -version
xcode-select -p
python3 --version
python3 -c 'import PyInstaller, PySide6; print("PyInstaller/PySide6 OK")'
```

## Do not copy the existing ad-hoc .app into App Store Connect

The current 2.4.3 app was built as:

- PyInstaller onedir;
- ad-hoc signed;
- no Team ID;
- no App Sandbox entitlement.

It is a development/release-test artifact only.

The App Store binary must be rebuilt with the final sandbox-compatible code and signed for App Store distribution by the account holder.

## Build provenance

Target source baseline:

`a1e979d3f1395ca464fc3f5853a43f9983607ab8`

Bundle ID:

`com.ilshat.trader712pro`

Marketing version:

`2.4.3`

The build number must be unique for each App Store Connect upload.

## Architecture

Keep the architecture policy explicit. If the product continues to support macOS 12, verify that the final PyInstaller payload contains every architecture required by the chosen deployment target.

If the release intentionally drops Intel support, raise the minimum macOS version accordingly and verify that decision against Apple's current Mac App Store options.

## Final validation

Before upload:

```bash
codesign --verify --deep --strict --verbose=2 "Trader_7_12 Pro.app"
codesign -d --entitlements :- "Trader_7_12 Pro.app"
codesign -dvvv "Trader_7_12 Pro.app" 2>&1 | grep -E "Identifier=|TeamIdentifier=|Authority=|Signature="
```

Then upload through a supported Apple workflow such as Xcode Organizer or Transporter.
