-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- MDS650 gated research datasets as queryable tables (private DB, RLS locked:
-- no policies -> service-role only; same license posture as the Storage bucket).
create table public.dev_training_all_origins (
  "origin_id" text,
  "asset" text,
  "session_date" text,
  "forecast_origin_utc" timestamptz,
  "sample_role" text,
  "rv30" double precision,
  "target_future_close_count" bigint,
  "target_price_count" bigint,
  "target_validity" text,
  "b0_session_minute" bigint,
  "b0_fmp_bar_availability" text,
  "b0_spot" double precision,
  "b0_rv_5m_lag" double precision,
  "b0_rv_30m_lag" double precision,
  "b0_return_5m_lag" double precision,
  "b0_volume_5m_lag" double precision,
  "b0_source_timestamp_raw_utc" timestamptz,
  "b0_available_at_utc" timestamptz,
  "b0_feature_age_seconds" double precision,
  "b0_availability_valid" boolean,
  "b0_plus2_spot" double precision,
  "b0_plus2_rv_5m_lag" double precision,
  "b0_plus2_rv_30m_lag" double precision,
  "b0_plus2_return_5m_lag" double precision,
  "b0_plus2_volume_5m_lag" double precision,
  "b0_plus2_source_timestamp_raw_utc" timestamptz,
  "b0_plus2_available_at_utc" timestamptz,
  "b0_plus2_feature_age_seconds" double precision,
  "b0_plus2_availability_valid" boolean,
  "b1q_atm_iv" double precision,
  "b1a_complete" boolean,
  "b1q_pit_evidence_valid" boolean,
  "b1q_quote_not_after_origin" boolean,
  "b1q_valid_expiry_bucket_count" bigint,
  "b1q_median_quote_age" double precision,
  "b1q_median_relative_spread" double precision,
  "b1q_iv_inversion_success_rate" double precision,
  "b1q_missing_reason" text,
  "b2_window_start" timestamptz,
  "b2_window_end" timestamptz,
  "b2_max_operational_time" timestamptz,
  "b2_source_hash" text,
  "b2_option_activity_present" boolean,
  "b2_availability_semantics" text,
  "option_trade_count_5m" text,
  "unique_contract_count_5m" text,
  "total_premium_5m" double precision,
  "max_trade_premium_5m" double precision,
  "call_premium_5m" double precision,
  "put_premium_5m" double precision,
  "ask_side_premium_share" double precision,
  "bid_side_premium_share" double precision,
  "repeated_contract_premium" double precision,
  "strike_concentration" double precision,
  "expiry_concentration" double precision,
  "b2_log_trade_count" double precision,
  "b2_unique_contract_share" double precision,
  "b2_log_mean_trade_premium" double precision,
  "b2_log_max_trade_premium" double precision,
  "b2_call_put_premium_imbalance_scaled" double precision,
  "b2_execution_side_premium_imbalance" double precision,
  "b2_repeated_contract_premium_share" double precision,
  "b2_strike_concentration" double precision,
  "b2_expiry_concentration" double precision,
  "target_complete" boolean,
  "b0_complete" boolean,
  "b1a_common_complete" boolean,
  "common_complete" boolean,
  "exclusion_reason" text,
  "source_cohort" text,
  "source_origin_id" text,
  "b1q_max_sip_timestamp_ns" bigint
);
comment on table public.dev_training_all_origins is 'C1 development training panel, all origins (80 sessions): PIT features B0/B1/B2 + rv30 target per 5-min origin.';
alter table public.dev_training_all_origins enable row level security;
create index on public.dev_training_all_origins (session_date);
create table public.dev_training_common (like public.dev_training_all_origins including all);
comment on table public.dev_training_common is 'C1 development training panel restricted to common-complete origins.';
alter table public.dev_training_common enable row level security;
create table public.c1_development_forecasts (
  "origin_id" text,
  "asset" text,
  "session_date" text,
  "forecast_origin_utc" timestamptz,
  "rv30" double precision,
  "fold" integer,
  "model_role" text,
  "information_set" text,
  "forecast" double precision,
  "qlike_loss" double precision,
  "absolute_error" double precision,
  "squared_error" double precision,
  "selected_parameters" text,
  "feature_schema_sha256" text
);
comment on table public.c1_development_forecasts is 'C1 walk-forward development forecasts with QLIKE loss per origin x model x information set.';
alter table public.c1_development_forecasts enable row level security;
create index on public.c1_development_forecasts (session_date);
create table public.c5_frozen_evaluation_forecasts (
  "origin_id" text,
  "asset" text,
  "session_date" text,
  "forecast_origin_utc" timestamptz,
  "block_id" text,
  "session_tercile" text,
  "volatility_regime" text,
  "rv30" double precision,
  "model_name" text,
  "information_set" text,
  "forecast" double precision,
  "qlike_loss" double precision,
  "selected_parameters" text
);
comment on table public.c5_frozen_evaluation_forecasts is 'C5 frozen two-block (2024) evaluation forecasts; model_name har_rv is a log-linear fixed extension (docs/model_naming_note_v1.md).';
alter table public.c5_frozen_evaluation_forecasts enable row level security;
create index on public.c5_frozen_evaluation_forecasts (session_date);
create table public.b1v3_features (
  "origin_id" text,
  "asset" text,
  "session_date" text,
  "forecast_origin_utc" text,
  "forecast_origin_ns" bigint,
  "session_tercile" text,
  "quote_cutoff_seconds" bigint,
  "valid_contract_count" bigint,
  "valid_consensus_point_count" bigint,
  "max_sip_timestamp_ns" bigint,
  "source_request_hashes" text,
  "atm_expiry" text,
  "atm_dte" bigint,
  "atm_interpolated" boolean,
  "skew_put_interpolated" boolean,
  "skew_call_interpolated" boolean,
  "short_dte" bigint,
  "medium_dte" bigint,
  "long_dte" bigint,
  "b1v3_log_atm_variance_30d" double precision,
  "b1v3_log_symmetric_skew_30d" double precision,
  "b1v3_log_forward_variance_short_medium" double precision,
  "b1v3_log_forward_variance_medium_long" double precision,
  "b1v3_level_missing_reason" text,
  "b1v3_log_atm_variance_change_5m" double precision,
  "b1v3_log_atm_variance_change_30m" double precision,
  "b1v3_log_symmetric_skew_change_30m" double precision,
  "b1v3_log_forward_variance_short_medium_change_30m" double precision,
  "b1v3_log_forward_variance_medium_long_change_30m" double precision,
  "b1v3a_complete" boolean,
  "b1v3b_complete" boolean,
  "b1v3c_complete" boolean,
  "b1v3_missing_reason" text
);
comment on table public.b1v3_features is 'B1v3 target-blind IV consensus features per origin.';
alter table public.b1v3_features enable row level security;
create index on public.b1v3_features (session_date);
create table public.b2_mechanism_forecasts (
  "origin_id" text,
  "asset" text,
  "session_date" text,
  "b0_session_minute" bigint,
  "session_tercile" text,
  "volatility_regime" text,
  "rv30" double precision,
  "fold" integer,
  "model_name" text,
  "information_set" text,
  "mechanism_id" text,
  "b2_variant" text,
  "variant_type" text,
  "forecast" double precision,
  "qlike_loss" double precision,
  "absolute_error" double precision,
  "squared_error" double precision
);
comment on table public.b2_mechanism_forecasts is 'B2 mechanism study forecasts (1.55M rows) underlying the absorption analysis.';
alter table public.b2_mechanism_forecasts enable row level security;
create index on public.b2_mechanism_forecasts (session_date);
