# RP3 preregistration

This document is sealed by SHA-256 before 2026-08-29, before the evaluation
window exists in full, and before any model in the program has been trained.
Everything the program is allowed to do is written here; anything not written
here is not part of the program.

- Preregistration status: SEALED (hash recorded at seal time in the RP3 seal
  manifest)
- Frozen B2 index hash: `d3140451976ffb485a68c42ff109fcb8c5a434c810fed24055bf929ce09365b6`
- Primary read size: 662 evaluable sessions
- Estimated read date: 2029-01-30
- Confirmatory reads so far: 0

## 1. Purpose and provenance

RP3 is a prospective, registered-report-style confirmation program. It takes
the one forecasting cell that cleared the RP2-v3 sequential alpha budget —
trade flow (B2), compressed to a single frozen linear index, improving
30-minute realized-variance forecasts beyond the option-surface set (B1) in
the LightGBM/QLIKE family, DeltaB2|B1 = +0.00101 in development — and asks
whether it replicates on market sessions that did not exist when the design
was frozen. RP2-v3 itself is not touched: its thesis, its frozen artifacts, and
its sealed cohorts stay exactly as published, and RP3 neither reopens nor
reinterprets them.

Full disclosure of how the hypotheses were selected, because the selection is
the program's largest liability:

- **The target came out of a 36-target exploratory sweep.** The frozen
  extension-1 artifact `artifacts/rp2_ext1_mechanism_utility/mechanism_utility.json`
  (dated, committed before this document) examined 36 targets. In it,
  `y_rv_60` is the only realized-variance target alive in both roles
  (D p = 2.0e-08, V p = 0.0044); `y_rv_5` dies in validation (V p = 0.33);
  `y_signed_return_120` shows V p = 1.3e-06. RV60 and the 120-minute
  direction target were chosen *because* they looked best in that sweep.
  Thirty-six targets were looked at; the multiplicity is declared here, not
  hidden.
- **The B2 index came out of an exploratory autopsy.** Run in role D only,
  on the same mask and the same 60/40 split as block 10 of the
  `rp2-v3-20260824-remeasure` run, the autopsy established that a single
  linear index over the B2 features reproduces the tree-ensemble increment
  (+0.00101 QLIKE, bootstrap CI [+0.00032, +0.00176], p = 0.0010, against
  +0.00108 published for the full feature set), that Gamma GLMs do not change
  when given the one extra parameter (the information is structurally
  redundant with what GLMs already extract), that a tree-fitted index is
  *negative* out-of-fold in all three model families (instant overfitting —
  which is why the index is linear), and that the benefit concentrates
  roughly 5x in the highest-flow quintile (+0.00286 vs +0.00054 in the rest;
  Spearman rho = +0.111 between flow volume and per-session benefit).
- **The RV60 candidate was measured dead before sealing.** The sweep's
  preferred target was RV60, and the sizing measurement killed it: through
  the same frozen index, the development effect on `rv_60` is **-0.000431**
  (bootstrap p = 0.395), measured on the target-panel origin grid and
  recorded permanently in `artifacts/rp3/sizing.json` under
  `measurements.rv_60`. The information tests that made RV60 look alive do
  not convert into forecast improvement — the same lesson RP2-v3 taught at 30
  minutes, repeating at 60. The primary is therefore not the sweep's winner
  but the replication of the already-budget-cleared rv_30 cell, measured on
  the same evaluation universe it was published on (the block-10 common mask;
  on the restricted target-panel grid the same contrast reads -0.000177,
  because that grid drops the early- and late-session origins where the index
  earns its keep — both universes are recorded in the sizing artifact).
- **Winner's curse is priced in, not argued away.** Because both hypotheses
  were selected as the winners of an exploratory search, their observed
  effects are upward-biased estimates of the true effects. All sample-size
  planning in this document divides the observed effect by 2 before sizing.
  The frozen power artifact says the same thing about itself: its direction
  power figure "is an upper bound on what a pre-registered test would
  achieve, not an unbiased estimate."

## 2. Hypotheses

The list is closed. Two hypotheses enter the program; nothing else does, and
nothing may be added, substituted, or re-scoped after sealing.

- **H1 (primary).** On the evaluation window, DeltaB2|B1 > 0 for 30-minute
  realized variance (RV30) in the `lightgbm_qlike` family, where B2 enters as
  the single frozen linear index whose coefficients live in
  `artifacts/rp3/b2_index_theta.json` (SHA-256 `d3140451976ffb485a68c42ff109fcb8c5a434c810fed24055bf929ce09365b6`). This is
  the prospective replication of the one development cell that cleared the
  RP2-v3 sequential budget (+0.00101, p = 0.0010, 156 development sessions).
  The test is the paired QLIKE contrast between the frozen B1 model and the
  frozen B1-plus-index model, one-sided in favor of the index, scored on
  every common-mask origin — the same evaluation universe the development
  cell was published on, stated here because the restricted target-panel
  grid measures the same contrast negative and a primary scored there would
  be a different experiment wearing the same name.
- **H2 (secondary).** On the evaluation window, the frozen B2 index carries
  directional information about the 120-minute signed return
  (`signed_return_120`). The frozen power artifact
  (`artifacts/rp2_ext4_power/power.json`) measured
  `sessions_for_80pct` = 42 for this direction contrast at the observed
  effect; applying the same effect/2 shrinkage quadruples the requirement to
  approximately 168 nominal sessions. Because the single read happens at
  662 sessions, the bank exceeds that requirement severalfold by
  read time; H2 is nevertheless registered as secondary and is tested only
  under the gatekeeping order of section 5 — it is not a second chance for
  the program to succeed.

## 3. Evaluation window

The evaluation window is every session strictly on or after **2026-07-18**.
The RP2-v3 validation role (V) ends on 2026-07-17, and no decision in this
program — target choice, index construction, family choice, test list,
sample-size plan — has seen any session past that date. Most of the window
does not exist yet at seal time, which is the strongest form of that
guarantee. The Phase B guardian asserts the boundary mechanically: it refuses
to train or freeze any model whose input data extends past 2026-07-17, and it
refuses to score any session on or before that date as evaluation.

## 4. Frozen design

- **Models are trained once.** In Phase B, the B1 model and the
  B1-plus-index model are trained on data through 2026-07-17 only, then
  serialized, and each serialized model's SHA-256 is recorded in the Phase B
  freeze manifest. After that point no re-training, re-tuning, or
  re-selection of any kind occurs.
- **The index is already frozen.** The B2 index coefficients (theta) are
  fixed in `artifacts/rp3/b2_index_theta.json`, hash `d3140451976ffb485a68c42ff109fcb8c5a434c810fed24055bf929ce09365b6`,
  referenced by this sealed document. The design has 15 columns — the 12
  registered B2 features plus the 3 train-absence indicators the fold
  preprocessor emits — because that is the exact design the index was fitted
  on; freezing only the 12 named features would be a different, never-fitted
  index. The index is a deterministic linear
  function of the frozen B2 features; nothing about it can adapt to
  evaluation data.
- **Every new session is an evaluation session.** Sessions arriving after
  2026-07-17 are scored by the frozen models and appended to the evaluation
  bank. None of them is ever used for training, calibration, or any other
  form of adaptation.

## 5. Look policy

- **One read.** The confirmatory statistics are computed exactly once, when
  the evaluation bank reaches **662** evaluable sessions (estimated
  date: **2029-01-30**). Before that point, no one computes, previews, or
  partially aggregates the confirmatory contrasts.
- **Look counter with tripwire.** The program maintains a machine-checked
  counter of confirmatory reads. Its only legal trajectory is 0 until the
  read, then 1. Any value other than those, at any time, invalidates the
  confirmatory claim of this preregistration; the tripwire converts a
  violated look policy into a recorded fact rather than a private one.
- **Alpha.** The program-wise alpha is 0.05, controlled by the
  fixed-sequence (gatekeeping) procedure: H1 is tested at the full 0.05, and
  H2 is tested at 0.05 only if H1 rejects. This controls the family-wise
  error rate at 0.05 exactly, respects the primary/secondary ordering
  declared above, and matches the sizing artifact, whose N_PRIMARY was
  computed at alpha = 0.05.
- **The result is published either way.** This document commits the program
  to registered-report logic: the read's outcome — positive, null, or
  negative — is published with the same prominence and the same artifacts. A
  null here is informative precisely because the design was sealed first.

## 6. What this preregistration cannot prevent

Preregistration removes analytic flexibility. It does not remove these three
risks, so each is declared with its consequence:

- **Additional shrinkage beyond effect/2.** The /2 winner's-curse correction
  is a convention, not a measurement; the true post-selection effect may be
  smaller still. Consequence: the program may be underpowered even for H1
  despite honest sizing, and a null read must be reported as "not detected at
  this power," never converted into evidence of absence.
- **Market regime change.** The evaluation window is later in time than
  every observation the design has seen, and the flow-concentration
  structure the index exploits may not persist. Consequence: a null or
  negative read cannot distinguish "the effect was never real" from "the
  effect did not survive the regime"; the program accepts that ambiguity
  rather than granting itself a post-hoc regime exclusion.
- **The index may have frozen noise.** The linear index was fitted on
  development data, and freezing it preserves whatever part of it is noise as
  faithfully as whatever part is signal. Consequence: H1 tests the frozen
  index as-is; a failure of the index is a failure of the hypothesis, and no
  re-fitted or repaired index may be substituted after the fact.
