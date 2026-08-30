# STATUS — canonical project state

> AUTO-GENERATED from `data/CANONICAL_STATE.json` by
> `scripts/generate_canonical_state.py`. Never edit by hand; CI fails on drift.
> This file supersedes any narrative document that disagrees with it.

- Governance: decision 104 is the latest (104 recorded).
- Frozen evidence: 83 artifacts registered; 81 are present in this release and 2 remain gated or withdrawn with their digests preserved in `data/FROZEN_ARTIFACTS.json`.
- Public metadata redactions: 10 frozen artifacts retain original and redacted SHA-256 custody in `data/PUBLIC_METADATA_REDACTIONS.json`.
- Gated data: 15 files in private storage (`data/GATED_DATA_POINTERS.json`).
- Supabase publication: **NO_CURRENT_RESULTS_PUBLICATION_AND_DIRECT_DML_DISABLED_DATASET_REGISTRY_EXACT** (19 schema migrations, 1 catalog reconciliation, and 6 dataset manifests committed; sealed reads: Phase 8 = 1, Phase 9 = 0).

## Active protocols

- **phase8-prospective-bridge** — `docs/phase8_bridge_protocol_v2.md`: EXPLORATORY_BRIDGE_EVALUATION_COMPLETE_WITH_RECORDED_RECOVERY_AND_DISPERSION_AUDIT
- **phase9-total-contribution** — `docs/phase9_total_contribution_protocol_v1.md`: frozen; collection active for sessions strictly after 2026-08-18, 60 complete/36 scored sessions, evaluation authorization ~Nov 2026; ongoing prospective follow-up, not an academic submission gate

## Current scientific bundle

- Run: `rp2-v3-20260827-remediation3`.
- Scientific hash: `386610a4908d601c1ad09688d8371cfa3fdd70e4e7ddf50c416e8d3b0907cb47`.
- Historical code provenance: recorded run commit `e7728ebbaf3f` and the pre-root sanitization audit are external references; neither is claimed reachable from this root-only public release.
- Eligibility: **REBUILD_COMPLETE_PIT_V22_BLOCKED**.
- Blocking reasons: PIT_V22_RECONCILIATION_BLOCKED.
- Current eligible headline results: none.
- Historical measurements remain traceable in `docs/rp2_v3/SUPERSEDED_RESULTS.md`; they are not current claims.
- Current academic report: `reports/final_report_draft_v2.md` with the Word submission rendering pinned under `current_report` in the machine state.
- Post-cutoff Phase 8A result: `reports/phase8a_exploratory_bridge_addendum_v2.md`.

## Future campaigns

- Phase 9 requires 60 complete (36 scored), previously unseen sessions and a separate read gate; academic submission does not wait for its outcome

## CI

- Required checks: quality, hermetic, scientific-contracts (coverage >= 80%).
- Tier 2 (licensed evidence): `scripts/run_local_evidence_gates.py`; scripts/publish_mirror.sh refuses to push unless tier-2 passes.
