# Research documentation

The current public result is **RP4 v4**, with 15-minute realized variance primary and
5 minutes secondary. Its improvement is conditional on family and historical window.
The [machine-readable state](../data/CANONICAL_STATE.json) and [generated status](../STATUS.md)
retain prior results as history; older gate labels do not override the current report.

## 00 — Question and research design

Start with the [research question and findings](../README.md), then the
[proposal, hypotheses and deviations](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md)
and [v4 specification](rp4/specification_v4.md).
The [program map](figures/public_refresh/proposal_to_replication.workflow.svg) connects design,
evaluation, evidence and prospective replication.

## 01 — Data and point-in-time availability

[Data access and licence boundary](../data/DATA_ACCESS.md) ·
[Timing contract](provider_timing_pit_contract_v22.md) ·
[Source-time limitations](pit_v22_claims_and_limitations.md) ·
[Source and sample construction](rp4/data_and_execution_v1.md).
The 120-second information cutoff and the forecast horizon answer different questions.

## 02 — Information sets B0 / B1 / B2

[Design and feature definitions](rp4/specification_v4.md) ·
[Defense explanation](rp4/DEFENSE_PACKAGE/revision_2/correction_7/defense_slides.md) ·
[Historical information-set diagram](figures/information-sets.svg).
Price history, option state and flow are nested; a source-time proxy is not a record of
historical receipt by a client.

## 03 — Evaluation and decision rules

[Walk-forward design](rp4/specification_v4.md) ·
[Current decisions](research_decisions_current.md) ·
[Sequential multiplicity history](sequential_multiplicity_policy_v1.md) ·
[Registration and read gates](figures/public_refresh/registration_seals.workflow.svg).
Primary means, bilateral/Holm comparisons and secondary medians are separate analyses.

## 04 — RP4 v4 results

[Final narrative](rp4/RESULTADO_FINAL.md) · [Full v4 report](rp4/results_v4.md) ·
[Primary statistics](../artifacts/rp4_v4_b4/primary_statistics.csv) ·
[Coverage](../artifacts/rp4_v4_b4/coverage.csv) ·
[Canonical English defense package](rp4/DEFENSE_PACKAGE/revision_2/correction_7/README.md) ·
[Claims matrix](rp4/DEFENSE_PACKAGE/revision_2/correction_7/claims_matrix.csv).

The [closed registered exploratory v5 extension](rp4/results_v5.md) and its
[specification](rp4/specification_v5.md) are supplementary. Its primary selector
fails H1; the secondary top2 result and post hoc averaging do not replace v4.
The [registered, closed eight-asset extension](rp4/results_universe_v1.md) adds
SPY/QQQ as targets; its eight-row appendix and exact six-asset control retain
the distinction between the successful linear sequence and failed joint claim.

## 05 — Robustness and limits

[Scientific findings ledger](scientific_findings_ledger.md) ·
[Known defects and resolutions](known_defects_and_resolutions.md) ·
[Threats to validity](threats_to_validity_matrix_v1.md) ·
[Robustness table](../artifacts/rp4_v4_b4/robustness.csv) ·
[Saved Holm analysis](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).
The final 25-session window does not confirm the complete sequence.

## 06 — Earlier results and convergence

[Program timeline](figures/public_refresh/programme_timeline.architecture.svg) ·
[Reconciled findings](scientific_findings_ledger.md) ·
[Historical RP2 report](rp2/FINAL_REPORT.md) ·
[Withdrawn results](rp2_v3/SUPERSEDED_RESULTS.md) ·
[PIT successor-v2 results](pit_v22_claims_and_limitations_v2.md) ·
[Phase 8 bridge](../reports/phase8a_exploratory_bridge_addendum_v13.md) ·
[Complete v3 report](rp4/results_v3.md).

The historical [Block 7 DML report](rp2/block7_dml_v1.md) records discovery joint
p = 9.673e-17 and validation p = 0.832088, with no same-sign p < 0.05 replication
across universes. Earlier numbers retain their supersession labels.

## 07 — Prospective replication and RP3

[RP4 prospective protocol](rp4/prospective_confirmation_v1.md) ·
[Power and 335-session extension](rp4/prospective_confirmation_v1_amendment_3.md) ·
[RP3 preregistration](rp3/PREREGISTRATION.md) ·
[Current decisions](research_decisions_current.md).
Twenty and forty are new-session checks; 45 combines 25 historical and 20 new
sessions. RP3's 2029-01-30 date is estimated. No prospective outcome is reported here.

## 08 — Reproducibility

[Executable reproduction guide](reproduce.md) ·
[Historical execution record and licensed rebuild limits](rp4/OPERATING_GUIDE.md) ·
[Public/licensed reproduction map](figures/public_refresh/reproducibility_map.architecture.svg) ·
[Reproducibility contract](reproducibility_contract_v1.md) ·
[CI contract](ci_contract_v1.md) ·
[Development guide](DEVELOPER_GUIDE.md) · [Script catalog](../scripts/README.md) ·
[Licensed historical rebuild](rp2_v3/REBUILD_GUIDE.md).
Public tests and aggregate checks verify implementation and reporting; a licensed
scientific rerun has a separate evidence and authorization boundary.

## 09 — Governance and licensed data

[Data access](../data/DATA_ACCESS.md) · [Database schema](../supabase/README.md) ·
[Current decisions](research_decisions_current.md) ·
[Methodology ledger](methodology_decisions.md) ·
[Computational assistance](AI_ASSISTANCE_STATEMENT.md) ·
[Security](../SECURITY.md) · [Citation](../CITATION.cff) ·
[Publication design review](public_repository_review.md).

## 10 — Historical archive and supporting material

[Archive index](archive/README.md) · [Report index](../reports/INDEX.md) ·
[Literature synthesis](literature_synthesis_v2.md) ·
[Claim-level literature evidence](literature_evidence_ledger_v2.csv) ·
[Architecture](architecture.md).
Frozen originals and historical corrections are retained with explicit provenance.
Their continued availability does not make them current scientific authority.
