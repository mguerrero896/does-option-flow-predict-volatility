-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- MDS650 research catalog: frozen-campaign aggregates + gated-data registry.
-- Private research DB: RLS enabled with NO policies -> anon/authenticated see
-- nothing; access is service-role only (owner + agents).

create table public.campaigns (
  campaign_id text primary key,
  sessions integer,
  row_count bigint,
  input_sha256 text not null,
  note text
);
comment on table public.campaigns is
  'Frozen evaluation campaigns (C1-C6) as re-analyzed by Gate 1 studentized inference.';

create table public.contrast_results (
  id bigint generated always as identity primary key,
  campaign_id text not null references public.campaigns,
  block_id text not null,
  model_role text not null,
  contrast text not null,
  estimate double precision,
  cluster_t double precision,
  p_cluster double precision,
  p_newey_west double precision,
  p_wild double precision,
  rho1 double precision,
  ljung_box_p double precision,
  unique (campaign_id, block_id, model_role, contrast)
);
comment on table public.contrast_results is
  'Studentized per-contrast statistics from artifacts/gate1_inference/results.json (aggregates only, no provider values).';

create table public.mcs_cells (
  id bigint generated always as identity primary key,
  campaign_id text not null,
  block_id text not null,
  block_length integer not null,
  cell text not null,
  mcs_p double precision,
  survivor boolean not null,
  unique (campaign_id, block_id, block_length, cell)
);
comment on table public.mcs_cells is
  'Model Confidence Set membership per campaign/block/bootstrap block length L (L=0 is the IID legacy baseline), from artifacts/mcs_block_sensitivity/results.json.';

create table public.gated_files (
  path text primary key,
  sha256 text not null,
  bytes bigint not null,
  bucket_object text not null unique
);
comment on table public.gated_files is
  'Registry of licensed-derived datasets held in the private research-data Storage bucket; mirrors data/GATED_DATA_POINTERS.json.';

create table public.access_grants (
  id bigint generated always as identity primary key,
  granted_at timestamptz not null default now(),
  grantee text not null,
  purpose text not null,
  bucket_object text not null references public.gated_files (bucket_object),
  expires_at timestamptz,
  note text
);
comment on table public.access_grants is
  'Log of per-request signed-URL grants from the gated bucket (docs/provider_license_review_v1.md discipline).';

create index on public.contrast_results (campaign_id);
create index on public.mcs_cells (campaign_id, block_id);
create index on public.access_grants (bucket_object);

alter table public.campaigns enable row level security;
alter table public.contrast_results enable row level security;
alter table public.mcs_cells enable row level security;
alter table public.gated_files enable row level security;
alter table public.access_grants enable row level security;
