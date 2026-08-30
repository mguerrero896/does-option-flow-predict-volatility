# Scripts index

Lifecycle and purpose of every top-level script. A file being executable does not mean its
data access, publication or one-shot action is authorized. Frozen-evidence scripts are
reproducibility records for hashed artifacts; re-running them against today's store is
undefined unless the governing protocol explicitly says otherwise. Archived dead scripts
live in `scripts/archive/` with their own README.

Lifecycle labels used below:

- **CURRENT** — maintained entrypoint used by the current repository or operation.
- **CONTROLLED** — maintained, but requires its documented evidence, credential or
  authorization boundary.
- **PIPELINE COMPONENT** — normally invoked by the ordered RP2/RP3 coordinator.
- **HISTORICAL/EXPLORATORY** — retained to reproduce a recorded analysis, not to define the
  current scientific state.

## Current control plane

| Script | Lifecycle | Purpose |
| --- | --- | --- |
| `scripts/generate_canonical_state.py` | CURRENT | Generate `data/CANONICAL_STATE.json` and `STATUS.md` from the explicit authority allowlist. |
| `scripts/run_rp2_v3_pipeline.py` | CONTROLLED | Execute the ordered RP2-v3 rebuild under one run identity and fail closed on sealed or drifting inputs. |
| `scripts/run_public_repro_demo.py` | CURRENT | Run the redistributable methodological smoke demo on synthetic structured inputs. |
| `scripts/run_local_evidence_gates.py` | CONTROLLED | Run Tier 2 validation against explicitly configured licensed evidence and live access posture. |
| `scripts/scan_public_secrets.py` | CURRENT | Scan reachable Git history for high-confidence secret material. |
| `scripts/freeze_registry.py` | CONTROLLED | Maintain the append-only registry of frozen evidence. |
| `scripts/verify_scheduled_tasks.py` | CURRENT | Validate required Windows tasks, action targets, workdirs, restart policy and future triggers. |
| `scripts/alert_forwarder.py` | CURRENT | Forward unattended campaign alerts without changing scientific state. |
| `scripts/register_alert_forwarder_task.ps1` | CONTROLLED | Idempotently register the alert-forwarder Windows task. |
| `scripts/phase8_watchdog_health.py` | CURRENT | Verify from watchdog logs that the Phase 8 watchdog actually ran, without outcome access. |
| `scripts/phase9_collect.py` | CONTROLLED | Collect one naturally closed Phase 9 session under the frozen protocol. |
| `scripts/phase9_verify.py` | CURRENT | Verify Phase 9 capture completeness and zero sealed reads from manifests and counters. |
| `scripts/register_phase9_tasks.ps1` | CONTROLLED | Idempotently register the Phase 9 collector and post-check tasks. |

## Data, Supabase and publication controls

| Script | Lifecycle | Purpose |
| --- | --- | --- |
| `scripts/fetch_gated_data.py` | CONTROLLED | Download owner-issued gated files and require pointer hashes to match. |
| `scripts/upload_gated_data.py` | CONTROLLED | Upload gated files to private storage with hash verification. |
| `scripts/load_supabase_datasets.py` | CONTROLLED | Load the six private datasets through run-scoped staging and atomic promotion. |
| `scripts/sync_supabase_catalog.py` | CONTROLLED | Reconcile the aggregate research catalog atomically from repository artifacts. |
| `scripts/sync_supabase_rp2_blocks.py` | CONTROLLED | Populate the historical RP2 block register from repository artifacts. |
| `scripts/publish_rp2_v3_supabase.py` | CONTROLLED | Publish one eligible RP2-v3 bundle through the guarded atomic RPC. |
| `scripts/verify_access_posture.py` | CONTROLLED | Re-measure the declared anonymous Supabase access posture. |
| `scripts/publish_ancestry_guard.py` | CURRENT | Refuse a mirror publication that would erase reachable public history. |

## Phase 8 and RP3 controlled programme

| Script | Lifecycle | Purpose |
| --- | --- | --- |
| `scripts/freeze_phase8_bridge_evaluator_v2.py` | CONTROLLED | Bind the Phase 8 evaluator bytes to the frozen target-blind bridge contract. |
| `scripts/freeze_phase8_bridge_evaluator_v3.py` | CONTROLLED | Bind the Phase 8 evaluator, dynamic producer scripts and package source closure. |
| `scripts/freeze_phase8_bridge_evaluator_v4.py` | CONTROLLED | Refreeze that complete closure after the shared Phase 9 calendar correction. |
| `scripts/evaluate_phase8_bridge_v2.py` | CONTROLLED | Perform the separately authorized one-shot Phase 8 bridge evaluation; metadata-only preflight remains safe. |
| `scripts/rp3_freeze_b2_index.py` | CONTROLLED | Freeze the development-only B2 index for the RP3 primary test. |
| `scripts/rp3_freeze_forecasters.py` | CONTROLLED | Freeze the two RP3 forecasters and their verified-byte manifest. |
| `scripts/rp3_sizing.py` | CURRENT | Reproduce target-blind RP3 sample-size planning. |

## RP2-v3 ordered producers and renderers

These files implement the canonical rebuild. Prefer `scripts/run_rp2_v3_pipeline.py` so
every producer receives the same run identity, configuration and invariant checks.

| Script | Lifecycle | Purpose |
| --- | --- | --- |
| `scripts/rp2_block1_freeze_partition.py` | PIPELINE COMPONENT | Freeze the development/validation partition. |
| `scripts/rp2_block2_pit_ledger.py` | PIPELINE COMPONENT | Build the receipt-latency, backfill and revisions ledger. |
| `scripts/rp2_block2_admissibility.py` | PIPELINE COMPONENT | Derive per-session point-in-time admissibility from the ledger. |
| `scripts/rp2_block3_target_panel.py` | PIPELINE COMPONENT | Build and compare candidate target horizons. |
| `scripts/rp2_block4_b0_panel.py` | PIPELINE COMPONENT | Build the causal B0 benchmark panel. |
| `scripts/rp2_block5_surface_panel.py` | PIPELINE COMPONENT | Build the ordinary option-state B1 surface panel. |
| `scripts/rp2_block5b_independent_surface.py` | PIPELINE COMPONENT | Diagnose the traded-surface selection boundary. |
| `scripts/rp2_block6_flow_panel.py` | PIPELINE COMPONENT | Build the B2 microstructure panel. |
| `scripts/rp2_block7_dml.py` | PIPELINE COMPONENT | Run the observational DML mechanism diagnostic. |
| `scripts/rp2_block8_ladder.py` | PIPELINE COMPONENT | Fit the registered model ladder with session-aware splits. |
| `scripts/rp2_block9_generalization.py` | PIPELINE COMPONENT | Evaluate prespecified generalization slices. |
| `scripts/rp2_block10_inference.py` | PIPELINE COMPONENT | Compute the registered inference bundle. |
| `scripts/rp2_block11_economics.py` | PIPELINE COMPONENT | Evaluate bounded economic-significance bridges. |
| `scripts/rp2_block11b_forward_economics.py` | PIPELINE COMPONENT | Evaluate the forecast against a tradable-contract framing. |
| `scripts/rp2_block12_prospective_design.py` | PIPELINE COMPONENT | Size the prospective follow-up from measured dispersion. |
| `scripts/rp2_acquire_validation_market_bars.py` | CONTROLLED | Acquire SPY/QQQ minute bars for registered validation sessions. |
| `scripts/rp2_repair_contradicted_volume.py` | CONTROLLED | Reconcile provider bars whose volume contradicts their own record. |
| `scripts/rp2_provenance_stamp.py` | PIPELINE COMPONENT | Stamp RP2 artifacts with input and code provenance. |
| `scripts/rp2_v3_readme_findings.py` | HISTORICAL/EXPLORATORY | Render a findings table from a scorecard; current README no longer promotes ineligible results. |
| `scripts/rp2_v3_scorecard_diff.py` | CURRENT | Compare two RP2-v3 scorecards field by field. |
| `scripts/rp2_verdict_tables.py` | PIPELINE COMPONENT | Render verdict tables directly from a run. |

## RP2 extensions and recorded exploratory analyses

| Script | Lifecycle | Purpose |
| --- | --- | --- |
| `scripts/rp2_b2_autopsy_extension.py` | HISTORICAL/EXPLORATORY | Diagnose where the B2 increment disappears between features and forecasts. |
| `scripts/rp2_b2_exploratory_campaign.py` | HISTORICAL/EXPLORATORY | Reproduce the registered B2 exploratory campaign. |
| `scripts/rp2_b2_exploratory_v2.py` | HISTORICAL/EXPLORATORY | Reproduce the learned-index B2 diagnostic. |
| `scripts/rp2_ext1_mechanism_utility.py` | HISTORICAL/EXPLORATORY | Test whether the Block 7 association generalizes beyond RV30 level. |
| `scripts/rp2_ext1_directional_v2.py` | HISTORICAL/EXPLORATORY | Reproduce the directional closeout and its treatment-by-coverage factorial from D/V only. |
| `scripts/rp2_ext2_tape_tensors.py` | HISTORICAL/EXPLORATORY | Produce tape tensors shared by recorded extensions. |
| `scripts/rp2_ext3_acquire_missing_bars.py` | CONTROLLED | Acquire bars missing from a recorded extension inventory. |
| `scripts/rp2_ext4_power_both_contrasts.py` | HISTORICAL/EXPLORATORY | Reproduce prospective power for both historical contrasts. |
| `scripts/rp2_ext12_level4_and_tensor.py` | HISTORICAL/EXPLORATORY | Reproduce the optional level-4 sequence/tensor extensions. |
| `scripts/run_economic_significance.py` | HISTORICAL/EXPLORATORY | Reproduce the decision-56 economic-significance appendix. |
| `scripts/run_gate12_harq_hardening.py` | HISTORICAL/EXPLORATORY | Reproduce HAR/HARQ hardening of the historical option-state result. |
| `scripts/run_global_multiplicity.py` | HISTORICAL/EXPLORATORY | Reproduce the post-null global multiplicity sensitivity. |
| `scripts/run_lgbm_importances.py` | HISTORICAL/EXPLORATORY | Reproduce LightGBM feature-importance diagnostics. |
| `scripts/run_mcs_block_sensitivity.py` | HISTORICAL/EXPLORATORY | Reproduce MCS block-bootstrap sensitivity. |

## Protocol-scoped research and automation (executable is not authorization)

| Script | Purpose |
|---|---|
| `scripts/aggregate_pit_reconciliation_gate_v21.py` | Build the local target-blind PIT v2.1 reconciliation gate. |
| `scripts/assess_provider_timing_semantics_evidence_v1.py` | Offline intake assessor for future sanitized provider-timing evidence submissions. |
| `scripts/build_b2_confirmation_inputs.py` | Staged builder of target-free inputs and frozen RV30 target for the two 2024 confirmation blocks. |
| `scripts/build_canonical_defense_notebook.py` | Generate the portable evidence-only canonical RV30 defense notebook. |
| `scripts/build_canonical_defense_package.py` | Render the evidence-bound defense report, tables and figures from canonical RV30 artifacts. |
| `scripts/build_confirmation_readiness_v2.py` | Emit the source-bound readiness v2 snapshot for a future confirmation acquisition. |
| `scripts/build_fixture_preview.py` | Deterministic fixture-only preview of the pilot dataset exercising the local builder without providers. |
| `scripts/build_independent_replication_panel.py` | Build replication origins, FMP/B0 and target-free B2 inputs for the 30-session block. |
| `scripts/build_literature_evidence_ledger.py` | Build the conservative DOI-verified evidence ledger from the literature matrix. |
| `scripts/build_phase9_power_deadline_audit.py` | Reproduce the target-blind Phase 9 scored-session, power and academic-deadline correction without outcome access. |
| `scripts/compare_development_models.py` | Training-only tuning and comparison of preregistered candidate models on the frozen Phase 5 panel. |
| `scripts/emit_date_level_pit_preflight_status_v2.py` | Emit the current no-network date-level PIT-preflight v2 status record. |
| `scripts/evaluate_b2_confirmation_blocks.py` | One-read frozen B0/B1a/B2 evaluator over the two 2024 confirmation blocks. |
| `scripts/generate_date_level_pit_preflight_plan_v1.py` | Generate the calendar-derived candidate plan for a date-level PIT preflight. |
| `scripts/log_uw_option_trade_receipts.py` | Build sanitized UW receipt logs from a local replay for timing evidence. |
| `scripts/publish_mirror.sh` | Recovery-only whole-history publisher; mandatory Tier 2 and ancestry guards currently refuse replacing the disjoint public lineage. Normal changes start from `origin/main`. |
| `scripts/register_uw_latency_tasks.ps1` | Idempotently registers the UW latency collector/watchdog Windows scheduled tasks (Gate 5.3). |
| `scripts/report_canonical_validation.py` | Reports hash-verified canonical RV30 evidence offline, recomputing inference without refits or provider calls. |
| `scripts/rp3_acquire_batch.py` | Acquire bounded post-window RP3 evaluation batches without opening outcomes. |
| `scripts/rp3_build_eval_panels.py` | Build one RP3 evaluation batch from configured external stores. |
| `scripts/rp3_score_batch.py` | Bank row-level RP3 forecasts and outcomes without computing aggregate results. |
| `scripts/run_canonical_validation.py` | Builds hash-bound canonical RV30 comparison evidence offline from registered predictions. |
| `scripts/run_gate10_positive_findings.py` | Gate 10 (decision 56a): formalizes every cross-family B0/B1/B2 contrast from frozen forecasts. |
| `scripts/run_gate11_era_map.py` | Gate 11 (decision 56b): era-information map 2024-2026 with a fixed per-era model ladder. |
| `scripts/run_gate1_inference.py` | Gate 1: studentized inference (cluster-t, DM, wild bootstrap, MCS) over every frozen forecast artifact. |
| `scripts/run_gate2_calibration.py` | Gate 2: calibration-vs-information recalibration analysis on the binding frozen samples. |
| `scripts/run_gate3_har.py` | Gate 3: HAR/HARQ intraday ladder on development data selecting the prospective base model. |
| `scripts/run_gate4_decay_power.py` | Gate 4: effect-decay regression and decay-aware power for the 2026-08-29 Phase 8 read. |
| `scripts/run_gate5_bar_reconciliation.py` | Gate 5.1: cross-provider FMP-vs-Massive 1-minute bar reconciliation measuring assumption A001. |
| `scripts/run_gate6_regimes.py` | Gate 6: regime/event composition table and leave-event-week-out sensitivity. |
| `scripts/run_gate7_noise_robust.py` | Gate 7: noise-robust RV30 target sensitivity on the frozen C6 forecasts. |
| `scripts/run_gate8_selection.py` | Gate 8: IPW re-estimation of frozen contrasts for common-complete selection bias on C6. |
| `scripts/run_gate9_localization.py` | Gate 9: signal localization via B2 feature ablation, earnings conditioning, and horizon term structure. |
| `scripts/uw_latency_collector.py` | Gate 5.2 live UW latency collector polling flow alerts every XNYS session with crash-safe appends and heartbeat. |
| `scripts/uw_latency_reconcile.py` | Gate 5.2 +7-day reconciliation of live UW observations against the historical full tape. |
| `scripts/uw_latency_verify.py` | Gate 5.3(d) same-day capture verification plus watchdog restart of the collector. |

## Frozen evidence (built/sealed registered artifacts — do not re-run)

| Script | Purpose |
|---|---|
| `scripts/acquire_b1_independent_replication_b1q.py` | Resumable Massive B1Q acquisition for the frozen 30-session B1 replication. |
| `scripts/acquire_b1_independent_replication_full_tape.py` | Acquire the frozen 30-session UW Full Tape replication batch without outcomes. |
| `scripts/acquire_b1v3_confirmation_b1q.py` | Resumable target-blind Massive B1Q acquisition for the frozen B1v3 confirmation dates. |
| `scripts/acquire_b1v3_confirmation_full_tape.py` | Acquire missing B1v3 Full Tape sessions with resumable hash checkpoints. |
| `scripts/acquire_gate3_dev_bars.py` | Fetch FMP 1-minute development bars for the six assets feeding the Gate 3 HAR/HARQ ladder. |
| `scripts/acquire_independent_replication_30d.py` | Acquire the causal warm-up plus independent 30-session Full Tape block. |
| `scripts/acquire_phase5_holdout.py` | Acquire and seal the prospective Phase 5 holdout without analysing outcomes. |
| `scripts/acquire_phase6.py` | Acquire the frozen Phase 6 Full Tape sessions with resumable hash checks. |
| `scripts/archive_provider_timing_v21_sources.py` | Archive hash-addressed metadata for the four official PIT v2.1 provider documentation pages. |
| `scripts/audit_provider_timing.py` | Offline v1 sanitized UW timing-evidence builder from already-acquired Full Tape. |
| `scripts/audit_provider_timing_v2.py` | Offline provider-timing PIT v2 evidence bundle builder. |
| `scripts/audit_provider_timing_v21.py` | Run the target-free Provider Timing PIT v2.1 audit. |
| `scripts/audit_uw_anomaly_evidence_v21.py` | Create target-blind forensic evidence for selected UW Full Tape incidents. |
| `scripts/build_b1_independent_replication_b1v3.py` | Build source-bound target-blind B1v3 predictors for the frozen replication. |
| `scripts/build_b1_independent_replication_b2.py` | Build corrected target-blind B2 predictors for the frozen replication. |
| `scripts/build_b1_independent_replication_base.py` | Build the source-bound target-blind FMP/origin/B0 replication layer. |
| `scripts/build_b1_independent_replication_common_panel.py` | Build the primary source-bound predictor-only panel for the replication. |
| `scripts/build_b1_independent_replication_timing.py` | Build the preregistered target-blind timing views for the replication. |
| `scripts/build_b1_replication_fmp_delay2.py` | Build the preregistered target-blind FMP plus-two-minute timing sensitivity. |
| `scripts/build_b1q_exogenous_provenance_v1.py` | Capture and hash-bind target-free B1Q rate/dividend provenance. |
| `scripts/build_b1v3_confirmation_b1.py` | Build canonical source-bound B1v3 predictors after the B1Q source seal. |
| `scripts/build_b1v3_confirmation_b2.py` | Build corrected 60/120/300-second B2 predictors without outcome access. |
| `scripts/build_b1v3_confirmation_base.py` | Build the source-bound B1v3 target-free origin/FMP/spot/B0 layer. |
| `scripts/build_b1v3_confirmation_common.py` | Build the source-bound target-blind B0/B1v3a/B2 common predictor panel. |
| `scripts/build_b1v3_confirmation_timing.py` | Build source-bound target-blind B1v3 provider-timing sensitivity inputs. |
| `scripts/build_b1v3_confirmation_timing_panels.py` | Build and seal the five source-bound target-blind B1v3 timing panels. |
| `scripts/build_b1v3_target_blind.py` | Build the source-bound target-blind B1v3 feature package (shared by B1v3/replication builders). |
| `scripts/build_b2_availability_v22.py` | Build the target-blind B2 availability remediation sidecar v2.2. |
| `scripts/build_b2_calibration_20d.py` | Build the twenty-session target-free B2 calibration panel applied to Pilot V2. |
| `scripts/build_canonical_evidence_index.py` | Build the sanitized SHA-256 index for canonical RV30 validation evidence. |
| `scripts/build_corrected_development_predictors.py` | Coverage-first construction guard for the corrected development predictors. |
| `scripts/build_corrected_development_release.py` | Build the immutable target-free corrected-development predictor release. |
| `scripts/build_fmp_b1q_exogenous_docs_review_v1.py` | Write the target-blind FMP B1Q documentation-review artifact. |
| `scripts/build_independent_b1.py` | Build the target-free B1v2a ATM-IV state for the 90-session replication. |
| `scripts/build_phase5_common_panel.py` | Build the canonical 80-session Phase 5 development panel. |
| `scripts/build_phase5_stability_inputs.py` | Build target-blind B2 timing sidecars from already-downloaded Full Tape. |
| `scripts/build_target_blind_common_panel_v22.py` | Build the v2.2-masked common B0/B1Q/B2 predictor panel without outcomes. |
| `scripts/build_target_blind_common_panel_v23.py` | Build the provenance-bound v2.3 predictor panel behind the closed PIT gate. |
| `scripts/build_target_blind_common_panel_v24.py` | Build the v2.4 source-bound target-blind predictor panel without evaluation. |
| `scripts/create_target_blind_confirmation_prereg_v22.py` | Seal the next confirmation preflight from target-blind v2.2 artefacts. |
| `scripts/download_calibration_20d.py` | Download and filter the authorized UW session batches for Phase 3F and Phase 5 allow-lists. |
| `scripts/finalize_calibration_20d.py` | Finalize bounded Phase 3F download telemetry and integrity evidence from checkpoints. |
| `scripts/freeze_b1_independent_replication_method.py` | Freeze the sign-agnostic replication method from development outcomes only. |
| `scripts/freeze_b1v3_confirmation_plan.py` | Freeze the target-blind B1v3 60/30 plan from authenticated provider evidence. |
| `scripts/freeze_b1v3_method.py` | Freeze B1v3 model choices and MDE using only the 60 development sessions. |
| `scripts/freeze_b2_direct_protocol.py` | Freeze the direct B2 protocol before the new independent acquisition. |
| `scripts/freeze_b2_mechanism_search.py` | Freeze the development-only B2 mechanism-search protocol before fitting. |
| `scripts/freeze_independent_parameters.py` | Freeze independent-replication model parameters before target access. |
| `scripts/freeze_independent_replication_30d.py` | Freeze the independent 30-session replication method before reading targets. |
| `scripts/freeze_phase5_preregistration.py` | Freeze the approved Phase 5 sessions and outcome-blind preregistration. |
| `scripts/freeze_phase8_bridge_v2.py` | Freeze the target-blind Phase 8 exploratory bridge without opening its cohort. |
| `scripts/freeze_phase6_method.py` | Freeze Phase 6 methods and training-only MDE before any OOS read. |
| `scripts/phase4a_common.py` | Shared deterministic helpers (availability validation, hashing) for the Phase 4A evidence builder. |
| `scripts/phase4b_common.py` | Shared deterministic Phase 4B contracts (window specs, hashing) for the local repair builders. |
| `scripts/plan_b1_independent_replication.py` | Freezes the sign-agnostic B1/B2 independent-replication plan. |
| `scripts/plan_b1v3_confirmation.py` | Builds the date-only B1v3 exposure ledger and the frozen 60/30 confirmation plan. |
| `scripts/plan_independent_replication_30d.py` | Freezes the disjoint 30-session replication window and its storage gate. |
| `scripts/prepare_b1_independent_replication_access.py` | Validates all target-blind gates and seals the single replication-read token. |
| `scripts/prepare_b1v3_confirmation_acquisition.py` | Prepares source-bound B1v3 storage and hardlinks verified reusable evidence. |
| `scripts/probe_fmp_bar_availability.py` | Replay-only validation of FMP bar timing semantics; implements no live provider request. |
| `scripts/probe_replication_30_common.py` | Probes FMP and Massive coverage for the independent 30-session block. |
| `scripts/probe_replication_30_uw.py` | Probes historical UW Full Tape metadata for the 30-session block without downloading ZIPs. |
| `scripts/reconcile_uw_live_vs_full_tape.py` | Reconciles locally replayed UW receipts against locally replayed Full Tape rows. |
| `scripts/render_provider_timing_docs.py` | Renders deterministic provider-timing v1 documentation from evidence JSON. |
| `scripts/render_provider_timing_v21_docs.py` | Renders the human-readable PIT v2.1 amendment from compact sidecars only. |
| `scripts/render_provider_timing_v2_docs.py` | Renders the PIT v2 contract and handoff documents from offline evidence. |
| `scripts/report_independent_replication_30d.py` | Materializes the independent-replication evidence without rereading targets. |
| `scripts/run_b1_calibration_20d.py` | Recomputes the repaired B1Q route over the authorized twenty-session origins. |
| `scripts/run_b1_closure.py` | Runs the bounded B1Q/B1T feasibility closure over Pilot V2 origins with cached Massive quotes. |
| `scripts/run_b1_diagnostics.py` | Runs the 60-session development-only B1v3 mechanism diagnostic. |
| `scripts/run_b1_independent_replication_once.py` | Consumes the single token and executes the preregistered independent replication. |
| `scripts/run_b1_independent_replication_provider_preflight.py` | Runs the bounded target-blind provider preflight for the Phase 7 replication. |
| `scripts/run_b1_replication_market_control_preflight.py` | Target-blind SPY/QQQ provider preflight for the predeclared B0 market controls. |
| `scripts/run_b1v3_confirmation_once.py` | Executes exactly one preregistered B1v3 confirmation after access is sealed. |
| `scripts/run_b1v3_pre_confirmation_quality.py` | Reproduces the historical target-blind quality gate; its local-only report input must be supplied explicitly. |
| `scripts/run_b2_mechanism_search.py` | Frozen development-only B2 residual-mechanism search with registered placebo/lagged variants. |
| `scripts/run_corrected_independent_replication.py` | Runs the single preregistered reevaluation with corrected independent B1 inputs. |
| `scripts/run_date_level_pit_preflight_v1.py` | Prepares the date-level PIT preflight report without a real network transport. |
| `scripts/run_date_level_pit_preflight_v2.py` | Runs the source-bound B1v3 provider preflight without opening outcomes. |
| `scripts/run_independent_replication.py` | Frozen 60/30-session replication runner with one guarded outcome read. |
| `scripts/run_phase5_development_evaluation.py` | Runs the preregistered Phase 5 development-only RV30 evaluation. |
| `scripts/run_phase5_holdout.py` | Executes the sole prospective Phase 5 holdout read after every gate passes. |
| `scripts/run_provider_timing_capture_once.ps1` | Operator wrapper for the prospective timing capture (Prepare prints the sequence; Replay validated a local source). |
| `scripts/run_window_pipeline.py` | Runs the bounded real pilot and the authorized frozen-window backfill acquisition. |
| `scripts/seal_b1_independent_replication_b1q_source.py` | Seals independent-replication B1Q attempts to immutable Massive payloads. |
| `scripts/seal_b1v3_access_ledger.py` | Seals the B1v3 one-read authorization after every pre-confirmation gate passes. |
| `scripts/seal_b1v3_confirmation_b1q_source.py` | Seals canonical B1v3 Massive attempts to their exact target-free raw payloads. |
| `scripts/seal_b1v3_preregistration.py` | Seals the source-bound B1v3 preregistration before any outcome access. |
| `scripts/seal_corrected_independent_preregistration_v1.py` | Freezes corrected independent B1 inputs and authorizes one fixed reevaluation. |
| `scripts/seal_target_blind_comparison_contract_v1.py` | CLI wrapper for the metadata-only target-blind comparison-contract sealer. |
| `scripts/seal_target_blind_confirmation_package_v4.py` | Offline metadata-only sealer of the v4 target-blind confirmation protocol and readiness package. |
| `scripts/seal_target_blind_confirmation_preregistration_v3.py` | Seals the source-bound target-blind preregistration before method freeze. |
| `scripts/verify_provider_timing_v2.py` | Verifies deterministic equality between two compact provider-timing v2 bundles. |
| `scripts/verify_provider_timing_v21.py` | Verifies PIT v2.1 evidence hygiene and byte-level canonical integrity. |

## One-shot done (governance/repair one-offs already executed)

| Script | Purpose |
|---|---|
| `scripts/audit_b1q_put_call_parity_feasibility.py` | Target-free B1Q put-call-parity feasibility report from local cache data. |
| `scripts/audit_confirmation_readiness_v1.py` | Offline readiness v1 audit for a future confirmation acquisition. |
| `scripts/audit_phase6_source_recovery.py` | Recover and verify the exact frozen Phase 6 git source blobs via local refs. |
| `scripts/build_pit_v22_claim_ledger.py` | Build the target-blind PIT v2.2 claims-and-limitations ledger. |
| `scripts/pit_verify_term_structure.py` | One-off check that retained UW option-state payloads are PIT-usable. |
| `scripts/prepare_phase5_storage.py` | Copies retained Phase 5 evidence to the external SSD with SHA-256 verification, without deleting sources. |
| `scripts/provider_audit_v1.py` | Bounded authenticated provider audit emitting sanitized hash/schema evidence only. |
| `scripts/run_phase4b.py` | Builds the local-only Phase 4B repair package from retained calibration and pilot parquets. |
| `scripts/window_probe_v1.py` | Bounded ~25-request probe measuring each provider's usable historical window. |

## Archived candidates (see scripts/archive/)

| Script | Purpose |
|---|---|
| `scripts/archive/fix_fmp_missing_window.py` | One-off FMP missing-window repair superseded by the corrected pipeline. |
| `scripts/archive/materialize_backfill_from_raw.py` | One-off backfill materialization from raw caches, superseded by the panel builders. |
| `scripts/archive/run_phase5_b1q_missing_55.py` | Superseded Phase 5 B1Q gap-fill run; already relocated to scripts/archive/. |
