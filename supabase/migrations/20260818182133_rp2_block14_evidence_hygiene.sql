-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- Research Program v2, Block 14. Two corrections only, both reversible.
--
-- 1. The C6-specific sign-convention note had been copied onto every campaign row,
--    which is the "repeated evidence chain" defect the program names. It is true of
--    C6 and false of C1, C2, C4c and C5. Removing a false statement is the honest fix;
--    inventing per-campaign notes would not be.
update public.campaigns
set note = null
where campaign_id <> 'C6_b1v3_confirmation'
  and note like 'C6 chain lists%';

-- 2. p_wild is NULL in all 36 contrast rows. The program forbids an ambiguous NULL:
--    it must be synchronised or explicitly labelled. It is labelled here, not invented.
alter table public.contrast_results
  add column if not exists p_wild_status text not null default 'NOT_SYNCED';

alter table public.contrast_results
  drop constraint if exists contrast_results_p_wild_status_check;

alter table public.contrast_results
  add constraint contrast_results_p_wild_status_check
  check (p_wild_status in ('SYNCED', 'NOT_SYNCED', 'NOT_APPLICABLE', 'AVAILABLE_IN_ARTIFACT_ONLY'));

update public.contrast_results
set p_wild_status = case when p_wild is null then 'AVAILABLE_IN_ARTIFACT_ONLY' else 'SYNCED' end;

comment on column public.contrast_results.p_wild_status is
  'Sync state of p_wild against artifacts/gate1_inference/results.json. AVAILABLE_IN_ARTIFACT_ONLY means the wild-bootstrap p-value exists in the frozen artifact but was never loaded here; never read a NULL p_wild as "not computed".';
