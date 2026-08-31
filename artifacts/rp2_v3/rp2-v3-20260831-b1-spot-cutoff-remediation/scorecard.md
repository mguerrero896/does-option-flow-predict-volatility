# RP2-v3 scorecard

Schema `rp2-v3-scorecard-v1.0`. The run this describes is named by the directory it sits in and by `run_manifest.json` beside it; the rendering does not repeat it, so two runs of the same experiment produce the same document.

Code commit `b70c54ba14fdda2197efd6bcf0aa676c4ba3d4f1`.

## data

| Field | Value |
| --- | ---: |
| `assets` | 6 |
| `b0_rows` | 181829 |
| `b1_rows` | 181829 |
| `b2_rows` | 181829 |
| `common_evaluation_rows` | {"D": 60407, "V": 12480} |
| `duplicate_keys` | 0 |
| `masked_rows_by_role` | {"D": 150629, "V": 31200} |
| `provider_failures` | 0 |
| `sessions_by_role` | {"D": 389, "V": 80} |
| `sparse_session_assets` | 0 |

## b1

| Field | Value |
| --- | ---: |
| `b1_core_coverage` | 0.9933893933310968 |
| `b1_duplicate_contracts_per_snapshot` | 0 |
| `b1_median_quote_age_s` | 550.0 |
| `b1_missing_rate_share` | 0.4303053968288887 |
| `b1_p95_quote_age_s` | 1725.0 |
| `b1_post_cutoff_observations` | 0 |
| `b1_rows_dropped_for_rate_or_dividend` | 0 |
| `b1_surface_contracts_per_origin` | 778.7895715204945 |
| `b1_surface_expiry_coverage` | 0.9978276292560593 |

## b2

| Field | Value |
| --- | ---: |
| `b2_empty_window_share` | 0.0023153622359469613 |
| `b2_mean_provider_latency_s` | 1.221522874453539 |
| `b2_multileg_share` | 0.23970385449719134 |
| `b2_p95_provider_latency_s` | 0.3555064279213946 |
| `b2_pit_violation_count` | 0 |
| `b2_provider_failure_share` | 0.0 |
| `b2_zero_dte_count` | 102568762 |

## engineering

| Field | Value |
| --- | ---: |
| `artifact_sha256` | {"input_manifest.json": "98c83e398520b99d526b4935230bbb7249e7d5ee6f7d5e54e10e827e4c02a17c", "rp2_block3_target/target_panel.parquet": "fdab55c524a6ee2cd94bb3f1f544dec527e1c8813f9a03d6e17ed8029f842831", "rp2_block3_target/comparison.json": "a0555ebf4d0184f17be0a95c87b866c87f83a8362193d21ce46a0a8c73d0c508", "rp2_block4_b0/b0_panel.parquet": "52d58fc297ee04aeec041d58657c7dd414c726f9a2b7b9a5c92bbd7e881e5e20", "rp2_block4_b0/ladder.json": "031ae58644be1bb5580fd301f4d053113d51faa8c98d021efe6f3388aa23f84f", "rp2_block5_surface/b1_surface_panel.parquet": "7e022d2845a4300be5f7d286337ec6ee4c0e5614fa00cacbc386924be3b37f33", "rp2_block5_surface/surface_coverage.json": "170c6d9ee3eb476e4096b512b9097942f6d49422d05fe3e686b6a5aea53e8076", "rp2_block6_flow/b2_flow_panel.parquet": "61c9843d79c6b63472e547b50334859c268183bdf1dee8864de6130491f465c6", "rp2_block6_flow/flow_coverage.json": "67f6252bec075b16f0f913c5e8ea747fe65ff14a1c31b3abeda605e1a89f940c", "feature_registry_report.json": "7389310b0a302a3e0d2a345f3155ee363aa13aaf7f81848c81a15f48b9e33b20", "common_masks.json": "47c36bd19a7d7bffef74afde3744fdc7bdcae65038cc932c32c05f39c9c68c5c", "rp2_block8_ladder/ladder.json": "85a8313800a12d7762c2e6f40f03c694c4cc6ea5554d3768c0b4bc9e314a474a", "rp2_block7_dml/dml.json": "d5efcd08e335108580528d09fa8d46d885208f0ecff24d6f5feba92210c8e20a", "rp2_block10_inference/inference.json": "a755efde156d61988fda6b7a727f1c70970ac90332f027056dbf3e231783eb81"} |
| `code_commit` | b70c54ba14fdda2197efd6bcf0aa676c4ba3d4f1 |
| `feature_registry_sha256` | 3c108a14a5a88e4da08bade7debd5dc05a1d51ea50c1e5adea6d1e88dc0acb9c |
| `input_manifest_sha256` | 53b252ec1c1cf094b3eac963332b2a0f0edf78c7740cb75970d79916bfd8ad8f |
| `model_config_sha256` | 6a088cb19f30bcf65bd3552affa52d2093dbe1f2de14be74bb22f8cfbb67c66f |
| `peak_memory_bytes` | see `run_manifest.json` |
| `runtime_seconds` | see `run_manifest.json` |

## forecast

| Family | Role | QLIKE B0 | ΔB1 | ΔB2\|B1 | MDE ΔB1 |
| --- | --- | ---: | ---: | ---: | ---: |
| `gamma_glm` | D | 0.14522 | +0.00256 | +0.00012 | 0.00233 |
| `gamma_glm` | V | 0.18347 | -0.00150 | -0.00264 | 0.00506 |
| `lightgbm_qlike` | D | 0.14239 | +0.00320 | +0.00052 | 0.00360 |
| `lightgbm_qlike` | V | 0.21304 | +0.00280 | +0.00198 | 0.01198 |
| `ridge_log` | D | 0.14576 | +0.00287 | +0.00028 | 0.00207 |
| `ridge_log` | V | 0.18724 | -0.00088 | -0.00250 | 0.00315 |

Calibration slope 1.024346029220891, intercept 0.17209258954450657.
