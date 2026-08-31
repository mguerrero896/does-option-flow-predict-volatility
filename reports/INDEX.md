# Reports index

Status classification for everything under `reports/`, mirroring `docs/INDEX.md`.
When two documents disagree, `data/CANONICAL_STATE.json` and its generated `STATUS.md`
govern. A dated report cannot promote a measurement that the canonical state marks
ineligible.

## Current

| File | Role |
|---|---|
| [`final_report_draft_v2.md`](final_report_draft_v2.md) | Authoritative evidence-cutoff thesis source; Phase 8/9 are reported as unopened/ongoing rather than as placeholders. |
| [`final_report_draft_v2.docx`](final_report_draft_v2.docx) | Word rendering generated from the Markdown source on 2026-08-28. It predates the 2026-08-31 numeric corrections in that source and must be re-exported before submission. |
| [`phase8a_exploratory_bridge_addendum_v10.md`](phase8a_exploratory_bridge_addendum_v10.md) | Current post-cutoff Phase 8A interpretation: all Holm p-values for B1 and B2 conditional on B1, frozen audit/replay closure, source-bound current D/V comparison and historical-provenance limitation. |

The evidence-cutoff pair and post-cutoff addendum are hash-pinned under `current_report`
in [`data/CANONICAL_STATE.json`](../data/CANONICAL_STATE.json). The Markdown thesis governs
the cutoff report; the Word file is its submission rendering; the addendum governs the
Phase 8A outcome.

Retired proposal, defense-deck and gate-cascade drafts are absent from the public release.
Their withdrawn numerical claims and reasons remain in
`docs/rp2_v3/SUPERSEDED_RESULTS.md`; presentation material must be regenerated from the
current canonical state.

## Historical (audit trail)

[`phase8a_exploratory_bridge_addendum_v1.md`](phase8a_exploratory_bridge_addendum_v1.md),
[`phase8a_exploratory_bridge_addendum_v2.md`](phase8a_exploratory_bridge_addendum_v2.md),
[`phase8a_exploratory_bridge_addendum_v3.md`](phase8a_exploratory_bridge_addendum_v3.md),
[`phase8a_exploratory_bridge_addendum_v4.md`](phase8a_exploratory_bridge_addendum_v4.md),
[`phase8a_exploratory_bridge_addendum_v5.md`](phase8a_exploratory_bridge_addendum_v5.md),
[`phase8a_exploratory_bridge_addendum_v6.md`](phase8a_exploratory_bridge_addendum_v6.md),
[`phase8a_exploratory_bridge_addendum_v7.md`](phase8a_exploratory_bridge_addendum_v7.md),
[`phase8a_exploratory_bridge_addendum_v8.md`](phase8a_exploratory_bridge_addendum_v8.md),
and [`phase8a_exploratory_bridge_addendum_v9.md`](phase8a_exploratory_bridge_addendum_v9.md)
— frozen Phase 8A interpretations retained at their registered SHA-256 values; v10 is
current.

[`literature_review_20260811/`](literature_review_20260811/),
[`literature_fulltext_audit_20260811/`](literature_fulltext_audit_20260811/) — literature
process snapshots; [`canonical_validation_v1/`](canonical_validation_v1/) — the 2026-08-11
defense package (report, figures, manifest) as evidence of that era's state.
