# Trader_7_12 Pro — App Store Release Checklist

## A. Product / legal gate

- [ ] Confirm the submitting legal entity.
- [ ] Confirm the developer account type: individual or organization.
- [ ] Confirm EU DSA trader status.
- [ ] Confirm financial-app eligibility under current Apple App Review Guidelines.
- [ ] Confirm all required financial licenses/permissions for every selected storefront, if applicable.
- [ ] Confirm ownership/permission for all third-party data, trademarks, and content.

## B. App identity

- [ ] Bundle ID: com.ilshat.trader712pro
- [ ] App name: Trader_7_12 Pro
- [ ] Version: 2.4.3
- [ ] Build string: set by final release process and increment for every uploaded build.
- [ ] SKU: TRADER712PRO-MAC
- [ ] Primary language: English (U.S.)
- [ ] Primary category: Finance
- [ ] Secondary category: Utilities
- [ ] Copyright completed.

## C. Sandbox / signing

- [ ] App Sandbox entitlement enabled.
- [ ] Outgoing network client entitlement enabled.
- [ ] Local credential storage migrated into the app container.
- [ ] No temporary exception entitlements unless specifically justified and accepted by Apple.
- [ ] Distribution signing identity created/available.
- [ ] App Store provisioning profile created/available.
- [ ] Final bundle signed after all nested executables/libraries are in place.
- [ ] Signature verified with codesign --verify --deep --strict.
- [ ] Entitlements verified with codesign -d --entitlements :-.
- [ ] Final build tested after signing; do not modify the bundle after signing.

## D. Build / QA

- [ ] 145+ project tests pass.
- [ ] git diff --check passes.
- [ ] No Cyrillic in user-facing UI.
- [ ] Clean-machine launch test.
- [ ] BCS connection test.
- [ ] MOEX market-data test.
- [ ] Spot Radar test.
- [ ] Futures OI test.
- [ ] Incomplete-data behavior test.
- [ ] No synthetic fallback test.
- [ ] App Sandbox violation log checked.
- [ ] No crashes on supported macOS versions.
- [ ] Final version/build numbers verified.

## E. App Store Connect metadata

- [ ] App name.
- [ ] Subtitle.
- [ ] Promotional text.
- [ ] Description.
- [ ] Keywords <= 100 bytes.
- [ ] Support URL with real contact information.
- [ ] Privacy Policy URL.
- [ ] Marketing URL if used.
- [ ] Copyright.
- [ ] Age rating questionnaire.
- [ ] Content rights.
- [ ] Accessibility information if applicable.
- [ ] App Review contact: name, email, international phone.
- [ ] App Review notes.
- [ ] Demo/test access if required.
- [ ] Export compliance.
- [ ] Pricing.
- [ ] Tax category.
- [ ] Availability / storefronts.

## F. Visual assets

- [ ] Mac icon accepted by App Store Connect.
- [ ] Minimum 1 Mac screenshot.
- [ ] Recommended 4–6 high-quality screenshots.
- [ ] Screenshot dimensions match Apple's current Mac specification.
- [ ] Screenshots show the actual running app.
- [ ] No fake data presented as live data.
- [ ] No unsupported marketing claims.
- [ ] No transparent/alpha channel in screenshots.

## G. Release

- [ ] Upload final build.
- [ ] Resolve any Invalid Binary / Missing Compliance status.
- [ ] TestFlight internal testing.
- [ ] External TestFlight review if needed.
- [ ] App Review submission.
- [ ] Choose manual release initially.
- [ ] After approval, release manually.
- [ ] Verify product page in selected storefronts.
