-- Applied to Supabase as migration 20260828020327 close_service_role_sensitive_mutation_paths.
-- Remote statements MD5: fb99bfba6d48f7e003483438e84e05f5.
-- Do not edit; corrections are new migrations.
-- ---- verbatim applied SQL follows ----
-- PENDING OWNER-APPLIED MIGRATION. Do not move into migrations/ until Supabase records it.
-- Fail closed for future public-schema objects created by the repository migration role,
-- and remove direct service-role mutation paths around retired RP2 results. Dataset DML
-- remains explicit because the hash-verified loader requires it for atomic promotion.
-- supabase_admin is intentionally absent: postgres cannot alter that platform superuser's
-- defaults; the ownership audit must continue to reject public objects owned by it.

alter default privileges for role postgres in schema public revoke all on tables from public, anon, authenticated, service_role;
alter default privileges for role postgres in schema public revoke all on sequences from public, anon, authenticated, service_role;
alter default privileges for role postgres in schema public revoke all on functions from public, anon, authenticated, service_role;

revoke insert, update, delete, truncate, references, trigger
on public.rp2_block_results,
   public.rp2_contrast_results,
   public.rp2_extension_results,
   public.rp2_power_results
from service_role;
