-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- Research Program v2 results catalogue. Aggregate statistics only: no origin-level
-- rows, no provider-derived values, nothing that the provider licence restricts.
create table if not exists public.rp2_blocks (
  block_id        text primary key,
  title           text not null,
  status          text not null,
  advance_rule    text not null,
  verdict         text not null,
  document        text not null,
  artifact_sha256 text
);
comment on table public.rp2_blocks is
  'Research Program v2: the eighteen-block cascade with each block''s advance rule and the verdict it actually returned. Aggregate only.';

create table if not exists public.rp2_power (
  id                bigint generated always as identity primary key,
  contrast          text not null,
  role              text not null,
  detail            text not null,
  sessions_for_80pct double precision,
  power_n30         double precision,
  power_n60         double precision,
  power_n120        double precision,
  note              text
);
comment on table public.rp2_power is
  'Prospective power for the variance and direction contrasts, sized on measured dispersion. Direction figures are an upper bound: the target was found by searching 36 candidates after the variance nulls were known.';

alter table public.rp2_blocks enable row level security;
alter table public.rp2_power  enable row level security;

insert into public.rp2_blocks (block_id, title, status, advance_rule, verdict, document) values
 ('01','Gate 0 - freeze D/V/C','COMPLETED','three temporally separated samples','PASS','docs/DISCOVERY_VALIDATION_CONFIRMATION_PROTOCOL.md'),
 ('02','Gate 1 - operational PIT truth','COMPLETED','empirical cutoff approved','PASS with amendment: 120 s replaces 60 s','docs/rp2/block2_pit_ledger_v1.md'),
 ('03','Gate 2 - validate the target','COMPLETED','one primary target frozen','PASS; RV60 escalated for signature','docs/rp2/block3_target_validation_v1.md'),
 ('04','Gate 3 - hard B0 baseline','COMPLETED','well-calibrated baseline','PASS with condition','docs/rp2/block4_b0_baseline_v1.md'),
 ('05','Gate 4 - B1 as a surface','COMPLETED','improvement in D/V or a clear mechanism','PASS on mechanism; two-family rule FAILS','docs/rp2/block5_b1_surface_v1.md'),
 ('06','Gate 5 - B2 microstructure','COMPLETED','target-blind features frozen','PASS','docs/rp2/block6_b2_microstructure_v1.md'),
 ('07','DML orthogonalization','COMPLETED','preliminary incremental evidence','PASS - joint Wald p = 3.0e-12','docs/rp2/block7_dml_v1.md'),
 ('08','Model ladder','COMPLETED','selection only in D/V','PASS procedurally, NULL substantively','docs/rp2/block8_ladder_v1.md'),
 ('09','Generalization','COMPLETED','no concentrated dependence','PASS in D, FAIL in V','docs/rp2/block9_generalization_v1.md'),
 ('10','Inference','COMPLETED','survives multiplicity','FAIL - best SPA p 0.0070 vs budget 0.00417','docs/rp2/block10_inference_v1.md'),
 ('11','Economics','COMPLETED','positive net value','FAIL - deflated Sharpe 0.000 when selective','docs/rp2/block11_economics_v1.md'),
 ('12','Prospective protocol','COMPLETED','binding result','NOT_RUN by design - 537 sessions needed','docs/rp2/block12_prospective_protocol_v1.md'),
 ('13','Cascade execution map','COMPLETED','-','map filled in with real verdicts','docs/rp2/block13_execution_map_v1.md'),
 ('14','Supabase evaluation','COMPLETED','-','2 fixes applied, 5 withheld for signature','docs/rp2/block14_supabase_v1.md'),
 ('15','Repository writing audit','COMPLETED','-','4 of 5 complaints already remediated','docs/rp2/blocks15_18_publication_pass_v1.md'),
 ('16','Professional structure','COMPLETED','-','reading layer proposed, not a bulk move','docs/rp2/blocks15_18_publication_pass_v1.md'),
 ('17','README opening','COMPLETED','-','implemented','docs/rp2/blocks15_18_publication_pass_v1.md'),
 ('18','Keep / move','COMPLETED','-','already satisfied for the README','docs/rp2/blocks15_18_publication_pass_v1.md')
on conflict (block_id) do update set
  status = excluded.status, verdict = excluded.verdict, document = excluded.document;

insert into public.rp2_power (contrast, role, detail, sessions_for_80pct, power_n30, power_n60, power_n120, note) values
 ('direction','V','signed_return_120 via strike_hhi', 42,   0.614, 0.942, 1.000, 'upper bound: target found by searching 36 candidates post hoc'),
 ('direction','V','signed_return_60 via strike_hhi',  44,   0.577, 0.925, 0.999, 'upper bound: target found by searching 36 candidates post hoc'),
 ('direction','D','signed_return_120 via premium',   267,   0.057, 0.141, 0.359, 'upper bound: target found by searching 36 candidates post hoc'),
 ('variance','D','lightgbm delta_B2_given_B1',       537,   0.026, 0.056, 0.139, 'measured QLIKE dispersion'),
 ('variance','D','gamma_glm delta_B1',              3209,   0.007, 0.010, 0.018, 'measured QLIKE dispersion'),
 ('variance','V','gamma_glm delta_B2_given_B1',    14753,   0.004, 0.005, 0.007, 'measured QLIKE dispersion');
