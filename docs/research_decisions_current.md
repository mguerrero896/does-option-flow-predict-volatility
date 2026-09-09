# Current research and publication decisions

**Status: CURRENT.** See [current scientific evidence](CURRENT.md) for the active result and limits; [the evidence map](EVIDENCE_MAP.md) identifies the saved support for each headline claim.

This register separates active decisions from superseded planning language. It does
not amend an old scientific registration or authorize an additional evaluation.

| Decision | Earlier wording | Current disposition | Source |
| --- | --- | --- | --- |
| Primary target | RP2/RP4 v3 RV30; historical RV60 diagnostic | RP4 v4: 15 minutes primary, 5 minutes secondary; 30 minutes is the v3 comparison. RV60 remains an RP2 diagnostic and is not an unresolved choice. | [v4 specification](rp4/specification_v4.md), [v4 decision](rp4/decision_133_v4.md), [historical target decision](target_horizon_decision.md) |
| Original proposal and design deviations | RV30 question and broad option-activity mechanism | Nested B0/B1/B2 separates price, option state and flow. Coverage/numerical repairs and a conditionally predeclared shorter horizon are disclosed; adaptive reuse remains a limitation. | [Proposal alignment](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md) |
| D005 | Window-amendment approval described as pending | Closed: the 2024 out-of-window blocks remain exploratory; no retrospective window amendment. | [Methodology decision 54](methodology_decisions.md) |
| D006 | Sealed-cohort disposition described as pending | Closed: Validation A/B were closed unread; Phase 8 completion was chosen, and its later exploratory bridge read was consumed. | [Methodology decisions 55 and 102](methodology_decisions.md), [Phase 8 closeout](../reports/phase8a_exploratory_bridge_addendum_v13.md) |
| RP4 prospective reads | Shorthand 20/40/45/335 sessions | Twenty new sessions for the registered read; forty for stability; 45 is the secondary 25-historical + 20-new combination. The 335-session extension is separately gated. No outcomes are reported here. | [Amendment 2](rp4/prospective_confirmation_v1_amendment_2.md), [amendment 3](rp4/prospective_confirmation_v1_amendment_3.md) |
| RP3 and other cohorts | Calendar date could read as a completed test | RP3 retains its protocol and estimated 2029-01-30 date; it has no reported outcome. C10 is inactive. The previously consumed Phase 8 bridge is historical, not newly sealed. | [RP3 registration](rp3/PREREGISTRATION.md), [current state](../data/CANONICAL_STATE.json) |
| Licensed bucket | Access decision or potential opening | Private. Each access request is managed by the maintainer within applicable provider entitlements; no automatic grant or public redistribution. | [Data access](../data/DATA_ACCESS.md), [measured database receipt](../artifacts/rp4_public_refresh/supabase_receipt.json) |
| Database loading | Historical audit-hold | The private dataset loader's historical hold was resolved in August. A separate mode in the existing catalog loader publishes only the three saved v4 aggregate sources, with hash and cell-equality checks. | [Catalog loader](../scripts/sync_supabase_catalog.py), [migration](../supabase/migrations/20260908153626_rp4_v4_public_aggregate_results.sql) |
| Old database migration draft | Pending signature | Superseded design history where already applied; remaining type/key changes are deferred and outside this presentation refresh. The draft must not be executed wholesale. | [Schema history](../supabase/README.md) |
| Public result scope | Later candidates originally excluded until audited | V4 keeps the headline. The closed v5 registered exploratory extension and registered eight-asset extension may be reported separately, including their failed primary-selector and joint-family claims respectively. Unaudited placebo and other PIT experiments remain outside this release. | [Publication review](public_repository_review.md), [v5 report](rp4/results_v5.md), [eight-asset report](rp4/results_universe_v1.md) |

The supplied presentation refresh authorizes candidate publication after local
verification. Merge requires five passing CI checks and written external review on
the pull request. These are publication gates, not unresolved scientific decisions.
