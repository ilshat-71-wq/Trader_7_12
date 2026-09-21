# Trader_7_12 Pro — Cloud Market Data Engine

## Purpose

The cloud engine changes the distribution model from:

    BCS -> every desktop client -> every client runs its own scan

to:

    BCS/MOEX -> one Cloud Market Data Engine -> many desktop clients

The existing market-information and Futures OI pipelines remain the source of
truth. The cloud layer caches one real-data snapshot and distributes it through
HTTP and WebSocket. No synthetic prices, no participant-identity claims, and
no order execution are introduced.

## Current API

- `GET /health` — process health, no authentication.
- `GET /v1/status` — engine state and last scan information.
- `GET /v1/snapshot` — latest complete market snapshot.
- `POST /v1/scan` — explicit refresh.
- `WS /v1/stream` — push every newly generated snapshot.

Set `CLOUD_CLIENT_API_KEY` to enable Bearer authentication for HTTP and
WebSocket clients. Leave it empty for local development only.

## Data flow

The cloud process uses one BCS read-only refresh token from
`BCS_REFRESH_TOKEN`. That credential must never be placed in the desktop app
or committed to Git.

Each scan runs the existing:

1. Market Information Radar
2. Futures OI
3. BCS 30m money flow + current order book

The result is held in memory as an immutable versioned snapshot. One scan can
therefore serve hundreds or thousands of connected clients without repeating
the market-data requests.

## Local run

From the repository root:

    python3 -m venv .venv-cloud
    source .venv-cloud/bin/activate
    pip install -r Cloud/requirements.txt
    export BCS_REFRESH_TOKEN='...'
    export CLOUD_CLIENT_API_KEY='...'
    PYTHONPATH=Program:. python3 -m cloud.app

Then:

    curl http://127.0.0.1:8080/health
    curl -H "Authorization: Bearer $CLOUD_CLIENT_API_KEY" http://127.0.0.1:8080/v1/status

## Production boundary

This first cloud stage deliberately does not alter the desktop UI. The next
client stage will add a provider abstraction:

    CloudProvider -> cached cloud snapshot
    LocalBCSProvider -> existing direct BCS mode

That lets the same application support a staged migration and keeps the
working local BCS path available during validation.

Before commercial redistribution of market data, confirm the applicable BCS
market-data/API agreement and redistribution rights. The cloud architecture
must not be treated as permission to redistribute a provider feed.

## Operating policy

- One scanner process per market-data credential.
- No overlapping scans.
- Last known good snapshot remains available when a refresh fails.
- Exact scanner diagnostics are preserved.
- Missing real data remains missing; the engine does not invent replacements.
- Read-only: no order placement.
