# Phase 4A — Scientific design freeze

> **Historical Phase 4A freeze, English translation.** This record describes its
> original authority. The current models, inference rules and horizons are resolved
> in [RP4 v4](rp4/specification_v4.md) and the [current decisions](research_decisions_current.md).
> The [original](archive/public_refresh_baseline/docs__phase4a_scientific_design_freeze_v1.md.original)
> is preserved for provenance; this translation changes no frozen method.

Status at this review: **PARTIAL / local-only**. The design was frozen as a research
convention; backfill, training and out-of-sample evaluation were not authorized by it.

## Question and estimand

> “Do continuous unusual options-activity features improve out-of-sample RV30
> forecasting beyond information contained in the underlying market and
> conventional options-state variables?”

The claim is incremental and predictive; it is neither causal nor a claim about
trader intent.

The planned estimand is the expected loss difference between B1Q and B2 on the
same origins, assets and dates surviving the PIT filters. At this freeze the
evaluation did not yet exist and lay outside the authorized scope.

## Unit and target

A row is an asset `i`, a regular XNYS session and a five-minute origin `t`.
The target is unannualized RV30:

```text
r(i,t+j) = ln(C(i,t+j) / C(i,t+j-1)), j=1,...,30
RV30(i,t:t+30) = sum_j r(i,t+j)^2
```

Exactly 31 prices are required: the anchor close available at `t` and the
30 future closes. This historical implementation contains RV30, not RV10.

## Frozen design

| Decision | Status | Source | Evidence | Assumption class | Consequence |
|---|---|---|---|---|---|
| Horizon | PASS | recorded decision and contract | `src/mds650/targets.py`; `artifacts/common_sample/common_matrix_profile_v1.json` | HUMAN_APPROVED_RESEARCH_ASSUMPTION | RV10 is not implemented. |
| Origin | PASS | project contract | `specs/001-pit-options-rv30/` | PROVIDER_CONFIRMED_FACT for session calendar; design convention for five-minute grid | `asset|session_date|forecast_origin_utc` is the key. |
| FMP availability | PARTIAL | authenticated probe + owner approval | `artifacts/pit/fmp_bar_semantics_v3.json` | HUMAN_APPROVED_RESEARCH_ASSUMPTION | raw+1m primary; raw+2m sensitivity; no provider claim. |
| UW availability | PARTIAL | retained Full Tape and documentation | `artifacts/pit/uw_created_at_semantics_v1.json` | HUMAN_APPROVED_RESEARCH_ASSUMPTION + UNRESOLVED_LIMITATION | `max(executed_at,created_at)`; 60s primary; 120/300 sensitivity. |
| Massive quotes | PASS for selected rows | authenticated local evidence | `artifacts/b1_full_origin/b1_origin_matrix.parquet` | AUTHENTICATED_EMPIRICAL_EVIDENCE | `sip_timestamp <= origin`, positive bid, ask>bid, age/spread filters. |
| Universe | PASS as purposive universe | project decision | `specs/001-pit-options-rv30/spec.md` | HUMAN_APPROVED_RESEARCH_ASSUMPTION | Eight liquid assets; not the US equity market. |
| Earnings | PASS for exclusion | approved design | `docs/earnings_pit_contract_v2.md` | HUMAN_APPROVED_RESEARCH_ASSUMPTION | Actual EPS/revenue are excluded from primary predictors. |
| Missingness | PASS | engineering contract | `artifacts/common_sample/common_matrix_exclusions_v1.parquet` | PROVIDER_CONFIRMED_FACT + design rule | No zero substitution, interpolation or silent repair. |
| Model and inference method | UNRESOLVED | not approved in this phase | `artifacts/methodology/` | FUTURE_METHOD_CANDIDATE | No method is selected or implemented. |

## Information sets

- **B0:** lagged underlying OHLCV and session controls available at the origin.
- **B1Q:** B0 plus ordinary option state reconstructed from Massive quotes and
  valid historical contracts.
- **B2:** B1Q plus continuous Full Tape activity aggregates. `unusual_event` is
  metadata only until a trailing calibration on prior sessions is approved.

The strict matrix requires every mandatory field in B0, B1Q and B2. The
availability-aware matrix retains valid B0/RV30 rows with explicit missingness.
Calibration rows precede pilot rows; no pilot-derived transform is used.

## Permitted and forbidden claims

Permitted: engineering coverage, reproducible as-of joins, missingness and
descriptive sample differences. Forbidden: causal claims, informed-trading or
direction claims, out-of-sample performance, final asset selection, or a claim
that `created_at` is publication time.

## Later human decisions

The protocol requires explicit approval for any provider-semantic closure, backfill execution window,
primary model, tuning policy, final test dates, inference procedure and asset
freeze. This Phase 4A report is not such approval.
