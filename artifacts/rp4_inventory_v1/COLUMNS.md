# RP4: columnas exactas verificadas

Inventario previo a A1, no una especificación de modelos congelada.

## B0

Archivo: `private-input/154e9a45ff331c4b01f6`.

SHA256: `52d58fc297ee04aeec041d58657c7dd414c726f9a2b7b9a5c92bbd7e881e5e20`.

### Registro CORE + RICH existente (22)

```text
QQQ_ret_30
QQQ_rv_30
SPY_ret_30
SPY_rv_30
day_of_week
dollar_volume_30
jump_back_30
minutes_since_open
minutes_to_close
parkinson_30
ret_30
ret_5
rq_back_30
rs_down_back_30
rs_up_back_30
rv_back_15
rv_back_30
rv_back_5
rv_prev_day
rv_session_to_date
rv_week
volume_30
```

### Fuera del registro y las claves; clasificar, no incluir automáticamente (5)

```text
role
source
rv30
jump30
minute_bucket
```

### Esquema completo (solo nombres y tipos)

| Columna | Tipo |
| --- | --- |
| `asset` | large_string |
| `session_date` | large_string |
| `role` | large_string |
| `source` | large_string |
| `origin_minute` | int64 |
| `rv30` | double |
| `jump30` | double |
| `rv_back_5` | double |
| `rv_back_15` | double |
| `rv_back_30` | double |
| `rq_back_30` | double |
| `rs_up_back_30` | double |
| `rs_down_back_30` | double |
| `jump_back_30` | double |
| `rv_session_to_date` | double |
| `rv_prev_day` | double |
| `rv_week` | double |
| `ret_5` | double |
| `ret_30` | double |
| `parkinson_30` | double |
| `volume_30` | double |
| `dollar_volume_30` | double |
| `minutes_since_open` | double |
| `minutes_to_close` | double |
| `minute_bucket` | int64 |
| `day_of_week` | int8 |
| `SPY_rv_30` | double |
| `SPY_ret_30` | double |
| `QQQ_rv_30` | double |
| `QQQ_ret_30` | double |

## B1

Archivo: `private-input/290d4589aed2042c87a8`.

SHA256: `7e022d2845a4300be5f7d286337ec6ee4c0e5614fa00cacbc386924be3b37f33`.

### Registro CORE + RICH existente (28)

```text
b1_iv_30d
b1_iv_60d
b1_iv_7d
b1_iv_minus_trailing_rv_30d
b1_median_quote_age_s
b1_median_relative_spread
b1_risk_reversal_25
b1_smile_level
b1_surface_coverage
b1_term_slope
b1_butterfly_25
b1_butterfly_violations
b1_expiries
b1_forward_expiries_fitted
b1_implied_dividend_yield
b1_implied_rate
b1_iv_14d
b1_iv_90d
b1_max_log_moneyness
b1_mfiv
b1_min_log_moneyness
b1_pcp_residual
b1_smile_curvature
b1_smile_residual
b1_smile_slope
b1_strikes
b1_term_convexity
b1_zero_dte_contracts
```

### Fuera del registro y las claves; clasificar, no incluir automáticamente (9)

```text
b1_contracts
b1_p95_quote_age_s
b1_spans_call_wing
b1_spans_put_wing
b1_calendar_violations
b1_quote_duplicates_dropped
b1_post_cutoff_selected
b1_duplicate_contracts_remaining
b1_rows_dropped_for_rate_or_dividend
```

### Reconstrucción del conteo solicitado; incluye diagnósticos y no es una lista oficial (34)

```text
b1_contracts
b1_expiries
b1_strikes
b1_median_quote_age_s
b1_p95_quote_age_s
b1_median_relative_spread
b1_forward_expiries_fitted
b1_min_log_moneyness
b1_max_log_moneyness
b1_spans_call_wing
b1_spans_put_wing
b1_zero_dte_contracts
b1_surface_coverage
b1_smile_level
b1_pcp_residual
b1_calendar_violations
b1_butterfly_violations
b1_iv_7d
b1_iv_14d
b1_iv_30d
b1_iv_60d
b1_iv_90d
b1_term_slope
b1_term_convexity
b1_smile_slope
b1_smile_curvature
b1_smile_residual
b1_risk_reversal_25
b1_butterfly_25
b1_mfiv
b1_implied_rate
b1_implied_dividend_yield
b1_rows_dropped_for_rate_or_dividend
b1_iv_minus_trailing_rv_30d
```

### Histogramas de calidad, no selección automática de predictores (74)

```text
b1_quote_age_bin_0
b1_quote_age_bin_1
b1_quote_age_bin_2
b1_quote_age_bin_3
b1_quote_age_bin_4
b1_quote_age_bin_5
b1_quote_age_bin_6
b1_quote_age_bin_7
b1_quote_age_bin_8
b1_quote_age_bin_9
b1_quote_age_bin_10
b1_quote_age_bin_11
b1_quote_age_bin_12
b1_quote_age_bin_13
b1_quote_age_bin_14
b1_quote_age_bin_15
b1_quote_age_bin_16
b1_quote_age_bin_17
b1_quote_age_bin_18
b1_quote_age_bin_19
b1_quote_age_bin_20
b1_quote_age_bin_21
b1_quote_age_bin_22
b1_quote_age_bin_23
b1_quote_age_bin_24
b1_quote_age_bin_25
b1_quote_age_bin_26
b1_quote_age_bin_27
b1_quote_age_bin_28
b1_quote_age_bin_29
b1_quote_age_bin_30
b1_quote_age_bin_31
b1_quote_age_bin_32
b1_quote_age_bin_33
b1_quote_age_bin_34
b1_quote_age_bin_35
b1_quote_age_bin_36
b1_quote_age_bin_37
b1_quote_age_bin_38
b1_quote_age_bin_39
b1_quote_age_bin_40
b1_quote_age_bin_41
b1_quote_age_bin_42
b1_quote_age_bin_43
b1_quote_age_bin_44
b1_quote_age_bin_45
b1_quote_age_bin_46
b1_quote_age_bin_47
b1_quote_age_bin_48
b1_quote_age_bin_49
b1_quote_age_bin_50
b1_quote_age_bin_51
b1_quote_age_bin_52
b1_quote_age_bin_53
b1_quote_age_bin_54
b1_quote_age_bin_55
b1_quote_age_bin_56
b1_quote_age_bin_57
b1_quote_age_bin_58
b1_quote_age_bin_59
b1_quote_age_bin_60
b1_quote_age_bin_61
b1_quote_age_bin_62
b1_quote_age_bin_63
b1_quote_age_bin_64
b1_quote_age_bin_65
b1_quote_age_bin_66
b1_quote_age_bin_67
b1_quote_age_bin_68
b1_quote_age_bin_69
b1_quote_age_bin_70
b1_quote_age_bin_71
b1_quote_age_bin_72
b1_quote_age_bin_73
```

### Esquema completo (solo nombres y tipos)

| Columna | Tipo |
| --- | --- |
| `b1_contracts` | double |
| `b1_expiries` | double |
| `b1_strikes` | double |
| `b1_median_quote_age_s` | double |
| `b1_p95_quote_age_s` | double |
| `b1_median_relative_spread` | double |
| `b1_quote_age_bin_0` | double |
| `b1_quote_age_bin_1` | double |
| `b1_quote_age_bin_2` | double |
| `b1_quote_age_bin_3` | double |
| `b1_quote_age_bin_4` | double |
| `b1_quote_age_bin_5` | double |
| `b1_quote_age_bin_6` | double |
| `b1_quote_age_bin_7` | double |
| `b1_quote_age_bin_8` | double |
| `b1_quote_age_bin_9` | double |
| `b1_quote_age_bin_10` | double |
| `b1_quote_age_bin_11` | double |
| `b1_quote_age_bin_12` | double |
| `b1_quote_age_bin_13` | double |
| `b1_quote_age_bin_14` | double |
| `b1_quote_age_bin_15` | double |
| `b1_quote_age_bin_16` | double |
| `b1_quote_age_bin_17` | double |
| `b1_quote_age_bin_18` | double |
| `b1_quote_age_bin_19` | double |
| `b1_quote_age_bin_20` | double |
| `b1_quote_age_bin_21` | double |
| `b1_quote_age_bin_22` | double |
| `b1_quote_age_bin_23` | double |
| `b1_quote_age_bin_24` | double |
| `b1_quote_age_bin_25` | double |
| `b1_quote_age_bin_26` | double |
| `b1_quote_age_bin_27` | double |
| `b1_quote_age_bin_28` | double |
| `b1_quote_age_bin_29` | double |
| `b1_quote_age_bin_30` | double |
| `b1_quote_age_bin_31` | double |
| `b1_quote_age_bin_32` | double |
| `b1_quote_age_bin_33` | double |
| `b1_quote_age_bin_34` | double |
| `b1_quote_age_bin_35` | double |
| `b1_quote_age_bin_36` | double |
| `b1_quote_age_bin_37` | double |
| `b1_quote_age_bin_38` | double |
| `b1_quote_age_bin_39` | double |
| `b1_quote_age_bin_40` | double |
| `b1_quote_age_bin_41` | double |
| `b1_quote_age_bin_42` | double |
| `b1_quote_age_bin_43` | double |
| `b1_quote_age_bin_44` | double |
| `b1_quote_age_bin_45` | double |
| `b1_quote_age_bin_46` | double |
| `b1_quote_age_bin_47` | double |
| `b1_quote_age_bin_48` | double |
| `b1_quote_age_bin_49` | double |
| `b1_quote_age_bin_50` | double |
| `b1_quote_age_bin_51` | double |
| `b1_quote_age_bin_52` | double |
| `b1_quote_age_bin_53` | double |
| `b1_quote_age_bin_54` | double |
| `b1_quote_age_bin_55` | double |
| `b1_quote_age_bin_56` | double |
| `b1_quote_age_bin_57` | double |
| `b1_quote_age_bin_58` | double |
| `b1_quote_age_bin_59` | double |
| `b1_quote_age_bin_60` | double |
| `b1_quote_age_bin_61` | double |
| `b1_quote_age_bin_62` | double |
| `b1_quote_age_bin_63` | double |
| `b1_quote_age_bin_64` | double |
| `b1_quote_age_bin_65` | double |
| `b1_quote_age_bin_66` | double |
| `b1_quote_age_bin_67` | double |
| `b1_quote_age_bin_68` | double |
| `b1_quote_age_bin_69` | double |
| `b1_quote_age_bin_70` | double |
| `b1_quote_age_bin_71` | double |
| `b1_quote_age_bin_72` | double |
| `b1_quote_age_bin_73` | double |
| `b1_forward_expiries_fitted` | double |
| `b1_min_log_moneyness` | double |
| `b1_max_log_moneyness` | double |
| `b1_spans_call_wing` | double |
| `b1_spans_put_wing` | double |
| `b1_zero_dte_contracts` | double |
| `b1_surface_coverage` | double |
| `b1_smile_level` | double |
| `b1_pcp_residual` | double |
| `b1_calendar_violations` | double |
| `b1_butterfly_violations` | double |
| `b1_iv_7d` | double |
| `b1_iv_14d` | double |
| `b1_iv_30d` | double |
| `b1_iv_60d` | double |
| `b1_iv_90d` | double |
| `b1_term_slope` | double |
| `b1_term_convexity` | double |
| `b1_smile_slope` | double |
| `b1_smile_curvature` | double |
| `b1_smile_residual` | double |
| `b1_risk_reversal_25` | double |
| `b1_butterfly_25` | double |
| `b1_mfiv` | double |
| `b1_implied_rate` | double |
| `b1_implied_dividend_yield` | double |
| `origin_minute` | int64 |
| `b1_quote_duplicates_dropped` | double |
| `b1_post_cutoff_selected` | double |
| `b1_duplicate_contracts_remaining` | double |
| `b1_rows_dropped_for_rate_or_dividend` | double |
| `b1_iv_minus_trailing_rv_30d` | double |
| `asset` | large_string |
| `session_date` | large_string |

## B2

Archivo: `private-input/8a4c5029ae2168842e57`.

SHA256: `61c9843d79c6b63472e547b50334859c268183bdf1dee8864de6130491f465c6`.

### Registro CORE + RICH existente (68)

```text
b2_5m_buy_premium_share
b2_5m_d_iv
b2_5m_decay_intensity_innovation
b2_5m_delta_flow
b2_5m_mean_provider_latency_s
b2_5m_multileg_size_share
b2_5m_premium
b2_5m_strike_hhi
b2_5m_trades
b2_5m_vega_flow
b2_5m_vega_flow_short_dte
b2_5m_zero_dte_premium_share
b2_30m_buy_premium_share
b2_30m_contracts
b2_30m_d_iv
b2_30m_d_mid_rel
b2_30m_d_spread
b2_30m_decay_intensity_innovation
b2_30m_decay_intensity_last
b2_30m_delta_flow
b2_30m_gamma_flow
b2_30m_is_empty_window
b2_30m_late_arrival_share
b2_30m_mean_provider_latency_s
b2_30m_multileg_premium_share
b2_30m_multileg_size_share
b2_30m_observed_span_s
b2_30m_otm_premium_share
b2_30m_passive_premium_share
b2_30m_premium
b2_30m_rate_per_second
b2_30m_sell_premium_share
b2_30m_size
b2_30m_sweep_premium_share
b2_30m_trades
b2_30m_vega_flow
b2_30m_vega_flow_abs
b2_30m_vega_flow_call
b2_30m_vega_flow_long_dte
b2_30m_vega_flow_put
b2_30m_vega_flow_short_dte
b2_30m_zero_dte_premium_share
b2_30m_zero_dte_signed_premium
b2_30m_zero_dte_trade_share
b2_5m_contract_entropy
b2_5m_contracts
b2_5m_d_mid_rel
b2_5m_d_spread
b2_5m_decay_intensity_last
b2_5m_expiry_hhi
b2_5m_gamma_flow
b2_5m_interarrival_cv
b2_5m_is_empty_window
b2_5m_late_arrival_share
b2_5m_multileg_premium_share
b2_5m_observed_span_s
b2_5m_otm_premium_share
b2_5m_passive_premium_share
b2_5m_rate_per_second
b2_5m_sell_premium_share
b2_5m_size
b2_5m_sweep_premium_share
b2_5m_vega_flow_abs
b2_5m_vega_flow_call
b2_5m_vega_flow_long_dte
b2_5m_vega_flow_put
b2_5m_zero_dte_signed_premium
b2_5m_zero_dte_trade_share
```

### Fuera del registro y las claves; clasificar, no incluir automáticamente (9)

```text
b2_pit_violations
b2_zero_dte_trades
b2_counting_trades
b2_counting_mean_latency_s
b2_counting_p95_latency_s
b2_5m_mean_age_s
b2_5m_p95_provider_latency_s
b2_30m_mean_age_s
b2_30m_p95_provider_latency_s
```

### Reconstrucción del conteo solicitado; incluye diagnósticos y no es una lista oficial (74)

```text
b2_zero_dte_trades
b2_counting_trades
b2_5m_trades
b2_5m_contracts
b2_5m_size
b2_5m_premium
b2_5m_vega_flow
b2_5m_gamma_flow
b2_5m_delta_flow
b2_5m_vega_flow_abs
b2_5m_vega_flow_call
b2_5m_vega_flow_put
b2_5m_vega_flow_short_dte
b2_5m_vega_flow_long_dte
b2_5m_otm_premium_share
b2_5m_buy_premium_share
b2_5m_sell_premium_share
b2_5m_passive_premium_share
b2_5m_sweep_premium_share
b2_5m_multileg_size_share
b2_5m_multileg_premium_share
b2_5m_d_iv
b2_5m_d_mid_rel
b2_5m_d_spread
b2_5m_decay_intensity_last
b2_5m_decay_intensity_innovation
b2_5m_rate_per_second
b2_5m_observed_span_s
b2_5m_is_empty_window
b2_5m_mean_age_s
b2_5m_mean_provider_latency_s
b2_5m_late_arrival_share
b2_5m_p95_provider_latency_s
b2_5m_zero_dte_premium_share
b2_5m_zero_dte_signed_premium
b2_5m_zero_dte_trade_share
b2_5m_strike_hhi
b2_5m_expiry_hhi
b2_5m_contract_entropy
b2_5m_interarrival_cv
b2_30m_trades
b2_30m_contracts
b2_30m_size
b2_30m_premium
b2_30m_vega_flow
b2_30m_gamma_flow
b2_30m_delta_flow
b2_30m_vega_flow_abs
b2_30m_vega_flow_call
b2_30m_vega_flow_put
b2_30m_vega_flow_short_dte
b2_30m_vega_flow_long_dte
b2_30m_otm_premium_share
b2_30m_buy_premium_share
b2_30m_sell_premium_share
b2_30m_passive_premium_share
b2_30m_sweep_premium_share
b2_30m_multileg_size_share
b2_30m_multileg_premium_share
b2_30m_d_iv
b2_30m_d_mid_rel
b2_30m_d_spread
b2_30m_decay_intensity_last
b2_30m_decay_intensity_innovation
b2_30m_rate_per_second
b2_30m_observed_span_s
b2_30m_is_empty_window
b2_30m_mean_age_s
b2_30m_mean_provider_latency_s
b2_30m_late_arrival_share
b2_30m_p95_provider_latency_s
b2_30m_zero_dte_premium_share
b2_30m_zero_dte_signed_premium
b2_30m_zero_dte_trade_share
```

### Histogramas de calidad, no selección automática de predictores (61)

```text
b2_latency_bin_0
b2_latency_bin_1
b2_latency_bin_2
b2_latency_bin_3
b2_latency_bin_4
b2_latency_bin_5
b2_latency_bin_6
b2_latency_bin_7
b2_latency_bin_8
b2_latency_bin_9
b2_latency_bin_10
b2_latency_bin_11
b2_latency_bin_12
b2_latency_bin_13
b2_latency_bin_14
b2_latency_bin_15
b2_latency_bin_16
b2_latency_bin_17
b2_latency_bin_18
b2_latency_bin_19
b2_latency_bin_20
b2_latency_bin_21
b2_latency_bin_22
b2_latency_bin_23
b2_latency_bin_24
b2_latency_bin_25
b2_latency_bin_26
b2_latency_bin_27
b2_latency_bin_28
b2_latency_bin_29
b2_latency_bin_30
b2_latency_bin_31
b2_latency_bin_32
b2_latency_bin_33
b2_latency_bin_34
b2_latency_bin_35
b2_latency_bin_36
b2_latency_bin_37
b2_latency_bin_38
b2_latency_bin_39
b2_latency_bin_40
b2_latency_bin_41
b2_latency_bin_42
b2_latency_bin_43
b2_latency_bin_44
b2_latency_bin_45
b2_latency_bin_46
b2_latency_bin_47
b2_latency_bin_48
b2_latency_bin_49
b2_latency_bin_50
b2_latency_bin_51
b2_latency_bin_52
b2_latency_bin_53
b2_latency_bin_54
b2_latency_bin_55
b2_latency_bin_56
b2_latency_bin_57
b2_latency_bin_58
b2_latency_bin_59
b2_latency_bin_60
```

### Esquema completo (solo nombres y tipos)

| Columna | Tipo |
| --- | --- |
| `origin_minute` | int64 |
| `b2_pit_violations` | double |
| `b2_zero_dte_trades` | double |
| `b2_counting_trades` | double |
| `b2_counting_mean_latency_s` | double |
| `b2_counting_p95_latency_s` | double |
| `b2_latency_bin_0` | double |
| `b2_latency_bin_1` | double |
| `b2_latency_bin_2` | double |
| `b2_latency_bin_3` | double |
| `b2_latency_bin_4` | double |
| `b2_latency_bin_5` | double |
| `b2_latency_bin_6` | double |
| `b2_latency_bin_7` | double |
| `b2_latency_bin_8` | double |
| `b2_latency_bin_9` | double |
| `b2_latency_bin_10` | double |
| `b2_latency_bin_11` | double |
| `b2_latency_bin_12` | double |
| `b2_latency_bin_13` | double |
| `b2_latency_bin_14` | double |
| `b2_latency_bin_15` | double |
| `b2_latency_bin_16` | double |
| `b2_latency_bin_17` | double |
| `b2_latency_bin_18` | double |
| `b2_latency_bin_19` | double |
| `b2_latency_bin_20` | double |
| `b2_latency_bin_21` | double |
| `b2_latency_bin_22` | double |
| `b2_latency_bin_23` | double |
| `b2_latency_bin_24` | double |
| `b2_latency_bin_25` | double |
| `b2_latency_bin_26` | double |
| `b2_latency_bin_27` | double |
| `b2_latency_bin_28` | double |
| `b2_latency_bin_29` | double |
| `b2_latency_bin_30` | double |
| `b2_latency_bin_31` | double |
| `b2_latency_bin_32` | double |
| `b2_latency_bin_33` | double |
| `b2_latency_bin_34` | double |
| `b2_latency_bin_35` | double |
| `b2_latency_bin_36` | double |
| `b2_latency_bin_37` | double |
| `b2_latency_bin_38` | double |
| `b2_latency_bin_39` | double |
| `b2_latency_bin_40` | double |
| `b2_latency_bin_41` | double |
| `b2_latency_bin_42` | double |
| `b2_latency_bin_43` | double |
| `b2_latency_bin_44` | double |
| `b2_latency_bin_45` | double |
| `b2_latency_bin_46` | double |
| `b2_latency_bin_47` | double |
| `b2_latency_bin_48` | double |
| `b2_latency_bin_49` | double |
| `b2_latency_bin_50` | double |
| `b2_latency_bin_51` | double |
| `b2_latency_bin_52` | double |
| `b2_latency_bin_53` | double |
| `b2_latency_bin_54` | double |
| `b2_latency_bin_55` | double |
| `b2_latency_bin_56` | double |
| `b2_latency_bin_57` | double |
| `b2_latency_bin_58` | double |
| `b2_latency_bin_59` | double |
| `b2_latency_bin_60` | double |
| `b2_5m_trades` | double |
| `b2_5m_contracts` | double |
| `b2_5m_size` | double |
| `b2_5m_premium` | double |
| `b2_5m_vega_flow` | double |
| `b2_5m_gamma_flow` | double |
| `b2_5m_delta_flow` | double |
| `b2_5m_vega_flow_abs` | double |
| `b2_5m_vega_flow_call` | double |
| `b2_5m_vega_flow_put` | double |
| `b2_5m_vega_flow_short_dte` | double |
| `b2_5m_vega_flow_long_dte` | double |
| `b2_5m_otm_premium_share` | double |
| `b2_5m_buy_premium_share` | double |
| `b2_5m_sell_premium_share` | double |
| `b2_5m_passive_premium_share` | double |
| `b2_5m_sweep_premium_share` | double |
| `b2_5m_multileg_size_share` | double |
| `b2_5m_multileg_premium_share` | double |
| `b2_5m_d_iv` | double |
| `b2_5m_d_mid_rel` | double |
| `b2_5m_d_spread` | double |
| `b2_5m_decay_intensity_last` | double |
| `b2_5m_decay_intensity_innovation` | double |
| `b2_5m_rate_per_second` | double |
| `b2_5m_observed_span_s` | double |
| `b2_5m_is_empty_window` | double |
| `b2_5m_mean_age_s` | double |
| `b2_5m_mean_provider_latency_s` | double |
| `b2_5m_late_arrival_share` | double |
| `b2_5m_p95_provider_latency_s` | double |
| `b2_5m_zero_dte_premium_share` | double |
| `b2_5m_zero_dte_signed_premium` | double |
| `b2_5m_zero_dte_trade_share` | double |
| `b2_5m_strike_hhi` | double |
| `b2_5m_expiry_hhi` | double |
| `b2_5m_contract_entropy` | double |
| `b2_5m_interarrival_cv` | double |
| `b2_30m_trades` | double |
| `b2_30m_contracts` | double |
| `b2_30m_size` | double |
| `b2_30m_premium` | double |
| `b2_30m_vega_flow` | double |
| `b2_30m_gamma_flow` | double |
| `b2_30m_delta_flow` | double |
| `b2_30m_vega_flow_abs` | double |
| `b2_30m_vega_flow_call` | double |
| `b2_30m_vega_flow_put` | double |
| `b2_30m_vega_flow_short_dte` | double |
| `b2_30m_vega_flow_long_dte` | double |
| `b2_30m_otm_premium_share` | double |
| `b2_30m_buy_premium_share` | double |
| `b2_30m_sell_premium_share` | double |
| `b2_30m_passive_premium_share` | double |
| `b2_30m_sweep_premium_share` | double |
| `b2_30m_multileg_size_share` | double |
| `b2_30m_multileg_premium_share` | double |
| `b2_30m_d_iv` | double |
| `b2_30m_d_mid_rel` | double |
| `b2_30m_d_spread` | double |
| `b2_30m_decay_intensity_last` | double |
| `b2_30m_decay_intensity_innovation` | double |
| `b2_30m_rate_per_second` | double |
| `b2_30m_observed_span_s` | double |
| `b2_30m_is_empty_window` | double |
| `b2_30m_mean_age_s` | double |
| `b2_30m_mean_provider_latency_s` | double |
| `b2_30m_late_arrival_share` | double |
| `b2_30m_p95_provider_latency_s` | double |
| `b2_30m_zero_dte_premium_share` | double |
| `b2_30m_zero_dte_signed_premium` | double |
| `b2_30m_zero_dte_trade_share` | double |
| `asset` | large_string |
| `session_date` | large_string |

## target

Archivo: `private-input/ce6bf6f13a0b59fbd2a0`.

SHA256: `fdab55c524a6ee2cd94bb3f1f544dec527e1c8813f9a03d6e17ed8029f842831`.

### Fuera del registro y las claves; clasificar, no incluir automáticamente (49)

```text
role
source
rv_session_to_date
rv_prev_day
rv_5
bv_5
jump_5
continuous_5
rq_5
rs_up_5
rs_down_5
rv_back_5
noise_5
rv_15
bv_15
jump_15
continuous_15
rq_15
rs_up_15
rs_down_15
rv_back_15
noise_15
rv_30
bv_30
jump_30
continuous_30
rq_30
rs_up_30
rs_down_30
rv_back_30
noise_30
rv_60
bv_60
jump_60
continuous_60
rq_60
rs_up_60
rs_down_60
rv_back_60
noise_60
rv_120
bv_120
jump_120
continuous_120
rq_120
rs_up_120
rs_down_120
rv_back_120
noise_120
```

### Esquema completo (solo nombres y tipos)

| Columna | Tipo |
| --- | --- |
| `asset` | large_string |
| `session_date` | large_string |
| `role` | large_string |
| `source` | large_string |
| `origin_minute` | int64 |
| `rv_session_to_date` | double |
| `rv_prev_day` | double |
| `rv_5` | double |
| `bv_5` | double |
| `jump_5` | double |
| `continuous_5` | double |
| `rq_5` | double |
| `rs_up_5` | double |
| `rs_down_5` | double |
| `rv_back_5` | double |
| `noise_5` | double |
| `rv_15` | double |
| `bv_15` | double |
| `jump_15` | double |
| `continuous_15` | double |
| `rq_15` | double |
| `rs_up_15` | double |
| `rs_down_15` | double |
| `rv_back_15` | double |
| `noise_15` | double |
| `rv_30` | double |
| `bv_30` | double |
| `jump_30` | double |
| `continuous_30` | double |
| `rq_30` | double |
| `rs_up_30` | double |
| `rs_down_30` | double |
| `rv_back_30` | double |
| `noise_30` | double |
| `rv_60` | double |
| `bv_60` | double |
| `jump_60` | double |
| `continuous_60` | double |
| `rq_60` | double |
| `rs_up_60` | double |
| `rs_down_60` | double |
| `rv_back_60` | double |
| `noise_60` | double |
| `rv_120` | double |
| `bv_120` | double |
| `jump_120` | double |
| `continuous_120` | double |
| `rq_120` | double |
| `rs_up_120` | double |
| `rs_down_120` | double |
| `rv_back_120` | double |
| `noise_120` | double |

## HARQ: columnas del productor existente, no materializadas aquí

```text
log_rv_30m
log_rv_session
log_rv_day
log_rv_week
minute_fraction
minute_fraction_sq
rq_attenuation
```
