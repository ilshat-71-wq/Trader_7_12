# Trader_7_12 Pro — Mac App Store Release Package

Release baseline: **2.4.3**  
Source commit: **a1e979d3f1395ca464fc3f5853a43f9983607ab6**  
Bundle ID: **com.ilshat.trader712pro**  
Platform: **macOS**  
Build system: **PyInstaller onedir + macOS .app**

## Purpose

This directory contains the material required to hand the project to the Apple Developer account holder who will create the App Store build, sign it, upload it to App Store Connect, run TestFlight, and submit it for App Review.

No Apple certificates, private keys, provisioning profiles, API keys, BCS credentials, or other secrets belong in this repository.

## Current product

Trader_7_12 Pro is a read-only market-information and market-intelligence application for Moscow Exchange markets.

It provides:
- Market Radar for the Russian equity universe.
- Futures intelligence with Open Interest, OI change, turnover, liquidity, Base Asset change, money flow, signals, probability, and entry zones.
- Real-data-only behavior: missing data remains missing.
- No order execution.
- No brokerage account management.
- No synthetic prices, synthetic candles, or perpetual-futures fallback.

## Current engineering baseline

- 145 tests passing at release preparation.
- International English user interface.
- Bundle version 2.4.3.
- Current development build is ad-hoc signed only and is **not** an App Store binary.
- App Store distribution requires App Sandbox and Apple distribution signing.

## Apple account holder must provide

1. Apple Developer Program membership with authority to distribute the app.
2. Team ID.
3. App Store Connect access.
4. Bundle ID registration for `com.ilshat.trader712pro`.
5. Apple distribution signing identity / App Store provisioning profile, as appropriate for the chosen external build workflow.
6. App Store Connect app record.
7. Legal developer/company name and copyright holder.
8. Support URL with real contact details.
9. Privacy Policy URL.
10. EU DSA trader information, if applicable.
11. App Review contact details in international phone format.
12. A review-access plan for the BCS-backed data connection.

## Important App Review eligibility check

Apple's current App Review Guidelines state that apps used for financial trading, investing, or money management should be submitted by the financial institution performing those services and have the necessary licensing and permissions in the locations where the app is available. The current product includes trading-oriented market intelligence and Long/Short signals, so this point must be reviewed by the account holder before submission.

Do **not** describe the app as a brokerage, exchange, execution platform, or licensed financial service unless that is legally true.

## Release sequence

1. Resolve the App Review eligibility/legal-entity question.
2. Register the Bundle ID.
3. Prepare App Sandbox entitlements.
4. Migrate local BCS credential storage into the app sandbox container.
5. Build and sign the App Store version.
6. Verify entitlements and signatures.
7. Test the signed build on a clean Mac.
8. Create the App Store Connect record.
9. Enter metadata, privacy, age rating, pricing, availability, and DSA information.
10. Upload the build.
11. Test with TestFlight.
12. Complete App Review information.
13. Submit for review.
14. Release manually after approval.

## Do not submit the current ad-hoc build

The installed 2.4.3 build is a development/release-test artifact. The final App Store binary must be rebuilt and distribution-signed by the account holder.
