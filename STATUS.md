# STATUS — canonical project state

> AUTO-GENERATED from `data/CANONICAL_STATE.json` by
> `scripts/generate_canonical_state.py`. Never edit by hand; CI fails on drift.
> This file supersedes any narrative document that disagrees with it.

- Governance: decision 126 is the latest (126 recorded).
- Frozen evidence: 147 artifacts registered; 145 are present in this release and 2 remain gated or withdrawn with their digests preserved in `data/FROZEN_ARTIFACTS.json`.
- Public metadata redactions: 14 frozen artifacts retain original and redacted SHA-256 custody in `data/PUBLIC_METADATA_REDACTIONS.json`.
- Gated data: 15 files in private storage (`data/GATED_DATA_POINTERS.json`).
- Supabase publication: **NO_CURRENT_RESULTS_PUBLICATION_AND_DIRECT_DML_DISABLED_DATASET_REGISTRY_EXACT** (19 schema migrations, 1 catalog reconciliation, and 6 dataset manifests committed; sealed reads: Phase 8 = 1, Phase 9 = 0).

## Active protocols

- **phase8-prospective-bridge** — `docs/phase8_bridge_protocol_v2.md`: EXPLORATORY_BRIDGE_EVALUATION_COMPLETE_WITH_RECORDED_RECOVERY_AND_DISPERSION_AUDIT_AND_POSTHOC_MATERIALIZED_REMEDIATION
- **phase9-total-contribution** — `docs/phase9_total_contribution_protocol_v1.md`: frozen; collection active for sessions strictly after 2026-08-18, 60 complete/36 scored sessions, evaluation authorization ~Nov 2026; ongoing prospective follow-up, not an academic submission gate

## UW latency campaign

- Lifecycle: **RECONCILED_PARTIAL** (6/12 sessions reconciled).
- Claim boundary: **PROXY_ONLY_CROSS_CHANNEL**; backfill and revision remain non-identifiable under the cross-channel design.
- State authority: `artifacts/gate5_pit/uw_latency_campaign_state_20260902_v3.json`.

## PIT v2.2 successor evaluation

- Status: **SCIENTIFIC_EVALUATION_COMPLETE_CUSTODY_VALIDATED**; decision: **GLOBAL_EDGE_NOT_CONFIRMED**.
- One-shot custody: 1 attempt, 1 OOS read, rerun allowed = false.
- Target linkage: development 37,312 -> 37,306 (6 excluded); all 62,266 -> 62,254 (12 excluded).
- Gamma confirmatory `delta_b1v2`: 0.00817124731841 [0.0026577746716, 0.0140242323071], Holm p=0.00839916008399, MDE=0.00841614346016, >=MDE=false.
- Gamma confirmatory `delta_b2v2`: -0.00312662105094 [-0.0139233571227, 0.00860854983579], Holm p=0.559544045595, MDE=0.00667622758309, >=MDE=false.
- LightGBM robustness `delta_b1v2` / `delta_b2v2`: 0.00417580612338 / 0.00136801409755; both are descriptive MDE references, not confirmatory promotion tests.
- Frozen result: `artifacts/target_blind_v22/successor_evaluation_result_v2.json` (SHA-256 `ddad159bc02067fd14ef1f7b1c35b9ed02eef26ebd5d19e9e88c5838d6b97775`).
- Frozen public log: `artifacts/target_blind_v22/successor_evaluation_run_v2.json` (SHA-256 `0507ccf5903d46ccd7fee2dc7a535faa8455501e7a1061bafceadd1d8e5f96a3`).
- Eligibility: scientific result = true after independent custody validation; edge claim = false, capital = false; `capital_go=false`, `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE`.

## Current scientific bundle

- Run: `rp2-v3-20260831-b1-spot-cutoff-remediation`.
- Scientific hash: `033f2eb6be35e5db06aec2f9e01ef5f3379a8be68b0372087f24e40fa681bea4`.
- Code provenance: recorded run commit `b70c54ba14fd` is reachable from this root release.
- Eligibility: **HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM**.
- Disposition: SUPERSEDED_BY_PIT_V22_SUCCESSOR_V2.
- Current canonical scientific result: the PIT v2.2 successor-v2 result above; no edge headline is eligible because no registered estimate met its frozen MDE and the signed contract contained no binary edge-promotion rule.
- Historical measurements remain traceable in `docs/rp2_v3/SUPERSEDED_RESULTS.md`; they are not current claims.
- Current academic report: `reports/final_report_draft_v2.md` with the Word submission rendering pinned under `current_report` in the machine state.
- Post-cutoff Phase 8A result: `reports/phase8a_exploratory_bridge_addendum_v13.md`.

## Future campaigns

- Phase 9 requires 60 complete (36 scored), previously unseen sessions and a separate read gate; academic submission does not wait for its outcome

## CI

- Required checks: quality, hermetic, scientific-contracts (coverage >= 90%).
- Tier 2 (licensed evidence): `scripts/run_local_evidence_gates.py`; scripts/publish_mirror.sh refuses to push unless tier-2 passes.
