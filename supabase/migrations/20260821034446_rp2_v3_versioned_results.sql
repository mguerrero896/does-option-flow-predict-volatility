-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
alter table public.ingestion_runs
    add column if not exists spec_version text,
    add column if not exists branch_name text,
    add column if not exists feature_registry_sha256 text,
    add column if not exists model_config_sha256 text,
    add column if not exists inference_config_sha256 text,
    add column if not exists common_mask_sha256 text,
    add column if not exists scientific_sha256 text,
    add column if not exists attempt_log text;
comment on column public.ingestion_runs.spec_version is
    'Which frozen specification the run implements, e.g. rp2-v3.';
comment on column public.ingestion_runs.common_mask_sha256 is
    'Digest of the evaluation rows every contrast in this run was scored on.';
create table if not exists public.rp2_block_results (
    block_id text not null,
    run_id text not null references public.ingestion_runs(run_id) on delete restrict,
    status text not null,
    verdict text not null,
    document text not null,
    artifact_sha256 text not null check (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    supersedes_run_id text references public.ingestion_runs(run_id) on delete restrict,
    is_current boolean not null default false,
    created_at timestamptz not null default now(),
    primary key (block_id, run_id)
);
create unique index if not exists rp2_block_results_one_current_per_block
    on public.rp2_block_results (block_id) where is_current;
create table if not exists public.rp2_extension_results (
    extension_id text not null,
    run_id text not null references public.ingestion_runs(run_id) on delete restrict,
    question text not null,
    result text not null,
    evidence text not null,
    document text not null,
    artifact_sha256 text check (artifact_sha256 is null or artifact_sha256 ~ '^[0-9a-f]{64}$'),
    supersedes_run_id text references public.ingestion_runs(run_id) on delete restrict,
    is_current boolean not null default false,
    created_at timestamptz not null default now(),
    primary key (extension_id, run_id)
);
create unique index if not exists rp2_extension_results_one_current_per_extension
    on public.rp2_extension_results (extension_id) where is_current;
create table if not exists public.rp2_power_results (
    contrast text not null,
    role text not null,
    run_id text not null references public.ingestion_runs(run_id) on delete restrict,
    method text not null,
    detail text not null,
    sessions_for_80pct double precision,
    power_n30 double precision,
    power_n60 double precision,
    power_n120 double precision,
    note text,
    is_current boolean not null default false,
    created_at timestamptz not null default now(),
    primary key (contrast, role, detail, run_id)
);
create unique index if not exists rp2_power_results_one_current_per_contrast
    on public.rp2_power_results (contrast, role, detail) where is_current;
create table if not exists public.rp2_contrast_results (
    run_id text not null references public.ingestion_runs(run_id) on delete restrict,
    role text not null,
    model_family text not null,
    base_information_set text not null,
    expanded_information_set text not null,
    estimate double precision not null,
    ci_low double precision not null,
    ci_high double precision not null,
    p_value double precision not null check (p_value >= 0.0 and p_value <= 1.0),
    sessions integer not null check (sessions > 0),
    block_length integer not null check (block_length > 0),
    mde double precision not null check (mde > 0.0),
    equivalence_bound double precision not null check (equivalence_bound > 0.0),
    common_mask_sha256 text not null check (common_mask_sha256 ~ '^[0-9a-f]{64}$'),
    is_current boolean not null default false,
    created_at timestamptz not null default now(),
    primary key (run_id, role, model_family, base_information_set, expanded_information_set),
    check (ci_low <= estimate and estimate <= ci_high)
);
create unique index if not exists rp2_contrast_results_one_current_per_contrast
    on public.rp2_contrast_results (role, model_family, base_information_set, expanded_information_set)
    where is_current;
comment on table public.rp2_block_results is
    'RP2 block outcomes, versioned by run_id. One current row per block.';
comment on table public.rp2_contrast_results is
    'Session-level nested contrasts, versioned by run_id. Every row carries the mask it was measured on and the smallest effect its design could have detected.';
alter table public.rp2_block_results enable row level security;
alter table public.rp2_extension_results enable row level security;
alter table public.rp2_power_results enable row level security;
alter table public.rp2_contrast_results enable row level security;
create or replace view api.current_rp2_block_results as
select block_id, run_id, status, verdict, artifact_sha256, created_at
from public.rp2_block_results where is_current;
create or replace view api.current_rp2_contrasts as
select run_id, role, model_family, base_information_set, expanded_information_set,
       estimate, ci_low, ci_high, p_value, sessions, mde, equivalence_bound,
       block_length, common_mask_sha256
from public.rp2_contrast_results where is_current;
create or replace view api.current_rp2_extension_results as
select extension_id, run_id, question, result, document, artifact_sha256, created_at
from public.rp2_extension_results where is_current;
create or replace view api.current_rp2_power_results as
select contrast, role, run_id, method, detail, sessions_for_80pct, power_n30, power_n60,
       power_n120, note
from public.rp2_power_results where is_current;
grant select on api.current_rp2_block_results to anon, authenticated;
grant select on api.current_rp2_contrasts to anon, authenticated;
grant select on api.current_rp2_extension_results to anon, authenticated;
grant select on api.current_rp2_power_results to anon, authenticated;
insert into public.ingestion_runs (run_id, started_at, status, input_count, rows_published, note)
select 'rp2-legacy-unrecorded', now(), 'PUBLISHED', 0, 0,
       'Placeholder for RP2 blocks whose originating run was never recorded by the '
       || 'pre-RP2-v3 sync. Not a run: a named absence, so a block with a real artifact '
       || 'digest is not dropped from the versioned register for want of an attribution.'
where exists (select 1 from public.rp2_blocks b
              where b.artifact_sha256 ~ '^[0-9a-f]{64}$' and b.run_id is null)
   or exists (select 1 from public.rp2_extensions e where e.run_id is null)
   or exists (select 1 from public.rp2_power p where p.run_id is null)
on conflict (run_id) do nothing;
insert into public.rp2_block_results (
    block_id, run_id, status, verdict, document, artifact_sha256, supersedes_run_id, is_current)
select b.block_id, coalesce(b.run_id, 'rp2-legacy-unrecorded'), b.status, b.verdict,
       b.document, b.artifact_sha256, null, true
from public.rp2_blocks b
where b.artifact_sha256 ~ '^[0-9a-f]{64}$'
  and coalesce(b.run_id, 'rp2-legacy-unrecorded') in (select run_id from public.ingestion_runs)
on conflict (block_id, run_id) do nothing;
insert into public.rp2_extension_results (
    extension_id, run_id, question, result, evidence, document, artifact_sha256,
    supersedes_run_id, is_current)
select e.extension_id, coalesce(e.run_id, 'rp2-legacy-unrecorded'), e.question, e.result,
       e.evidence, e.document, null, null, true
from public.rp2_extensions e
where coalesce(e.run_id, 'rp2-legacy-unrecorded') in (select run_id from public.ingestion_runs)
on conflict (extension_id, run_id) do nothing;
insert into public.rp2_power_results (
    contrast, role, run_id, method, detail, sessions_for_80pct, power_n30, power_n60,
    power_n120, note, is_current)
select p.contrast, p.role, coalesce(p.run_id, 'rp2-legacy-unrecorded'), p.method, p.detail,
       p.sessions_for_80pct, p.power_n30, p.power_n60, p.power_n120, p.note, false
from public.rp2_power p
where coalesce(p.run_id, 'rp2-legacy-unrecorded') in (select run_id from public.ingestion_runs)
on conflict (contrast, role, detail, run_id) do nothing;
