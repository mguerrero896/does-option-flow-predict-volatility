-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- Extensions 1-4: what was tried after the eighteen-block cascade closed.
-- Aggregate verdicts only, no origin-level rows.
create table if not exists public.rp2_extensions (
  extension_id text primary key,
  question     text not null,
  result       text not null,
  evidence     text not null,
  document     text not null
);
comment on table public.rp2_extensions is
  'Research Program v2 extensions. Three asked whether the null was an artefact of the programme''s own choices (it was not); the fourth found the signed forward return, which is the only target surviving Holm in validation.';

alter table public.rp2_extensions enable row level security;

insert into public.rp2_extensions (extension_id, question, result, evidence, document) values
 ('ext1a','Can the mechanism flag a variance-tail regime?','NEGATIVE',
  'AUC D 0.8875 -> 0.8875; V 0.8659 -> 0.8627 (worse)','docs/rp2/extensions_1_4_v1.md'),
 ('ext1b','Can it rank origins for execution timing?','NEGATIVE',
  'Spearman D 0.8533 -> 0.8535; V 0.7877 -> 0.7870','docs/rp2/extensions_1_4_v1.md'),
 ('ext1c','Does it speak to a target other than RV30 level?','POSITIVE',
  'signed forward return 60-120 min: only 3 of 36 targets survive Holm in V, two are this; V p=1.26e-06 Holm 0.0000; strike concentration + / total premium - with consistent signs in both universes; UPPER BOUND, target found by post-hoc search',
  'docs/rp2/extensions_1_4_v1.md'),
 ('ext2','Does the moneyness x DTE tensor recover the signal?','NEGATIVE',
  'D 0.13742 -> 0.13912 (worse, p=0.057); V 0.21331 -> 0.21168 (ns, p=0.477)','docs/rp2/extensions_1_4_v1.md'),
 ('ext1_level4','Do level-4 sequence models over the raw tape recover it?','NEGATIVE',
  'DeepSets vs LightGBM: D 0.1496 vs 0.1374 (-0.0122 worse); V 0.2107 vs 0.2133 (+0.0027). The +0.63 headline against the MLP control is not reported: the MLP is a weak control, and QLIKE amplifies a 9-30% log-RMSE gap into a 4x gap',
  'docs/rp2/extensions_1_4_v1.md'),
 ('ext3','Can the panel be widened?','DONE',
  '153 sessions acquired, 906 FMP requests, zero empty; Discovery 236 -> 384 sessions, panel 125,136 -> 183,744 origins',
  'docs/rp2/extensions_1_4_v1.md'),
 ('ext4','Where is a one-read cohort worth spending?','DIRECTION, NOT VARIANCE',
  'direction 42 sessions for 80% power vs variance 537 - a 13x difference. Phase 8 cannot be re-aimed: its protocol is hash-frozen for variance and re-aiming would break the seal',
  'docs/rp2/extensions_1_4_v1.md')
on conflict (extension_id) do update set
  result = excluded.result, evidence = excluded.evidence;
