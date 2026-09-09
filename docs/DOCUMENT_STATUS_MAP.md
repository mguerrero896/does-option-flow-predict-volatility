# Document status map

Start with [current scientific evidence](CURRENT.md), then use the
[documentation index](INDEX.md) for the reading order and the
[scientific findings ledger](scientific_findings_ledger.md) for the status of
individual claims. The [canonical state](../data/CANONICAL_STATE.json) and
[generated status](../STATUS.md) provide the machine-readable and generated
counterparts. A filename version alone does not establish authority.

This map classifies document families and selected entry points. Family-level
classifications are provisional where individual documents have not been reviewed;
they do not certify every claim in every file. A historical document can remain
necessary evidence without representing the current conclusion.

## Status meanings

| Status | Meaning |
| --- | --- |
| CURRENT | Current reading entry or governing account within its stated scope. |
| HISTORICAL | Record of an earlier analysis, decision or implementation. |
| SUPERSEDED | Earlier account replaced by a later account; retain for provenance. |
| EXPLORATORY | Supplementary investigation whose outcome does not replace the primary result. |
| PROSPECTIVE - NOT YET EVALUATED | Future evaluation or explicitly unregistered proposal; the document states which. No prospective outcome is established here. |
| ARCHIVED EVIDENCE | Preserved source, correction, translation baseline or integrity record. |

## Results and protocols

| Document or family | Status | Interpretation |
| --- | --- | --- |
| [Current evidence](CURRENT.md) and [findings ledger](scientific_findings_ledger.md) | CURRENT | Begin here for results, limitations and unresolved evidence boundaries. |
| [Completed linear RV15 placebo report](rp4/robustness_committed_v1_placebo_linear_rv15.md), [summary](../artifacts/rp4_robustness_public_v1/placebo_log_ridge_harq_rv15_summary.csv) and [provenance](../artifacts/rp4_robustness_public_v1/import_receipt.json) | CURRENT | Closed post-primary robustness evidence; timely order flow is not demonstrated. The English report is a declared public derivative; other robustness stages are not certified by this closure. |
| [RP4 v4 result](rp4/results_v4.md) and [specification](rp4/specification_v4.md) | CURRENT | Primary historical result and its design, read with the qualifications below. |
| [Final narrative](rp4/RESULTADO_FINAL.md) | CURRENT | Public narrative accompanying the v4 result; current evidence and the ledger resolve older closeout wording. |
| [Final narrative revision 1](rp4/RESULTADO_FINAL_revision_1.md) and [revision 2](rp4/RESULTADO_FINAL_revision_2.md) | HISTORICAL | Retained closeout accounts; their statements that the programme ends without v5 describe an earlier scope. |
| [RP4 v1](rp4/results_v1.md), [v2](rp4/results_v2.md), [v3](rp4/results_v3.md) | SUPERSEDED | Earlier result accounts; v4 is the primary current historical result. |
| [V1 specification](rp4/specification_v1.md), [v2 specification](rp4/specification_v2.md), [v3 specification](rp4/specification_v3.md) | HISTORICAL | Protocols governing their corresponding versions; replacement does not invalidate their provenance. |
| [RP4 v5 result](rp4/results_v5.md), [specification](rp4/specification_v5.md) and [technical amendment](rp4/specification_v5_technical_amendment_2.md) | EXPLORATORY | Closed registered extension; its primary selector fails H1. Secondary and post hoc findings do not replace v4. |
| [Eight-asset extension](rp4/results_universe_v1.md) | EXPLORATORY | Closed supplementary extension adding SPY and QQQ as targets; retain the distinction between the linear sequence and the joint claim. |
| [Current English defense package](rp4/DEFENSE_PACKAGE/revision_2/correction_7/README.md) | CURRENT | Presentation of existing evidence, with a claims matrix and source bindings. |
| [RP4 prospective protocol](rp4/prospective_confirmation_v1.md), [amendment 1](rp4/prospective_confirmation_v1_amendment_1.md), [amendment 2](rp4/prospective_confirmation_v1_amendment_2.md), [amendment 3](rp4/prospective_confirmation_v1_amendment_3.md) and [context](rp4/prospective_confirmation_v1_amendment_3_context_1.md) | PROSPECTIVE - NOT YET EVALUATED | Read the protocol together with its amendments; a registration or collection plan is not an evaluated outcome. |
| [RP3 preregistration](rp3/PREREGISTRATION.md) | PROSPECTIVE - NOT YET EVALUATED | Separate prospective programme and its stated constraints. |
| [Future research priorities](rp4/PROSPECTIVE_RESEARCH.md) | PROSPECTIVE - NOT YET EVALUATED | Unregistered proposals; no execution or amendment is authorized by this document. |
| [Implementation boundary](architecture.md#rp4-implementation-and-execution-boundary) | CURRENT | Maps RP4 snapshot entrypoints and shared maintained imports without moving historical code. |
| [Final documentary review](FINAL_REVIEW.md) | CURRENT | Four analytical perspectives and twelve located answers; no measured reader-comprehension or reading-time result. |
| [RP2 report](rp2/FINAL_REPORT.md) and [RP2 v3 withdrawn results](rp2_v3/SUPERSEDED_RESULTS.md) | HISTORICAL / SUPERSEDED | Read each claim with its withdrawal or supersession disposition. |

The v4 report's sentence **"There is no v5"** records its original closeout scope.
It is not a current assertion that the later, closed exploratory v5 extension does
not exist. Its **"Confirmation comparison"** heading refers to the final
historical window comparison, not an independently collected prospective
confirmation. The complete sequence is not confirmed in that final 25-session
window. These clarifications do not amend the recorded results or their seals.

## Family inventory

The completed [60-second](../artifacts/rp4_robustness_public_v1/pit_60_contrasts.csv)
and [300-second timing sensitivities](../artifacts/rp4_robustness_public_v1/pit_300_contrasts.csv), including their exact saved 120-second primary controls,
and their [interpretation](FAQ.md#14-does-the-flow-result-survive-a-stricter-availability-cutoff)
are **CURRENT**, with [import provenance](../artifacts/rp4_robustness_public_v1/import_receipt.json).
The three-cutoff series is descriptive evidence of timing sensitivity, not a stronger registered finding or historical receipt proof. Tree-model placebos at RV15 and RV30 are deferred for cost; the linear RV30 placebo remains in progress and is not certified by this closure.

The baseline inventory contains 2,801 tracked files, including 528 Markdown files.
Counting `.md`, `.rst`, `.txt`, `.pdf`, `.docx`, `.pptx`, `.html` and `.ipynb`
as documents gives 558 documents before this map and other new documentation.
That definition includes test-report text and HTML visualizations, but excludes
JSON, CSV, images and `.original` or `.public` archive copies. Counts describe the
inventory baseline, not an automatically maintained total.

| Family | Baseline documents | Initial classification |
| --- | ---: | --- |
| Documentation root | 133 | CURRENT entry points mixed with HISTORICAL contracts and decisions; consult the index. |
| Documentation archive | 151 | ARCHIVED EVIDENCE. |
| RP4 documentation | 76 | Mixed statuses; use the result and protocol table above. |
| RP2 documentation | 23 | Primarily HISTORICAL. |
| Recovery documentation | 14 | Primarily HISTORICAL incident and recovery records. |
| RP2 v3 documentation | 12 | HISTORICAL contracts and SUPERSEDED results. |
| Figure documentation | 7 | Mixed CURRENT presentation and HISTORICAL evidence. |
| Model cards | 5 | HISTORICAL model specifications. |
| RP3 documentation | 4 | PROSPECTIVE - NOT YET EVALUATED programme documentation. |
| Technical references | 2 | Reference material; verify applicability to the intended execution. |
| Literature-source guide | 1 | Source access and provenance; claim-level verification is separate. |
| Artifact documents | 81 | Primarily HISTORICAL or ARCHIVED EVIDENCE; preserve bindings. |
| Reports | 23 | Mixed historical accounts; use the [report index](../reports/INDEX.md). |
| Specifications outside docs | 12 | Version-specific design records; verify their governing scope. |
| Script documents | 4 | Operational references; use the [script catalog](../scripts/README.md). |
| Notebooks | 2 | Reproduction or historical presentation; execution is not implied by inclusion. |
| Supabase documents | 2 | Database references; use the [database guide](../supabase/README.md). |
| Data-access document | 1 | [Access and licence boundary](../data/DATA_ACCESS.md). |
| Pull-request template | 1 | Contribution workflow. |
| Root README, STATUS, CONTRIBUTING and SECURITY | 4 | Public entry, generated state and maintenance policies. |

## Integrity and physical labels

The [frozen-artifact registry](../data/FROZEN_ARTIFACTS.json) contains 159 entries
in the inventory baseline. Registry membership is not the only integrity boundary:
protocol seals, evidence manifests and archive maps can bind additional files.
Original frozen documents are not physically relabelled, rewritten or moved to
apply this classification. This map supplies reading context outside those bytes.

Use the [archive guide](archive/README.md),
[historical source map](archive/public_history/original_paths.json),
[general-document baseline map](archive/public_refresh_baseline/original_paths.json),
[defense source map](archive/rp4/DEFENSE_PACKAGE/original_paths.json) and
[presentation source map](archive/rp4/presentation_originals/original_paths.json)
to trace earlier wording and its public derivative. The first three source maps
contain 50, 21 and 99 entries respectively in the inventory baseline. Their
existence does not imply that every referenced original is redistributed.
The [immutability contract](evidence_immutability_v1.md) explains the verification
boundary. Archive retention does not restore withdrawn claims or authorize a new
evaluation.
