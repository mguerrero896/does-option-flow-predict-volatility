# Gate 5 — Foundational PIT assumptions, end to end (v1)

Started 2026-08-17. Code: `scripts/run_gate5_bar_reconciliation.py` (5.1),
`scripts/uw_latency_{collector,verify,reconcile}.py` + `scripts/register_uw_latency_tasks.ps1`
(5.2/5.3). Artifacts: `artifacts/gate5_pit/` and `MDS650_EXTERNAL_ROOT/uw_latency/`.
Zero model reads; zero sealed-cohort access; decision-52 compliant.

## 5.1 — FMP bar semantics (A001): MEASURED, resolved

Cross-provider reconciliation of the same one-minute bars from FMP and the
Polygon-compatible Massive aggregates endpoint (new bounded method
`MassiveProvider.stock_minute_aggregates`), over ten stratified sessions spanning the
C5 (2024), C4 (mid-2025), C6 and 2026 development windows, six outcome assets:

| Alignment | Median of per-cell median relative close differences |
|---|---|
| **Identical labels (same_label)** | **3.1e−06 (near-exact)** |
| FMP shifted +1 minute | 3.66e−04 |

Both providers label one-minute bars identically; same-label agreement is two orders
of magnitude tighter than the shifted convention, with many 2025/2026 cells exactly
equal.
Combined with Gate 3 (reconstructed 30-minute RV matches the frozen `b0_rv_30m_lag`
with log-correlation 1.0000 under shift 0), registered assumption A001 is now an
empirically pinned fact: the pipeline's convention is correct, with an independent
second source across all evaluation eras. A standing tripwire
(`tests/test_gate5_bar_reconciliation_contract.py`) fails the suite if a future
re-acquisition breaks this agreement.

## 5.2/5.3 — UW `created_at` latency campaign: RECONCILED_PARTIAL

**Lifecycle authority refreshed 2026-09-02; hourly-latency correction dated 2026-09-01.** This section supersedes the 2026-08-18
`RUNNING (unattended)` label and its promise that five reconciled sessions would by
themselves permit a claim upgrade. The machine authority is
`artifacts/gate5_pit/uw_latency_campaign_state_20260902_v4.json`; the aggregate and
anomaly disposition are in the two sibling versioned artifacts. The current inventory
contains 12 collected sessions, seven reconciled sessions and five collected but not yet
reconciled sessions. All 2026-09-01 artifacts and the 2026-09-02 v1/v2/v3 pairs remain
immutable historical snapshots; v4 records the matured 2026-08-25 reconciliation without
editing them.

The latency half produced a measured result. Across all seven reconciliations, 2,846 of
2,846 live flow alerts had contract-window tape support (100%). After excluding only the
2026-08-21 contaminated latency distribution, the median of the six session p50 values
is 30.853676 seconds. For 2026-08-17, p10/p50/p90/p99 were
5.001470/29.500069/53.133085/59.831160 seconds. Median-of-session-median latency by
asset was 25.331907–35.564361 seconds. These session-level measurements alone do not
establish that a fixed receipt buffer holds at the opening.

The hourly overlay computes local `receipt_utc - created_at`, assigns the NY hour from
`receipt_utc`, retains only records whose `start_time` belongs to that NY session, and
keeps the first valid receipt per record. It contains 2,196 first receipts from the six
clean sessions; 2026-08-21 remains excluded under its registered disposition. The full
receipt-hour distribution is:

| Receipt hour NY | n | Sessions | p10 s | p50 s | p90 s | p99 s | >60 s | >120 s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 480 | 6 | 4.151851 | 33.311092 | 54.743226 | 60.249050 | 8 | 0 |
| 10 | 587 | 6 | 6.130806 | 31.500023 | 55.283491 | 61.351718 | 15 | 0 |
| 11 | 360 | 5 | 6.257217 | 32.997296 | 57.220070 | 61.233538 | 18 | 0 |
| 12 | 244 | 5 | 5.415984 | 28.995449 | 49.336543 | 59.452789 | 2 | 0 |
| 13 | 187 | 5 | 6.090277 | 31.143349 | 54.436570 | 59.688000 | 0 | 0 |
| 14 | 133 | 5 | 6.198958 | 31.302216 | 55.819877 | 116.894217 | 3 | 2 |
| 15 | 202 | 3 | 3.857133 | 24.293230 | 54.251838 | 60.824584 | 5 | 0 |
| 16 | 3 | 3 | 25.267928 | 32.500017 | 49.212158 | 52.972389 | 0 | 0 |

**Opening-cutoff answer.** The opening hour contains 480 first receipts across all six
clean sessions. Eight exceed 60 seconds, 8/480 (1.67%), and its p99 is 60.249050 seconds;
0/480 exceed 120 seconds. Therefore the registered 60-second UW availability buffer —
the B2 timing leg used alongside the separately measured FMP+1-minute bar convention —
does not hold as a strict conservative bound at the NY opening in this sample. The
120-second sensitivity does hold at the opening in these six sessions, but not as an
all-day strict bound: two of 133 receipts in hour 14 exceed 120 seconds. Six sessions and
480 opening receipts are sufficient to falsify a zero-exceedance claim in the observed
sample, not to certify a universal future-session guarantee. This changes no historical
panel, mask, estimate or verdict; `created_at` remains a proxy rather than proven client
availability.

The hour-by-asset table is published only where both `n >= 30` and at least three
sessions contribute. At the opening this supports AAPL (58), META (41), NVDA (229) and
TSLA (99). AMZN (26 across six sessions) and MSFT (27 across five) are reported as
insufficient rather than assigned unstable quantiles. The v4 artifact contains every
supported hour-by-asset quantile and every insufficient-cell count.

The 2026-08-21 p50 of 4,294.886974 seconds was a collector restart/replay duplication,
classification `COLLECTOR_RESTART_REPLAY_DUPLICATION`, rather than a collector stop,
clock shift or measured provider degradation. Its first-receipt p50 was 34.172432
seconds. It is excluded from latency aggregation under
`EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT`; its 636/636 support observations remain in the
contract-window support rate. A ten-times-peer p50 guard now routes this order of
deviation through the existing popup and `logs/UW_LATENCY_ALERT.txt` path.

The hourly table is a custody-safe aggregate derived from the licensed observation logs;
no provider row, identifier, price, premium or external absolute path is emitted. Exact
source hashes bind the aggregate to the six logs. A live freshness contract regenerates
the snapshot from the authorized `uw_latency/sessions` inventory and fails on any byte
divergence. Because the campaign is still moving, drift requires a new dated immutable
snapshot; v1–v3 are not overwritten.

The backfill/revision half is not identifiable under this design. Every reconciliation
is `PROXY_ONLY_CROSS_CHANNEL`: live observations are aggregate alerts while the later
tape contains individual trades. Backfill remains `None` for
`CROSS_CHANNEL_NOT_IDENTIFIABLE`; revision remains `None` for
`AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE`. More sessions cannot repair a
cross-channel estimand. The count condition (at least five reconciliations) is met, but
the content condition is not; no upgrade to `VALID_UNDER_REGISTERED_TIMING_ASSUMPTIONS`
follows.

## What this retires (and what it does not)

- A001 (bar semantics): retired — measured, two providers, three eras.
- A002 (`created_at` as availability): remains `PROXY_ONLY_CROSS_CHANNEL`. Live receipt
  latency is measured, but the 60-second buffer is not a strict opening bound in the
  observed sample; the 120-second sensitivity has no opening exceedance but has two
  hour-14 exceedances. Backfill and revision remain non-identifiable across the two
  channels. PITV22-C002 therefore remains `PROXY_ONLY`; historical tapes remain
  assumption-based.
