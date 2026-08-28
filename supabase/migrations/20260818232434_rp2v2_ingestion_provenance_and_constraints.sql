-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- RP2-v2 hardening, part 1: provenance, constraints and an atomic publish path.
-- Additive and reversible. The heavy rewrites (type casts, PKs on 1.55M rows) stay in
-- supabase/migrations_pending/ because they require a duplicate audit first.

-- Every row that reaches a published table must name the run that produced it, and every
-- run must carry the byte hashes of what it read. Without this a number in the catalogue
-- cannot be traced back to a file.
create table if not exists public.ingestion_runs (
  run_id            text primary key,
  started_at        timestamptz not null default now(),
  completed_at      timestamptz,
  status            text not null default 'RUNNING',
  code_commit       text,
  inputs_sha256     text,
  input_count       integer not null default 0,
  rows_published    bigint  not null default 0,
  note              text,
  constraint ingestion_runs_status_check
    check (status in ('RUNNING', 'PUBLISHED', 'FAILED', 'SUPERSEDED')),
  constraint ingestion_runs_completed_after_start
    check (completed_at is null or completed_at >= started_at),
  constraint ingestion_runs_rows_non_negative check (rows_published >= 0)
);
comment on table public.ingestion_runs is
  'One row per RP2 ingestion. status advances RUNNING -> PUBLISHED or FAILED; a re-publish marks the previous run SUPERSEDED rather than deleting it.';

create table if not exists public.ingestion_inputs (
  run_id        text not null references public.ingestion_runs(run_id) on delete cascade,
  input_name    text not null,
  path          text not null,
  provider      text not null,
  sha256        text not null,
  bytes         bigint not null,
  rows          bigint,
  schema_sha256 text,
  time_min      text,
  time_max      text,
  primary key (run_id, input_name),
  constraint ingestion_inputs_provider_check
    check (provider in ('fmp', 'massive', 'unusual_whales', 'derived', 'synthetic')),
  constraint ingestion_inputs_sha256_shape check (sha256 ~ '^[0-9a-f]{64}$'),
  constraint ingestion_inputs_bytes_positive check (bytes > 0)
);
comment on table public.ingestion_inputs is
  'Byte SHA-256 plus schema, row count and time span per input file of a run. The sha256 CHECK enforces the shape so a truncated or placeholder hash cannot be stored.';

create index if not exists ingestion_inputs_sha256_idx on public.ingestion_inputs(sha256);
create index if not exists ingestion_runs_status_idx on public.ingestion_runs(status);

-- Tighten the RP2 catalogue tables added earlier: provenance, NOT NULL and CHECKs.
alter table public.rp2_blocks
  add column if not exists run_id text references public.ingestion_runs(run_id),
  add column if not exists updated_at timestamptz not null default now();

alter table public.rp2_blocks drop constraint if exists rp2_blocks_status_check;
alter table public.rp2_blocks add constraint rp2_blocks_status_check
  check (status in ('COMPLETED', 'PARTIAL', 'OPEN', 'BLOCKED', 'NOT_RUN'));

alter table public.rp2_power
  add column if not exists run_id text references public.ingestion_runs(run_id),
  add column if not exists method text not null default 'blocked_simulation';

alter table public.rp2_power drop constraint if exists rp2_power_contrast_check;
alter table public.rp2_power add constraint rp2_power_contrast_check
  check (contrast in ('variance', 'direction'));

alter table public.rp2_power drop constraint if exists rp2_power_probabilities;
alter table public.rp2_power add constraint rp2_power_probabilities
  check (
    (power_n30  is null or power_n30  between 0 and 1) and
    (power_n60  is null or power_n60  between 0 and 1) and
    (power_n120 is null or power_n120 between 0 and 1)
  );

alter table public.rp2_power drop constraint if exists rp2_power_method_check;
alter table public.rp2_power add constraint rp2_power_method_check
  check (method in ('blocked_simulation', 'ex_post_max_t_INVALIDATED'));

-- The rows loaded before this migration came from the ex-post max-|t| rescaling, which
-- is invalidated. They are relabelled, not deleted: the record of what was reported
-- stands, and the label says it must not be used.
update public.rp2_power set method = 'ex_post_max_t_INVALIDATED' where run_id is null;

alter table public.rp2_extensions
  add column if not exists run_id text references public.ingestion_runs(run_id);

alter table public.rp2_extensions drop constraint if exists rp2_extensions_result_check;
alter table public.rp2_extensions add constraint rp2_extensions_result_check
  check (result in ('POSITIVE', 'NEGATIVE', 'DONE', 'OPEN', 'DIRECTION, NOT VARIANCE'));
