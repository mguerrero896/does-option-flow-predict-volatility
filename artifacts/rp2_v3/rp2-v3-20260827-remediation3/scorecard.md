# RP2-v3 scorecard

Schema `rp2-v3-scorecard-v1.0`. The run this describes is named by the directory it sits in and by `run_manifest.json` beside it; the rendering does not repeat it, so two runs of the same experiment produce the same document.

Code commit `e7728ebbaf3f353143a5faea2a54211bb5d16b12`.

## data

| Field | Value |
| --- | ---: |
| `assets` | 6 |
| `b0_rows` | 184632 |
| `b1_rows` | 184632 |
| `b2_rows` | 184632 |
| `common_evaluation_rows` | {"D": 61336, "V": 12672} |
| `duplicate_keys` | 0 |
| `masked_rows_by_role` | {"D": 152954, "V": 31678} |
| `provider_failures` | 0 |
| `sessions_by_role` | {"D": 389, "V": 80} |
| `sparse_session_assets` | 0 |

## b1

| Field | Value |
| --- | ---: |
| `b1_core_coverage` | 0.9934247584384072 |
| `b1_duplicate_contracts_per_snapshot` | 0 |
| `b1_median_quote_age_s` | 550.0 |
| `b1_missing_rate_share` | 0.4305375016248537 |
| `b1_p95_quote_age_s` | 1725.0 |
| `b1_post_cutoff_observations` | 0 |
| `b1_rows_dropped_for_rate_or_dividend` | 0 |
| `b1_surface_contracts_per_origin` | 783.1134906191776 |
| `b1_surface_expiry_coverage` | 0.9978281121365744 |

## b2

| Field | Value |
| --- | ---: |
| `b2_empty_window_share` | 0.0023181247021101434 |
| `b2_mean_provider_latency_s` | 1.221522874453539 |
| `b2_multileg_share` | 0.23693619596357562 |
| `b2_p95_provider_latency_s` | 0.3555064279213946 |
| `b2_pit_violation_count` | 0 |
| `b2_provider_failure_share` | 0.0 |
| `b2_zero_dte_count` | 102568762 |

## engineering

| Field | Value |
| --- | ---: |
| `artifact_sha256` | {"input_manifest.json": "9a2a1633127623a9ff806051ee75da5b57633e277619e3005ae41d22dbd20984", "rp2_block3_target/target_panel.parquet": "4723e433b7feb2043270c463924cfbc975ccf44cc665845f9ee80346770ba992", "rp2_block3_target/comparison.json": "4ac71484a10d24ee4353d0a137ce6cf97c076de2a4703e32195584581878a3fa", "rp2_block4_b0/b0_panel.parquet": "0fad590d0c12825b82b556c904e0d25f4e36e0fa616bb5bbfe80e27a6cd80a2a", "rp2_block4_b0/ladder.json": "9038505987b1043c43603bca177297d3a23c7b5e413d92a78c2b46b79628ef35", "rp2_block5_surface/b1_surface_panel.parquet": "3da2195176468f0f2fd83c6e3a085cb6436d026989cfdec7e6d4627ea2dec5ba", "rp2_block5_surface/surface_coverage.json": "ce518771dbcd0b84902b3f71346344e9cf08c9ecc4025aa8965328cf508ffbff", "rp2_block6_flow/b2_flow_panel.parquet": "5375ef33a13f188ebaa84dd4db5bb7813aecd2eb19f5b09027d725a8f9053eda", "rp2_block6_flow/flow_coverage.json": "d5836b7b4c12fcb6a91d2038c8f9cbb1c014a225fa7ebe13e5574f99f5a52b0f", "feature_registry_report.json": "028280aa2cacbe679ae11093f27692bba96e11c891f26ec6d69d2778d40958f0", "common_masks.json": "60b5a709af1db14e928b39b40648f78d54ba5689dabce6d7737177e271bbc4fc", "rp2_block8_ladder/ladder.json": "112a931e51748847e40c45843785253cc63866a97657838447c746010acd7894", "rp2_block7_dml/dml.json": "44f0b708a3ff6cce7f8a73cdc1c5618d4e670b2a394ecfdca6c75efb5ff2c99a", "rp2_block10_inference/inference.json": "05b059772907b6d57a7aaceeeee24a060144f8d7ac3888da42d950ad5e3ec3b2"} |
| `code_commit` | e7728ebbaf3f353143a5faea2a54211bb5d16b12 |
| `feature_registry_sha256` | 3c108a14a5a88e4da08bade7debd5dc05a1d51ea50c1e5adea6d1e88dc0acb9c |
| `input_manifest_sha256` | 11a158b302ade3c4c6b475f6cde973a93b275ec1c4b894ace66bccbc84ded8ab |
| `model_config_sha256` | 9ea917b7bcdf8835ef3a5abc772fc9d0fe714f6dfba0bcc6d5536ad1993d5dd8 |
| `peak_memory_bytes` | see `run_manifest.json` |
| `runtime_seconds` | see `run_manifest.json` |

## forecast

| Family | Role | QLIKE B0 | ΔB1 | ΔB2\|B1 | MDE ΔB1 |
| --- | --- | ---: | ---: | ---: | ---: |
| `gamma_glm` | D | 0.13860 | +0.00219 | -0.00002 | 0.00180 |
| `gamma_glm` | V | 0.17501 | -0.00113 | -0.00215 | 0.00411 |
| `lightgbm_qlike` | D | 0.13550 | +0.00253 | +0.00060 | 0.00325 |
| `lightgbm_qlike` | V | 0.19866 | +0.00211 | +0.00336 | 0.01517 |
| `ridge_log` | D | 0.13910 | +0.00229 | +0.00017 | 0.00170 |
| `ridge_log` | V | 0.17851 | -0.00083 | -0.00194 | 0.00271 |

Calibration slope 1.0209977151573864, intercept 0.13799147209811324.
