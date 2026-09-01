# Gate 5 UW latency campaign closeout v1

> **SUPERSEDED FOR CURRENT USE (2026-09-01).** This frozen-snapshot closeout is retained
> as historical context. The current hourly correction and authority are in
> `docs/gate5_pit_foundations_v1.md` and the sibling `uw_latency_campaign_20260902_v4`
> aggregate/state artifacts. The v1 artifacts were not modified.

**As of 2026-09-01: `RECONCILED_PARTIAL`. Target-blind operational timing evidence
only. No target, forecast, loss, model fit or sealed cohort was read.**

## Authority and custody

| Role | Versioned authority | Semantic SHA-256 |
| --- | --- | --- |
| Campaign aggregate | `artifacts/gate5_pit/uw_latency_campaign_20260901_v1.json` | `412a0645b9ffe635cefc905e897150b66f7bda5c1bddcf30fe8e70ee242268eb` |
| Lifecycle state | `artifacts/gate5_pit/uw_latency_campaign_state_20260901_v1.json` | `49bd39cbec49cd497724956ec638315f0a3314c771aa5ef971583896b3f9b96f` |
| 2026-08-21 anomaly | `artifacts/gate5_pit/uw_latency_anomaly_20260821_v1.json` | `7bec93a37b89e27308d0f4aa21b19edee326b46d82ff51ea1d49c3ead8d6108a` |

The aggregate was built only from six session-level `reconciliation.json` files,
dated 2026-08-17 through 2026-08-21 and 2026-08-24. The anomaly audit used safe session
metadata plus structural counts and timestamps from the licensed observation log; it
did not emit, quote or version any provider row or row-level field value. Repository
artifacts contain logical paths and hashes only, never an external absolute path.

## Harvested result

| Quantity | Result |
| --- | ---: |
| Collected / reconciled / unreconciled sessions | 11 / 6 / 5 |
| Contract-window support | 2,418 / 2,418 (100%) |
| Unmatched live alerts | 0 |
| Latency sessions retained / excluded | 5 / 1 |
| Median of retained session p50 values | 29.500069 s |

For the first reconciled session, p10/p50/p90/p99 were
5.001470/29.500069/53.133085/59.831160 seconds. Median-of-retained-session medians by
asset were AAPL 30.191226, AMZN 29.750699, META 29.807567, MSFT 32.370149, NVDA
30.684475 and TSLA 24.130425 seconds.

NY-hour aggregation is the one declined subcomponent of 6A. The authorized
`reconciliation.json` inputs do not persist it, while reconstructing it would require
reading licensed rows outside the harvest contract. The artifact fails closed with
`NOT_AVAILABLE_IN_RECONCILIATION_JSON` and reason
`SESSION_RECONCILIATIONS_DID_NOT_PERSIST_NY_HOUR_AGGREGATES; CAMPAIGN_HARVEST_MAY_NOT_READ_LICENSED_ROW_DATA`.

## Anomaly disposition

The 2026-08-21 session had an all-receipt p50 of 4,294.886974 seconds, 145.589 times
the clean peer median. Safe structural evidence showed 4,214 lines, 1,836 distinct
identities and 2,378 duplicate lines; 1,200 distinct identities belonged to earlier
dates. The first-receipt p50 for the in-session identities was 34.172432 seconds.
Heartbeat, capture and collector-summary metadata showed normal completion and zero
poll errors.

The evidence supports `COLLECTOR_RESTART_REPLAY_DUPLICATION`. It does not support a
collector stop, clock shift or provider degradation. The registered disposition is
`EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT`: exclude this session only from the latency
distribution, preserve its 636/636 support count, and retain the source evidence. A
ten-times-peer p50 guard uses the existing popup plus `logs/UW_LATENCY_ALERT.txt` path.

## Identifiability boundary

All six reconciliations are `PROXY_ONLY_CROSS_CHANNEL`. The live channel aggregates
alerts; the later channel represents individual trades. Consequently:

- backfill is `None`, reason `CROSS_CHANNEL_NOT_IDENTIFIABLE`;
- revision is `None`, reason
  `AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE`;
- collecting more sessions under the same design cannot identify either quantity;
- A002 and PITV22-C002 remain proxy-only; no scientific eligibility state is promoted.

## Reproduction boundary

`scripts/audit_uw_latency_session_anomaly.py` reproduces the structural anomaly
evidence. `scripts/harvest_uw_latency_campaign.py` accepts six explicit
`reconciliation.json` paths and the 11 session directories, then writes new files only;
it refuses overwrite conflicts. The state and prose contracts derive from the
artifacts, and the canonical-state generator registers their hashes. Licensed raw logs
and tapes remain external and are not publication inputs.
