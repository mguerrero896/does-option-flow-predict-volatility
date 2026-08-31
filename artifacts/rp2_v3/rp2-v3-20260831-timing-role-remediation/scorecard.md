# RP2-v3 scorecard

Schema `rp2-v3-scorecard-v1.0`. The run this describes is named by the directory it sits in and by `run_manifest.json` beside it; the rendering does not repeat it, so two runs of the same experiment produce the same document.

Code commit `cbdd0b5840da9ae685e2dff90a113ba33e7a7806`.

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
| `b1_core_coverage` | 0.9933673946400189 |
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
| `artifact_sha256` | {"input_manifest.json": "98c83e398520b99d526b4935230bbb7249e7d5ee6f7d5e54e10e827e4c02a17c", "rp2_block3_target/target_panel.parquet": "fdab55c524a6ee2cd94bb3f1f544dec527e1c8813f9a03d6e17ed8029f842831", "rp2_block3_target/comparison.json": "a0555ebf4d0184f17be0a95c87b866c87f83a8362193d21ce46a0a8c73d0c508", "rp2_block4_b0/b0_panel.parquet": "52d58fc297ee04aeec041d58657c7dd414c726f9a2b7b9a5c92bbd7e881e5e20", "rp2_block4_b0/ladder.json": "031ae58644be1bb5580fd301f4d053113d51faa8c98d021efe6f3388aa23f84f", "rp2_block5_surface/b1_surface_panel.parquet": "446d64cf0e6369eaa99cbeae09337602924d2217953d817bd79d6d14ca2c714b", "rp2_block5_surface/surface_coverage.json": "0339bf12529cee5cdd83d4f120633f311c9cd59ae680e487b8348e2a34c862ed", "rp2_block6_flow/b2_flow_panel.parquet": "61c9843d79c6b63472e547b50334859c268183bdf1dee8864de6130491f465c6", "rp2_block6_flow/flow_coverage.json": "67f6252bec075b16f0f913c5e8ea747fe65ff14a1c31b3abeda605e1a89f940c", "feature_registry_report.json": "174a68286c2292cb4ca04df84a4454e3c04d89900f5d527079de41c3b4ece5ef", "common_masks.json": "47c36bd19a7d7bffef74afde3744fdc7bdcae65038cc932c32c05f39c9c68c5c", "rp2_block8_ladder/ladder.json": "0146654727f8970851bb0c60b7002b708a414b91b2f091d0fc0375111e942112", "rp2_block7_dml/dml.json": "eae323a11eeede693aeeb04bf17b1c253f1056239a672c8cd62fdf8d0f79e7fa", "rp2_block10_inference/inference.json": "271f179988023064635155b65031ccd2f75aa6441332a52a0de3d6548b72b486"} |
| `code_commit` | cbdd0b5840da9ae685e2dff90a113ba33e7a7806 |
| `feature_registry_sha256` | 3c108a14a5a88e4da08bade7debd5dc05a1d51ea50c1e5adea6d1e88dc0acb9c |
| `input_manifest_sha256` | 53b252ec1c1cf094b3eac963332b2a0f0edf78c7740cb75970d79916bfd8ad8f |
| `model_config_sha256` | 6a088cb19f30bcf65bd3552affa52d2093dbe1f2de14be74bb22f8cfbb67c66f |
| `peak_memory_bytes` | see `run_manifest.json` |
| `runtime_seconds` | see `run_manifest.json` |

## forecast

| Family | Role | QLIKE B0 | ΔB1 | ΔB2\|B1 | MDE ΔB1 |
| --- | --- | ---: | ---: | ---: | ---: |
| `gamma_glm` | D | 0.14522 | +0.00258 | +0.00018 | 0.00231 |
| `gamma_glm` | V | 0.18347 | -0.00152 | -0.00272 | 0.00496 |
| `lightgbm_qlike` | D | 0.14239 | +0.00267 | +0.00096 | 0.00341 |
| `lightgbm_qlike` | V | 0.21304 | +0.00136 | -0.00202 | 0.01037 |
| `ridge_log` | D | 0.14576 | +0.00288 | +0.00028 | 0.00208 |
| `ridge_log` | V | 0.18724 | -0.00092 | -0.00251 | 0.00311 |

Calibration slope 1.0202895568451738, intercept 0.13222061691179254.
