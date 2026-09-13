# Descriptive MAE and RMSE

Robustness committed in the proposal, executed after the primary read; does not select models or change the headline; reported regardless of outcome.

Saved predictions; zero new fits. Units are non-annualized realized variance. Errors are averaged equally by asset and session; RMSE is the square root of the mean squared error. Descriptive 95% intervals use five-session blocks, 9,999 resamples and seed 20260907. No hypothesis tests or model selection. The source closure records 72 estimates independently recalculated from verified saved predictions; this import does not repeat that computation. The historical "confirmation" window is not independent prospective confirmation.

| RV | Window | Family | Set | Metric | Estimate | 95% CI | Sessions | Origins |
|---:|---|---|---|---|---:|---|---:|---:|
| 15 | primary | log_ridge_harq | B0 | MAE | 4.6811776e-06 | [3.5028882e-06, 6.5897969e-06] | 419 | 160832 |
| 15 | primary | log_ridge_harq | B0 | RMSE | 3.3641832e-05 | [8.5499885e-06, 5.6705972e-05] | 419 | 160832 |
| 15 | primary | log_ridge_harq | B1 | MAE | 4.7195749e-06 | [3.5023223e-06, 6.6947178e-06] | 419 | 160832 |
| 15 | primary | log_ridge_harq | B1 | RMSE | 3.3551646e-05 | [8.5570322e-06, 5.6553072e-05] | 419 | 160832 |
| 15 | primary | log_ridge_harq | B2 | MAE | 4.6911436e-06 | [3.497845e-06, 6.6292821e-06] | 419 | 160832 |
| 15 | primary | log_ridge_harq | B2 | RMSE | 3.3519018e-05 | [8.5172e-06, 5.6516676e-05] | 419 | 160832 |
| 15 | primary | lightgbm_qlike | B0 | MAE | 4.737404e-06 | [3.4726715e-06, 6.8169995e-06] | 419 | 160832 |
| 15 | primary | lightgbm_qlike | B0 | RMSE | 3.4772374e-05 | [8.8382157e-06, 5.8604808e-05] | 419 | 160832 |
| 15 | primary | lightgbm_qlike | B1 | MAE | 4.7704735e-06 | [3.466591e-06, 6.9216754e-06] | 419 | 160832 |
| 15 | primary | lightgbm_qlike | B1 | RMSE | 3.4857009e-05 | [8.8279463e-06, 5.8740079e-05] | 419 | 160832 |
| 15 | primary | lightgbm_qlike | B2 | MAE | 4.7803196e-06 | [3.4621579e-06, 6.954714e-06] | 419 | 160832 |
| 15 | primary | lightgbm_qlike | B2 | RMSE | 3.487629e-05 | [8.7309796e-06, 5.8837915e-05] | 419 | 160832 |
| 15 | confirmation | log_ridge_harq | B0 | MAE | 2.7974118e-06 | [2.3811482e-06, 3.2137905e-06] | 25 | 9750 |
| 15 | confirmation | log_ridge_harq | B0 | RMSE | 7.3787273e-06 | [4.4395927e-06, 1.0341535e-05] | 25 | 9750 |
| 15 | confirmation | log_ridge_harq | B1 | MAE | 2.7543007e-06 | [2.352568e-06, 3.1579479e-06] | 25 | 9750 |
| 15 | confirmation | log_ridge_harq | B1 | RMSE | 7.3715354e-06 | [4.4272087e-06, 1.0335512e-05] | 25 | 9750 |
| 15 | confirmation | log_ridge_harq | B2 | MAE | 2.7487798e-06 | [2.3502874e-06, 3.146776e-06] | 25 | 9750 |
| 15 | confirmation | log_ridge_harq | B2 | RMSE | 7.3625381e-06 | [4.4126848e-06, 1.033036e-05] | 25 | 9750 |
| 15 | confirmation | lightgbm_qlike | B0 | MAE | 2.787286e-06 | [2.3410507e-06, 3.2405279e-06] | 25 | 9750 |
| 15 | confirmation | lightgbm_qlike | B0 | RMSE | 7.458954e-06 | [4.5602283e-06, 1.0379975e-05] | 25 | 9750 |
| 15 | confirmation | lightgbm_qlike | B1 | MAE | 2.7306503e-06 | [2.307513e-06, 3.1646509e-06] | 25 | 9750 |
| 15 | confirmation | lightgbm_qlike | B1 | RMSE | 7.3773192e-06 | [4.4112544e-06, 1.0360401e-05] | 25 | 9750 |
| 15 | confirmation | lightgbm_qlike | B2 | MAE | 2.7585206e-06 | [2.3450883e-06, 3.1881147e-06] | 25 | 9750 |
| 15 | confirmation | lightgbm_qlike | B2 | RMSE | 7.3793407e-06 | [4.4053916e-06, 1.0378173e-05] | 25 | 9750 |
| 30 | primary | log_ridge_harq | B0 | MAE | 8.0258249e-06 | [6.0078862e-06, 1.1307157e-05] | 419 | 160832 |
| 30 | primary | log_ridge_harq | B0 | RMSE | 5.1039098e-05 | [1.4433906e-05, 8.537393e-05] | 419 | 160832 |
| 30 | primary | log_ridge_harq | B1 | MAE | 8.0913252e-06 | [5.995317e-06, 1.1493953e-05] | 419 | 160832 |
| 30 | primary | log_ridge_harq | B1 | RMSE | 5.0833303e-05 | [1.4508075e-05, 8.4977528e-05] | 419 | 160832 |
| 30 | primary | log_ridge_harq | B2 | MAE | 8.0327357e-06 | [5.9946219e-06, 1.1348205e-05] | 419 | 160832 |
| 30 | primary | log_ridge_harq | B2 | RMSE | 5.0749155e-05 | [1.4400634e-05, 8.4886645e-05] | 419 | 160832 |
| 30 | primary | lightgbm_qlike | B0 | MAE | 8.2027798e-06 | [5.9603796e-06, 1.1859054e-05] | 419 | 160832 |
| 30 | primary | lightgbm_qlike | B0 | RMSE | 5.3126218e-05 | [1.5239168e-05, 8.8688189e-05] | 419 | 160832 |
| 30 | primary | lightgbm_qlike | B1 | MAE | 8.3436001e-06 | [5.9430214e-06, 1.2307026e-05] | 419 | 160832 |
| 30 | primary | lightgbm_qlike | B1 | RMSE | 5.3410308e-05 | [1.4976894e-05, 8.9273135e-05] | 419 | 160832 |
| 30 | primary | lightgbm_qlike | B2 | MAE | 8.2796629e-06 | [5.9282263e-06, 1.2147733e-05] | 419 | 160832 |
| 30 | primary | lightgbm_qlike | B2 | RMSE | 5.3357675e-05 | [1.4914243e-05, 8.9205332e-05] | 419 | 160832 |
| 30 | confirmation | log_ridge_harq | B0 | MAE | 4.7185129e-06 | [3.9439801e-06, 5.4966633e-06] | 25 | 9750 |
| 30 | confirmation | log_ridge_harq | B0 | RMSE | 1.1230616e-05 | [7.0507578e-06, 1.5581888e-05] | 25 | 9750 |
| 30 | confirmation | log_ridge_harq | B1 | MAE | 4.6056141e-06 | [3.8699815e-06, 5.3513372e-06] | 25 | 9750 |
| 30 | confirmation | log_ridge_harq | B1 | RMSE | 1.1186832e-05 | [6.9706487e-06, 1.5551701e-05] | 25 | 9750 |
| 30 | confirmation | log_ridge_harq | B2 | MAE | 4.5921974e-06 | [3.8624939e-06, 5.3302977e-06] | 25 | 9750 |
| 30 | confirmation | log_ridge_harq | B2 | RMSE | 1.1165485e-05 | [6.923413e-06, 1.5539441e-05] | 25 | 9750 |
| 30 | confirmation | lightgbm_qlike | B0 | MAE | 4.6325132e-06 | [3.8307204e-06, 5.4760437e-06] | 25 | 9750 |
| 30 | confirmation | lightgbm_qlike | B0 | RMSE | 1.1249311e-05 | [7.0100863e-06, 1.5649265e-05] | 25 | 9750 |
| 30 | confirmation | lightgbm_qlike | B1 | MAE | 4.490723e-06 | [3.7320051e-06, 5.3086997e-06] | 25 | 9750 |
| 30 | confirmation | lightgbm_qlike | B1 | RMSE | 1.1153461e-05 | [6.7903196e-06, 1.5635681e-05] | 25 | 9750 |
| 30 | confirmation | lightgbm_qlike | B2 | MAE | 4.5293978e-06 | [3.8135075e-06, 5.3205556e-06] | 25 | 9750 |
| 30 | confirmation | lightgbm_qlike | B2 | RMSE | 1.1147961e-05 | [6.7825693e-06, 1.5637795e-05] | 25 | 9750 |
| 5 | primary | log_ridge_harq | B0 | MAE | 2.1431271e-06 | [1.6623025e-06, 2.8969682e-06] | 419 | 160832 |
| 5 | primary | log_ridge_harq | B0 | RMSE | 1.4390137e-05 | [4.1514979e-06, 2.4080049e-05] | 419 | 160832 |
| 5 | primary | log_ridge_harq | B1 | MAE | 2.1608334e-06 | [1.6654368e-06, 2.9410494e-06] | 419 | 160832 |
| 5 | primary | log_ridge_harq | B1 | RMSE | 1.4375489e-05 | [4.1671436e-06, 2.4044469e-05] | 419 | 160832 |
| 5 | primary | log_ridge_harq | B2 | MAE | 2.1557246e-06 | [1.6653809e-06, 2.9242353e-06] | 419 | 160832 |
| 5 | primary | log_ridge_harq | B2 | RMSE | 1.4370208e-05 | [4.1539029e-06, 2.4041901e-05] | 419 | 160832 |
| 5 | primary | lightgbm_qlike | B0 | MAE | 2.1422821e-06 | [1.639716e-06, 2.9435142e-06] | 419 | 160832 |
| 5 | primary | lightgbm_qlike | B0 | RMSE | 1.4839148e-05 | [4.2506534e-06, 2.4843886e-05] | 419 | 160832 |
| 5 | primary | lightgbm_qlike | B1 | MAE | 2.1467682e-06 | [1.6355393e-06, 2.9614325e-06] | 419 | 160832 |
| 5 | primary | lightgbm_qlike | B1 | RMSE | 1.4821522e-05 | [4.2211845e-06, 2.4820166e-05] | 419 | 160832 |
| 5 | primary | lightgbm_qlike | B2 | MAE | 2.1430084e-06 | [1.632497e-06, 2.9599883e-06] | 419 | 160832 |
| 5 | primary | lightgbm_qlike | B2 | RMSE | 1.4798689e-05 | [4.1986688e-06, 2.4792386e-05] | 419 | 160832 |
| 5 | confirmation | log_ridge_harq | B0 | MAE | 1.3154583e-06 | [1.1280785e-06, 1.5002511e-06] | 25 | 9750 |
| 5 | confirmation | log_ridge_harq | B0 | RMSE | 3.5845468e-06 | [2.2239739e-06, 5.0076242e-06] | 25 | 9750 |
| 5 | confirmation | log_ridge_harq | B1 | MAE | 1.3000249e-06 | [1.1159711e-06, 1.480706e-06] | 25 | 9750 |
| 5 | confirmation | log_ridge_harq | B1 | RMSE | 3.5825279e-06 | [2.2201232e-06, 5.0057306e-06] | 25 | 9750 |
| 5 | confirmation | log_ridge_harq | B2 | MAE | 1.2996426e-06 | [1.1153578e-06, 1.4806386e-06] | 25 | 9750 |
| 5 | confirmation | log_ridge_harq | B2 | RMSE | 3.5775887e-06 | [2.2200247e-06, 4.9989405e-06] | 25 | 9750 |
| 5 | confirmation | lightgbm_qlike | B0 | MAE | 1.3005554e-06 | [1.1095388e-06, 1.4894323e-06] | 25 | 9750 |
| 5 | confirmation | lightgbm_qlike | B0 | RMSE | 3.6148302e-06 | [2.2741209e-06, 5.0227712e-06] | 25 | 9750 |
| 5 | confirmation | lightgbm_qlike | B1 | MAE | 1.2858952e-06 | [1.1032576e-06, 1.4688529e-06] | 25 | 9750 |
| 5 | confirmation | lightgbm_qlike | B1 | RMSE | 3.5898632e-06 | [2.2191023e-06, 5.019016e-06] | 25 | 9750 |
| 5 | confirmation | lightgbm_qlike | B2 | MAE | 1.2888977e-06 | [1.1093907e-06, 1.4671371e-06] | 25 | 9750 |
| 5 | confirmation | lightgbm_qlike | B2 | RMSE | 3.5846758e-06 | [2.2145669e-06, 5.0148099e-06] | 25 | 9750 |

[Numerical source](secondary_metrics.csv), [execution receipt](secondary_metrics_receipt.json), [source closure](close_secondary_metrics.json) and [import provenance](import_receipt.json). MAE/RMSE are descriptive without tests; nothing changes the headline or registered sequence.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
