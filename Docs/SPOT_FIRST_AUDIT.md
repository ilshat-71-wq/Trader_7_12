# SPOT-first architecture audit

Date: 2026-08-26
Branch: `main`

## Result

The live pipeline is correctly deriving `signal_state` from SPOT setup and trigger. `futures_confirmation` is explicitly marked `NOT_APPLICABLE` / `MAPPING_ONLY` in `MorningTradingPipelineService` and is not used for ranking or readiness.

One remaining architectural dependency was found in `TwoPhaseFuturesMorningRadarService`:

1. the two-phase scanner calls `_select_current_contracts()` before SPOT FAST screening;
2. `_select_current_contracts()` rejects contracts with missing expiry and contracts expiring within three days;
3. the deep stage then calls `FuturesContractSelectorService.select()` before the SPOT result reaches the pipeline.

Therefore futures data is still capable of preventing a SPOT candidate from reaching the SPOT setup/readiness stage. This is a **mapping/universe dependency**, not futures confirmation, but it is inconsistent with the strict SPOT-first passport wording.

## Canonical chain

`FAST SPOT SCREEN -> DEEP SPOT H1/RS/M5 -> SETUP/TRIGGER -> READINESS -> FUTURES MAPPING`

The following must remain SPOT-only:

- direction;
- relative strength;
- event-risk exclusion;
- H1 structural context;
- M5 setup;
- entry trigger;
- READY / CONFIRMED state;
- opportunity ranking.

Futures may only provide a reference mapping after a base asset has already qualified.

## Legacy paths still requiring cleanup

- `historical_universe_replay_service.py` still treats futures confirmation as the event that defines `trade_ready_time` and historical ranking.
- `morning_replay_service.py` still uses `SetupEngine`, while the live SPOT-first path uses `SpotFirstPullbackService` / `InstrumentMorningRadarService`. This creates two setup implementations.
- `futures_confirmation_service.py` should remain available for optional execution-stage validation, but must not participate in SPOT watchlist eligibility or ranking.
- `futures_trade_candidate_service.py` is still named and shaped around futures candidates even though the current pipeline treats them as SPOT opportunity records with futures mapping fields.

## Security finding

`Program/config.py` contained a BCS refresh token committed to the repository. The token has been removed from the working tree and `config.py` is now configured to read `BCS_REFRESH_TOKEN` from the environment. `Program/.gitignore` now ignores local `config.py` and `.env` files.

The exposed BCS refresh token must be **revoked/rotated immediately** at the BCS side. Removing it from the latest commit does not invalidate a credential that was already present in Git history.

## Next safe refactor

Refactor the two-phase scanner so that it operates on a SPOT universe first and attaches/selects a futures mapping only after SPOT ranking. Then migrate historical replay to the same canonical `SpotFirstPullbackService` setup implementation and make futures confirmation purely diagnostic/optional.
