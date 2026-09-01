# Research documentation index

This is a researcher-facing map, not a second source of scientific truth. The single
machine-readable authority is `data/CANONICAL_STATE.json`; `STATUS.md` is generated from it.
The current state is `CURRENT_ELIGIBLE_SCIENTIFIC_RESULT_EDGE_NOT_CONFIRMED`: the
successor-v2 result is reportable, while the RP2-v3 bundle remains historical and no global
edge or capital claim is eligible.

## Start here

| Document | Purpose |
| --- | --- |
| [`README.md`](../README.md) | Scope, current eligibility, information sets and reproducibility boundary. |
| [`STATUS.md`](../STATUS.md) | Generated human-readable projection of the canonical state. |
| [`data/CANONICAL_STATE.json`](../data/CANONICAL_STATE.json) | One current run pointer, evidence hashes and fail-closed eligibility reasons. |
| [`docs/AI_ASSISTANCE_STATEMENT.md`](AI_ASSISTANCE_STATEMENT.md) | Computational-assistance disclosure and scientific decision boundaries. |
| [`docs/rp2_v3/SUPERSEDED_RESULTS.md`](rp2_v3/SUPERSEDED_RESULTS.md) | Withdrawn or invalidated measurements and their reasons. |
| [`docs/rp2_v3/VERDICT.md`](rp2_v3/VERDICT.md) | Corrected-protocol 2026-08-27 measurement, explicitly not a current claim. |

## Maintainer map

| Document | Purpose |
| --- | --- |
| [`docs/DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) | Onboarding, source-of-truth hierarchy, safe commands and change workflow. |
| [`docs/architecture.md`](architecture.md) | Current code, evidence, canonical-state and live-operation architecture. |
| [`scripts/README.md`](../scripts/README.md) | Lifecycle and purpose of every top-level executable script. |
| [`reports/INDEX.md`](../reports/INDEX.md) | Current submission source and historical report packages. |
| [`supabase/README.md`](../supabase/README.md) | Reproducible database structure, migration order and access boundaries. |

The repository retains versioned protocols and audit records because their hashes and
citations matter. A filename suffix does not establish authority. Use the current-state
pointer above and the lifecycle labels in this index; do not reorganize by moving frozen
files between directories.

## Methods and evidence boundaries

| Document | Purpose |
| --- | --- |
| [`docs/target_horizon_decision.md`](target_horizon_decision.md) | Recorded RV30 primary-target decision. |
| [`docs/rp2/block3_target_validation_v1.md`](rp2/block3_target_validation_v1.md) | Current target-horizon diagnostic: RV60 leads in D, RV30 leads in V. |
| [`docs/pit_v22_claims_and_limitations.md`](pit_v22_claims_and_limitations.md) | Source-time PIT and availability limitations. |
| [`docs/pit_v22_claims_and_limitations_v2.md`](pit_v22_claims_and_limitations_v2.md) | Current successor-v2 contrasts, custody validation and claim limits. |
| [`docs/gate5_pit_foundations_v1.md`](gate5_pit_foundations_v1.md) | Current Gate 5 authority, including UW receipt-hour latency and opening-cutoff disposition. |
| [`docs/gate5_uw_latency_closeout_v1.md`](gate5_uw_latency_closeout_v1.md) | Superseded historical UW latency closeout retained for v1 snapshot provenance. |
| [`docs/gate5_uw_same_channel_reconciliation_proposal_v1.md`](gate5_uw_same_channel_reconciliation_proposal_v1.md) | Resource-gated proposal for identifiable same-channel backfill and revision. |
| [`docs/provider_timing_pit_contract_v22.md`](provider_timing_pit_contract_v22.md) | Governing provider-timing contract and proxy semantics. |
| [`docs/rp2_v3/B1_CONTEMPORANEOUS_SPEC_V2.md`](rp2_v3/B1_CONTEMPORANEOUS_SPEC_V2.md) | Current B1 option-state contract: option rows and underlying spot share the `t-120 s` cutoff; v1 remains historical. |
| [`docs/sequential_multiplicity_policy_v1.md`](sequential_multiplicity_policy_v1.md) | Future-campaign alpha spending; retrospective D/V remains exploratory. |
| [`docs/phase8_bridge_protocol_v2.md`](phase8_bridge_protocol_v2.md) | Frozen exploratory 20-of-30 Phase 8 bridge; decision 102 records its consumed one-shot read, `MIXED_EXPLORATORY` result and execution recovery. |
| [`docs/phase9_total_contribution_protocol_v1.md`](phase9_total_contribution_protocol_v1.md) | Frozen 60-complete-session Phase 9 protocol; evaluation remains one-shot and separately authorized. |
| [`docs/phase9_academic_reporting_policy_v2.md`](phase9_academic_reporting_policy_v2.md) | Current target-blind deadline and power policy: 36 scored sessions at endpoint; Phase 9 does not gate submission. |
| [`docs/rp3/B2_INCREMENTAL_EDGE_ROUTE.md`](rp3/B2_INCREMENTAL_EDGE_ROUTE.md) | Design-only route for a future disjoint incremental B2 test; records why no global edge exists now and activates no read. |
| [`docs/methodology_decisions.md`](methodology_decisions.md) | Recorded methodological decisions and amendments. |
| [`docs/branch_lineage_reconciliation_20260831.md`](branch_lineage_reconciliation_20260831.md) | Branch-lineage audit and selective replay disposition after repository recreation. |
| [`docs/threats_to_validity_matrix_v1.md`](threats_to_validity_matrix_v1.md) | Validity threats, mitigations and residual risks. |

The Phase 8 row in `sequential_multiplicity_policy_v1.md` preserves its historical slot.
It is not a confirmation threshold: the bridge contract classifies every p-value as
descriptive, forbids confirmatory promotion and permits no second read. The historical
outcome, exact replay and same-30-session post-hoc information-clock sensitivity are
published in
[`reports/phase8a_exploratory_bridge_addendum_v13.md`](../reports/phase8a_exploratory_bridge_addendum_v13.md).

## Reproduction and data access

| Document | Purpose |
| --- | --- |
| [`docs/reproducibility_contract_v1.md`](reproducibility_contract_v1.md) | Hermetic/Tier 2 boundary and methodological smoke demo. |
| [`docs/ci_contract_v1.md`](ci_contract_v1.md) | Hosted hermetic checks versus licensed-evidence checks. |
| [`docs/rp2_v3/REBUILD_GUIDE.md`](rp2_v3/REBUILD_GUIDE.md) | Ordered 13-step licensed rebuild, exact invocation, storage budget and resume flags. |
| [`data/DATA_ACCESS.md`](../data/DATA_ACCESS.md) | Controlled access to licensed-derived evidence and licence scope. |
| [`data/GATED_DATA_POINTERS.json`](../data/GATED_DATA_POINTERS.json) | Hash and size pointers for gated datasets. |
| [`SECURITY.md`](../SECURITY.md) | Private vulnerability reporting and data-leak scope. |

## Literature

| Document | Purpose |
| --- | --- |
| [`docs/literature_synthesis_v2.md`](literature_synthesis_v2.md) | Evidence-bounded synthesis with verification tiers. |
| [`docs/literature_evidence_ledger_v2.csv`](literature_evidence_ledger_v2.csv) | Claim-level source and full-text status ledger. |
| [`docs/literature_reconciliation_v1.md`](literature_reconciliation_v1.md) | Literature expectations versus observed project evidence. |

## RP2 audit trail

The block documents preserve historical measurements. They do not override the canonical
eligibility state. Block 7 is listed explicitly because a contract checks that its public
summary reproduces the run it names:

| Document | Current audit interpretation |
| --- | --- |
| [`docs/rp2/block7_dml_v1.md`](rp2/block7_dml_v1.md) | Historical run: discovery joint p = 9.673e-17; validation p = 0.832088; no replicates across universes were found with the same sign at p < 0.05. |
| [`docs/rp2/extension_b2_directional_utility_v2.md`](rp2/extension_b2_directional_utility_v2.md) | Preregistered D/V-only Ext1 closeout: `DO_NOT_PURSUE`; no confirmatory or sealed-cohort claim. |
| [`docs/rp2/FINAL_REPORT.md`](rp2/FINAL_REPORT.md) | Historical programme report; consult supersession markers before using any result. |
| [`docs/canonical_claims_and_limitations.md`](canonical_claims_and_limitations.md) | RP2-v2 claim ledger retained for audit under its `SUPERSEDED AUTHORITY` banner; it has no current claim authority. |
| [`docs/research_program_v2.md`](research_program_v2.md) | Historical design record; executed and superseded, not current operating authority. |
| [`docs/rp2_v3/IMPLEMENTATION_STATUS.md`](rp2_v3/IMPLEMENTATION_STATUS.md) | Gate completion record plus current invalidation banner. |

All other documents under `docs/` remain available as methodology, frozen protocol,
diagnostic or superseded audit material. A historical document is not current merely because
it remains published. New maintained documents must be linked from this index; new
top-level scripts must be registered in `scripts/README.md`.
