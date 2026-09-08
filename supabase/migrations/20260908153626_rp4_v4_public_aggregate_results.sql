-- Reconstructed from the applied migration record; identity checked by contract.
-- ---- verbatim applied SQL follows ----
-- Public, saved aggregate results only. Existing tables, views and storage are unchanged.
create table public.rp4_v4_primary_statistics (
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  row_number integer not null check (row_number > 0),
  source_path text not null check (source_path = 'artifacts/rp4_v4_b4/primary_statistics.csv'),
  horizon_minutes integer not null check (horizon_minutes in (5,15,30)),
  result jsonb not null check (jsonb_typeof(result) = 'object'),
  primary key (source_sha256,row_number)
);
alter table public.rp4_v4_primary_statistics enable row level security;
revoke all on table public.rp4_v4_primary_statistics from public, anon, authenticated, service_role;
grant select on table public.rp4_v4_primary_statistics to anon, authenticated;
grant select, insert, update on table public.rp4_v4_primary_statistics to service_role;
create policy public_read on public.rp4_v4_primary_statistics for select to anon, authenticated using (true);
comment on table public.rp4_v4_primary_statistics is 'RP4 v4 public aggregates. Result JSON preserves exact CSV cell strings; no licensed per-origin observations.';

create table public.rp4_v4_coverage (
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  row_number integer not null check (row_number > 0),
  source_path text not null check (source_path = 'artifacts/rp4_v4_b4/coverage.csv'),
  horizon_minutes integer not null check (horizon_minutes in (5,15,30)),
  result jsonb not null check (jsonb_typeof(result) = 'object'),
  primary key (source_sha256,row_number)
);
alter table public.rp4_v4_coverage enable row level security;
revoke all on table public.rp4_v4_coverage from public, anon, authenticated, service_role;
grant select on table public.rp4_v4_coverage to anon, authenticated;
grant select, insert, update on table public.rp4_v4_coverage to service_role;
create policy public_read on public.rp4_v4_coverage for select to anon, authenticated using (true);
comment on table public.rp4_v4_coverage is 'RP4 v4 public aggregates. Result JSON preserves exact CSV cell strings; no licensed per-origin observations.';

create table public.rp4_v4_horizons (
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  row_number integer not null check (row_number > 0),
  source_path text not null check (source_path = 'artifacts/rp4_public_refresh/horizon_reference.csv'),
  horizon_minutes integer not null check (horizon_minutes in (5,15,30)),
  result jsonb not null check (jsonb_typeof(result) = 'object'),
  primary key (source_sha256,row_number)
);
alter table public.rp4_v4_horizons enable row level security;
revoke all on table public.rp4_v4_horizons from public, anon, authenticated, service_role;
grant select on table public.rp4_v4_horizons to anon, authenticated;
grant select, insert, update on table public.rp4_v4_horizons to service_role;
create policy public_read on public.rp4_v4_horizons for select to anon, authenticated using (true);
comment on table public.rp4_v4_horizons is 'RP4 v4 public aggregates. Result JSON preserves exact CSV cell strings; no licensed per-origin observations.';
