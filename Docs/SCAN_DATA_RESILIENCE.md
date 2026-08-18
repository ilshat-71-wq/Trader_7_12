# Scan data resilience

## Purpose

A temporary BCS network failure must not be presented to the user as `no candidates`.

The scanner distinguishes:

- valid market data with no candidate;
- incomplete market data for a required SPOT dependency;
- a recoverable transient request failure.

## Network policy

- General scanner metadata remains fail-fast for the 20–30 second target.
- Candle/history reads get a short bounded retry window because H1/D SPOT history is structurally important.
- No request is allowed to stall the whole scan for minutes.
- Missing required SPOT H1/D data prevents a candidate from being ranked, but the scan must expose the data problem instead of returning an empty result without explanation.

## Architecture

SPOT remains authoritative for trend, H1 structure and pullback/rebound context. Futures remain the tradable instruments.

Canonical mapping: `BMU6 -> BRENT1026`.

No order execution or automatic entry decisions are introduced.
