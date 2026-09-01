# Point-in-time options information for forecasting next-30-minute realised variance

**Capstone report — scientific-result cutoff 2026-08-31; timing amendment 2026-09-01**

> Status: `EVIDENCE_CUTOFF_COMPLETE`. Supersedes the v1 skeleton. Phase 8 and Phase 9 are
> reported at their actual evidence-cutoff status rather than left as result placeholders.
> All claims are bounded by decision 53;
> exploratory findings carry their labels and the `positive_findings_v1.md` citation
> rule. Numbers are drawn only from the frozen artifacts cited in each section.
>
> **Evidence status (2026-08-31).** The current reproducible bundle is
> `rp2-v3-20260831-b1-spot-cutoff-remediation` (scientific hash
> `033f2eb6be35e5db...`). It repairs partition-role assignment, aligns B0 with the
> documented 120-second B1/B2 cutoff, gives B1 the same XNYS expiry calendar as B2,
> and makes B1's underlying spot obey its own option-quote cutoff.
> It remains a historical D/V measurement because `PIT_V22_RECONCILIATION_BLOCKED` is
> active. No number in this report is an eligible current headline; `STATUS.md` and
> `docs/rp2_v3/VERDICT.md` govern if a dated narrative disagrees.
>
> **Methodological timing amendment (2026-09-01).** The predictive-result cutoff above
> is unchanged. A later target-blind UW receipt-latency snapshot is included only to
> correct the operational-availability limitation in §§3, 7 and 8. It changes no panel,
> mask, estimate, interval or verdict and reads no sealed outcome cohort.

## Title page

**Title:** Point-in-time options information for forecasting next-30-minute realised variance

**Author:** Miguel Guerrero Quijano

**Course:** MDS650 Capstone Research Project

**Document:** Capstone report, evidence-cutoff version

**Evidence cutoff:** 31 August 2026 (Australia/Sydney)

**Methodological timing amendment:** 1 September 2026 (target-blind; no result re-evaluation)

## Abstract

This project asks whether option-market information improves out-of-sample prediction of
the next thirty minutes of realised variance (RV30) for six large US equities. At
five-minute New York-session origins it compares three nested information sets on
identical rows: underlying and market state (B0), option-surface state (B1), and
point-in-time option-trade flow (B2). The current corrected-protocol run measures 389
discovery sessions and 80 later validation sessions with three model families and QLIKE.
It is retrospective and exploratory: validation was used adaptively during development,
and the stricter sequential alpha is a conservative post-hoc sensitivity rather than a
preregistered confirmation. The decision-relevant B2 result is negative. The registered
directional rule returns `DO_NOT_PURSUE`; the same-30-session Phase 8 remediation places
the positive contribution in the B1 option-state block while every ΔB2|B1 interval crosses
zero. It improves information-clock validity rather than absolute forecast score: only one
of eight B1-inclusive primary cells lowers paired QLIKE after correction. In the retrospective run,
discovery ΔB1 is positive in all three families, validation does not establish replication,
and ΔB2|B1 changes sign by family and partition. Ten of twelve contrasts are below their
own minimum detectable effect. Provider source-time and record-creation rules prevent
look-ahead under documented assumptions, but they do not prove historical client receipt
time. A five-clean-session receipt audit found 6/406 (1.48 per cent) opening receipts
beyond 60 seconds and none beyond 120 seconds, so the 60-second UW proxy is not a strict
conservative opening bound in this sample; PIT v2.2 reconciliation therefore remains
blocked. Phase 8 consumed its sole
exploratory read and is `MIXED_EXPLORATORY`; an append-only post-hoc reconstruction uses
only those already materialized sessions and does not create a second read. Phase 9 is an ongoing 60-session prospective
follow-up, not a submission gate. No causal, confirmatory or profitability claim is made;
the current read counters are Phase 8 = 1 and Phase 9 = 0.

## 1. Introduction

Short-horizon realised-variance forecasting sits at the intersection of two mature
literatures: autoregressive realised-variance modelling, in which heterogeneous lag
structures (HAR-type models) set a demanding baseline, and options-based volatility
forecasting, in which option prices are treated as forward-looking information. Between
them lies a specific and under-tested question: does option-trade *activity* — what was
just traded, over and above what option *prices* already say — add incremental
predictive information at intraday horizons, when the forecaster is restricted to
information that was operationally available at the moment of the forecast?

That restriction is the heart of this project. Existing evidence on options-based
volatility prediction is largely silent about operational availability: whether the
researcher's data existed, in the form used, at the moment the forecast pretends to have
been made. Activity-based predictors are especially exposed to that silence, because the
trade tape that carries them is a vendor product with its own publication delay, and a
forecast built from a record that arrived after its own origin is not a forecast. This
project therefore builds a source-time PIT panel from three commercial providers under
documented availability rules and fail-closed exclusions. The D/V analyses are
retrospective and exploratory; only separately frozen prospective protocols can support
one-read claims. A vendor source timestamp or `created_at` field is not relabelled as proof
of historical client receipt.

The research question is strictly predictive-informational: does an expanded option-
information set reduce out-of-sample QLIKE loss for the realised variance of the next
thirty minutes (RV30) on identical forecast origins? Three nested information sets are
compared over the same origins, on a five-minute grid inside the regular session:
underlying and market state (B0); B0 plus contemporaneous option-surface state (B1); and
B1 plus point-in-time option-trade flow (B2). Two estimands follow — the option-state
increment ΔB1, defined as the QLIKE of B0 minus the QLIKE of B1, and the conditional
activity increment ΔB2|B1, defined analogously. Both are estimated for three
fixed model families: a regularised gamma GLM, a ridge regression in logs, and a
gradient-boosted challenger trained on the QLIKE objective. Inference is made at the
level of the trading session through a circular block bootstrap, so the unit of
uncertainty is the day, not the origin. The roles of the sample are separated by time
and do not overlap: discovery covers 389 sessions (2024-08-02 to 2026-03-23) and
validation 80 (2026-03-24 to 2026-07-17), over six outcome equities on a single exchange
calendar. No claim about direction, trader intent, causality or profitability is in
scope.

Four contributions remain after those limits are imposed. First, the project implements a
nested intraday design whose rows, splits and session-level uncertainty are auditable.
Second, it measures how the option-state increment changes after conditioning on lagged
intraday realised variance, without promoting the exploratory D/V result. Third, every
increment is reported beside its minimum detectable effect, separating absence of evidence
from evidence of absence. Fourth, it supplies fail-closed source-time PIT machinery,
access-ledgered sealed cohorts and reproducible paired-session inference. The empirical arc
is correspondingly bounded: discovery ΔB1 is positive, validation does not confirm it,
ΔB2|B1 is family- and partition-dependent, and the current bundle cannot be reconciled
into an eligible headline until PIT v2.2 clears.

## 2. Literature review

The literature boundary is the checked-in evidence ledger. Full-text, abstract-only and
metadata-only sources are used only at their recorded claim strength.

Four strands of prior work frame this design, and each made a prediction that the data
could have contradicted. Citation discipline is deliberately narrow: only sources
verified in the project's evidence ledger (`docs/literature_evidence_ledger_v2.csv`) are
cited, and each is used only at the strength the ledger records for it, so that a
reference retained as an abstract is never asked to carry a numeric claim.

The first strand is the heterogeneous-autoregressive tradition following Corsi (2009),
which models realised variance through a cascade of multi-horizon components. The ledger
retains the fully verified 2004 working-paper predecessor as the method reading copy; no
published-version page locator is asserted. Its prediction here
is procedural: a candidate predictor must beat a heterogeneous autoregressive baseline,
not merely a naive one. Recent evaluations sharpen the demand. Puke and Schweikert
(2026) show that HAR-type specifications remain the reference under QLIKE and MSE across
horizons, sampling frequencies and rolling-window lengths, and Kiliç (2025) reports that
threshold and smooth-transition variants outperform machine-learning alternatives when
the predictor set is limited. This project's results agree with the strand. Once the
field-standard baselines were added to the ladder, the HARQ implementation became the
strongest baseline available, and the option-activity block added a null-to-negative
increment on top of HAR and HARQ (§5.4). The default of the field explains these data;
the candidate predictor does not improve on it.

The second strand is the implied-volatility informativeness literature. The
ledger-verified anchor used here is the modern machine-learning study by Michael, Cucuringu
and Howison (2025), who report that option-surface and model-derived features lift
selected specifications and that their gradient-boosted challenger beats the baseline in
76 percent of reported QLIKE cases. The prediction for this project is direct: the B1
information set should reduce loss relative to B0. What the data return is a two-part
answer that neither confirms nor refutes it. On the discovery role the option-state
increment is positive under all three fixed families. On the validation role, separated
from discovery by time but used adaptively during model and reporting development, no
family establishes a confirmatory result and the point estimates do not agree in sign
(§5.1). Design analysis removes the temptation to read that as a
refutation: no family was powered in validation against effects of the size discovery
reported (§5.1). The honest reconciliation is a scope statement, not a verdict. The
strand's evidence is rarely conditioned on rich lagged intraday realised variance and is
gathered predominantly at a daily horizon or longer; at thirty minutes, with those
controls in place and with inference at the session level, this study could not
reproduce the gain seen at discovery and could not have detected it either.

The third strand is the options-activity and informed-trading literature, which motivates
B2 without licensing a claim about trader intent. The ledger's anchor for the modern
decomposition of informed option trading is
Asencio, Bernales, González, Holowczak and Verousis (2026), and the ledger is explicit
about its limits: it estimates informed-trading components rather than forecasting
realised variance, and it must never be used to infer trader intent from this project's
vendor labels. Read as a motivating prior rather than a benchmark, it asks whether recent
activity adds predictive information beyond option state. The measured increments are
small and mixed across families and partitions (§5.1), so they do not establish a
universal activity contribution.

The fourth strand is the loss-function literature. The retained full text of Patton
(2011) supports QLIKE and MSE as robust variance-forecast comparison losses under imperfect
volatility proxies. In this project QLIKE also exposes conditional-mean calibration: a
feature that repairs a biased forecast can improve the score without identifying a new
market mechanism. That is precisely the failure
mode the design must guard against. Disagreement between model families is not an
anomaly to be explained away but an anticipated consequence of comparing a miscalibrated
family with a calibrated one under a calibration-sensitive loss, and the project measures
the channel directly by re-scoring out-of-evaluation Mincer-Zarnowitz recalibrated
forecasts (§5.3). Patton (2011) is the reason this report never pools families into a
single verdict and never treats one family's increment as the study's answer.

A fifth, weaker body of work supplies comparative context. At metadata/abstract strength
only, Díaz, Hansen and Cabrera (2024) report horizon-dependent ML-versus-HAR results and
Li, Xie, Wang, Zhu, Zeng and Gong (2024) report non-uniform gains from shrinkage HAR.
Neither source is used for an exact table or numerical claim. Caporin, Di Fonzo and
Girolimetto (2024), Zhang, Song, Peng
and Wang (2024) and Omer, Månsson, Sjölander and Uddin (2026) each obtain gains from
richer intraday structure, jump-aware deep learning, and regularisation and tree
methods, but none targets a thirty-minute equity horizon with option data and one is a
commodity study; they position this work rather than transfer to it.

The gap follows from the strands rather than from a claim of novelty. None of the
ledger-verified sources evaluates option-trade activity at an intraday horizon under
explicit operational-availability rules, with information sets nested on identical
forecast origins, and none reports the sample size at which its own null would have been
detectable. The design consequence is that the quantity treated as central here is not a
p-value but a minimum detectable effect, and that the strands above are answered with
stated precision. The sealed prospective campaigns remain future evidence rather than
being narrated as if their outcome were already known.

## 3. Data and point-in-time discipline

Three commercial providers feed the panel. FMP supplies the one-minute underlying bars from
which both the target and the lagged realised-variance features are built; Massive, a
Polygon-compatible service, supplies the independent observations against which those bars
and the option surface are audited; Unusual Whales supplies the option-trade tape,
1,461,521,313 rows across the 469 sessions of the study window, streamed in full rather than
sampled. Raw licensed data live outside the repository; the committed evidence is code,
schemas, preregistration manifests, SHA-256 hashes for every derived panel, access ledgers
and aggregate artifacts — auditability rather than redistribution.

The target is unannualised RV30: the sum of thirty squared one-minute log returns from
thirty-one consecutive closes following each forecast origin. Origins lie on a five-minute
grid from session minute 30 to 355 of the regular XNYS session, sixty-six per session-asset.
The outcome universe is six liquid mega-cap equities (AAPL, AMZN, META, MSFT, NVDA, TSLA),
with SPY and QQQ entering only as market controls — a deliberate, stated scope limitation
(§7). The assembled panel holds 181,829 origins over 2,814 session-assets, none dropped for
a sparse minute grid. One property of the target matters before any model does: its relative
standard error at this horizon has a median of 25.6 per cent in discovery, so roughly a
quarter of what is being predicted is the estimator's own sampling error.

Both option blocks are defined by availability, not by convenience. B1 is a contemporaneous
option-state snapshot: the last observation of every contract timestamped at or before the
origin minus 120 seconds and no older than thirty minutes, from which implied variance at
fixed maturities, term and smile shape, a 25-delta risk reversal and quote-quality fields
are computed. Coverage of the ten B1-core features is 99.3 per cent and the average snapshot
carries 779 contracts. B2 adds the point-in-time trade tape under the same cutoff, and the
panel records zero availability violations. Because the surface is reconstructed from the
quotes carried on trades, a contract enters only if somebody traded it; that selection was
measured rather than assumed: against a directly quoted chain the traded surface understates
put skew by 46 per cent, while its at-the-money level — the feature the later blocks consume
— is essentially unbiased.

The availability evidence is asymmetric. The bar-label audit supports the project's
conservative FMP `+1 minute` rule (with `+2 minutes` sensitivity) and Massive SIP as-of
selection. For the trade tape, Unusual Whales `created_at` remains `PROXY_ONLY`: it is a
record-creation timestamp, not provider-proven publication time or historical client
receipt. PIT v2.2 therefore excludes 451 of 77,328 predictor rows rather than recoding
delayed records as zero activity, and it keeps
`SAFE_TO_RECONCILE_EXISTING_RESULTS=NO`. The timing machinery prevents source-time
look-ahead under its documented assumptions; it does not establish a universal provider-
latency claim.

A target-blind live receipt audit dated 2026-09-01 tests that operational assumption
without changing the historical panel. Its measured result and sample boundary are
reported separately in §5.6. It leaves `created_at` as `PROXY_ONLY`, preserves
`PIT_V22_RECONCILIATION_BLOCKED`, and does not re-score any forecast.

Discipline also means repairing data rather than smoothing over it. Two discovery bar
stores carried only closes, and the session grid had reconstructed the absent range and
volume from the close and from zero, fabricating three features on 22,967 of 152,954
discovery origins and on none of the validation origins. The fix was re-acquisition, not
imputation; minutes whose recorded zero volume their own price range contradicts are now
carried as missing.

The evaluation design separates roles by time, and the separation is exact. Discovery (D)
runs from 2024-08-02 to 2026-03-23, 389 sessions and 152,954 origins; validation (V) runs
from 2026-03-24 to 2026-07-17, 80 sessions and 31,678 origins. The two universes share
assets, calendar and feature recipe, and no calendar day belongs to both: D ends the session
before V begins, and the partition was frozen by content hash before these analyses ran.
Within each universe models are fitted on the chronologically first sixty per cent of
sessions and evaluated on the rest, so the inference unit is 156 evaluated sessions in D and
32 in V — a property of the sample, not of the estimator, and one that §5 and §7 return to.
D spans a wide range of market conditions, including the August 2024 volatility shock, in
whose window the VIX reached 38.6, and the November 2024 election week; the stretch of V
from 2026-05-20 to 2026-07-17 is unremarkable by comparison, with a VIX median of 16.7. The
eras also differ in difficulty: the same three-term price-history regression attains an
out-of-sample log R² of 0.796 in D and 0.553 in V, so the underlying itself became less
forecastable, and any comparison of effect sizes across the two must carry that. Those two
figures are carried over from the superseded RP2-v2 cascade and are not reproducible from
any artifact in this release; the difficulty gap they illustrate is qualitative here. A third
cohort, sealed and prospective, is recorded by protocol reference only; it is never
enumerated, sampled or read here. Its exploratory bridge is described separately in §5.2
without inventing an outcome.

## 4. Methodology

### 4.1 Nested information sets on identical origins

The three information sets introduced in §1 are strictly nested — B0, then B0+B1 adding the
contemporaneous option-state snapshot, then B0+B1+B2 adding point-in-time option-flow
activity — and each larger set is the smaller one plus a feature block, scored on the same
origins. Every contrast is therefore a paired difference of losses in which asset mix,
session mix and market regime cancel by construction, and only the information differs.

Comparisons are also family-matched: a model family is compared against itself across
information sets, never against another family (`docs/rp2_v3/RESEARCH_CONTRACT.md`). Three
families were frozen before any delta existed — a Gamma GLM with log link (`gamma_glm`), a
ridge regression on the log target (`ridge_log`) and a gradient-boosted tree fitted
directly to QLIKE (`lightgbm_qlike`) — and the producer refuses to write a result artifact
omitting one of them. The other ladder families are robustness only, and the log-MSE and
QLIKE trees count as one family rather than two pieces of evidence; HAR and HARQ are
external baselines, not deciding families (§5.4).

Each nested pair is evaluated on exactly one common row mask — valid target, keys and
availability — recorded by SHA-256 with the contrast, so a base model is never scored on
rows the expanded model dropped and an apparent improvement can never be an easier sample.
Discovery and validation are separated by time rather than at random; the partition and
the evaluated-session counts are given in §3.

### 4.2 The loss, and why it was frozen

QLIKE is the primary loss, frozen in the research contract together with the target, the
comparison direction and the inference unit before any code moved. It suits a strictly
positive conditional-mean variance target; it is robust to noise in the variance proxy,
which matters at a horizon where the proxy is itself an estimate (§3); and it penalises
calibration error, a property that is substantive here rather than decorative, since
features that repair a biased baseline can masquerade as information under it (Patton
2011; §5.3). Freezing it matters procedurally as much as statistically: a loss chosen
after the deltas exist tests nothing. The nonlinear family was aligned to it, so that what
it optimises and what it is judged on coincide.

The sign convention was fixed in the same document — `delta_B1 = L(B0) − L(B0+B1)`,
`delta_B2|B1 = L(B0+B1) − L(B0+B1+B2)`, positive favouring the larger set — together with
the rule that governs this report: a null or negative delta is reported as measured, and
no family, feature, horizon or threshold may be added to move a delta toward the expected
sign.

### 4.3 Preregistration and one-read gates

Every campaign froze its question, estimands, universe, session lists, models and stop
rules in hash-sealed manifests before any outcome was read. The B1v3 preregistration
(`docs/b1v3_preregistration.md`, SHA-256 `e538ad00…`) lists its sixty development and
thirty confirmation sessions by date, declares the primary contrasts and both model
specifications, carries an evaluation flag and a read counter, and retains positive, null
and negative signs alike. The successor method freeze
(`docs/confirmation_protocol_v4_sourcebound.md`) is target-blind by construction: it
authorises no model fit, no metric evaluation and no holdout access, and it prohibits
selection by sign and the choice of features, assets, models or the primary comparison
using the target or the loss. No sealed cohort was read during development, and
prospective confirmation may begin only once the feature registry, models, preprocessing,
cutoff, universe, inference and detectable effect are frozen and hashed.

The retained Phase 8 cohort is governed by the exploratory bridge contract
(`docs/phase8_bridge_protocol_v2.md`). The twenty strictly unobserved sessions form the
primary descriptive window and all thirty sessions form a sensitivity; the first ten
overlap the already-read C2 dates. The bridge cannot produce a confirmatory claim, and its
separate written authorisation was consumed on 2026-08-30; the outcome and subsequent
same-session remediation sensitivity are reported in Section 5.2.

### 4.4 Session-level inference

The unit of observation is the trading session. Losses are averaged within a session
first, and that series is what every estimator sees, so an early-close session carries the
same weight as a full one and neither replicating nor reordering origins inside a day can
move an estimate. Intervals and p-values come from a circular block bootstrap over whole
sessions, with the block length fixed in advance at five sessions, 2,000 repetitions and a
fixed seed. Each contrast also reports a Newey–West long-run variance under a Bartlett
kernel at the same lag, a wild cluster bootstrap, Clark–West for linear nested pairs, and
Hansen's test of superior predictive ability. A bootstrap interval wholly inside one per
cent of the base loss is reported only as exploratory compatibility with the margin; the
implementation does not perform TOST or establish formal equivalence. Holm's correction is applied within each
family and role over its four nested contrasts — ΔB1, ΔB2|B0, ΔB2|B1 and the total — the
family the scientific question defines. The earlier programme's global Holm correction is
retained as a conservative bound, since no retrospective correction is exact for a
data-dependent sequence.

Interval calibration remains an explicit threat. The current run did not repeat the
separate empirical-coverage experiment, so this report does not transfer its historical
0.784 estimate to the replacement intervals. Every validation interval reported in §5.1
crosses zero; no current validation claim relies on interval exclusion.

### 4.5 Power, declared per contrast

A minimum detectable effect is computed for every contrast and published beside its
estimate: `(t_{1−α/2,n−1} + t_{power,n−1}) · sqrt(long-run variance / n)`, at α = 0.05
two-sided and power 0.80, over the same session series the interval is built on. It is
declared per contrast because a null without one is uninterpretable: it does not
distinguish an absent increment from a design that could never have seen one. The bounds
themselves, and the count of contrasts that fall below their own, are reported beside the
estimates in §5.1 rather than announced here.

Those published MDEs use the historical planning default α = 0.05. They do not share the
retrospective sensitivity budget of approximately 0.00417 and therefore understate the
session requirement that a new confirmatory design would face. Their defensible use here
is qualitative and comparative: validation was underpowered even under the less stringent
planning threshold.

What is fixed here is how they are to be read, and that reading was fixed before the
estimates existed. Where a contrast lies below its own detection threshold, its null is a
statement about the design and not about the market. The evidence can then show that a
discovery-sample effect is not reproduced out of sample, and show with numbers that
validation would not have seen that effect had it persisted; it cannot adjudicate whether
option state or flow carries information of that size, nor separate a change in the market
from a change in representation. Deciding either requires a fresh prospective cohort sized
in advance. The separate Block-12 design estimates at least 180 sessions and approximately
537 for its best observed favorable ΔB2|B1 case, with two independent families and one
read. That is future-design evidence, not a reason to hold the capstone open.

## 5. Results

The order below is binding (decision 53).

### 5.1 Retrospective results

The current reproducible retrospective evidence is
`rp2-v3-20260831-b1-spot-cutoff-remediation` (scientific hash
`033f2eb6be35e5db...`, code commit `b70c54ba14fd`). It covers the two disjoint calendar
roles frozen in §3 — discovery
D and validation V — on six outcome assets, with 60,407 and 12,480 common evaluation rows.
Three fixed families crossed with two nested contrasts and two roles give twelve
comparisons. A positive delta is an improvement in QLIKE: the loss of the smaller
information set minus the loss of the larger one. Eight deltas are positive and nine
intervals contain zero. These are retrospective exploratory measurements. Applying the
0.00417 sequential budget is a conservative post-hoc sensitivity, not preregistered
confirmation, and no validation contrast clears it.

In discovery ΔB1 is +0.00256 for `gamma_glm` (95 percent interval [+0.00100,
+0.00417]), +0.00287 for `ridge_log` ([+0.00153, +0.00437]) and +0.00320 for
`lightgbm_qlike` ([+0.00106, +0.00590]). All three intervals exclude zero, but their
retrospective origin and adaptive validation use cap them at exploratory evidence. The
effects are small relative to their B0 loss levels.

Validation does not establish replication. ΔB1 is −0.00150 for `gamma_glm`
([−0.00511, +0.00224]), −0.00088 for `ridge_log` ([−0.00315, +0.00156]) and +0.00280
for `lightgbm_qlike` ([−0.00518, +0.01030]); every interval contains zero. B0 QLIKE also
rises from 0.14522 to 0.18347 for `gamma_glm` and from 0.14239 to 0.21304 for
`lightgbm_qlike`, so the later role is both shorter and harder in level.

The conditional flow increment is mixed rather than globally null. In discovery
ΔB2|B1 is +0.00012 for `gamma_glm`, +0.00028 for `ridge_log` and +0.00052 for
`lightgbm_qlike`; in validation it is −0.00264, −0.00250 and +0.00198. Two of the six
family-role pairs are negative, and all six intervals cross zero. The small smooth-family
development estimates are compatible with
the recorded margin, but the implementation does not establish formal
multiplicity-adjusted TOST equivalence. The family- and partition-dependent signs do not
support a universal B2 contribution.

The current run preserves three result-changing repairs: bar roles are derived from
partition dates instead of trusted file literals; every B0 predictor, market control and
volatility state is shifted back three one-minute bars to share the documented 120-second
B1/B2 cutoff; and B1 uses the XNYS expiry-close calendar already used by B2. Adversarial
follow-up found a fourth defect: B1 option rows stopped at `t−120 s`, but parity,
moneyness and delta used `close[m]`, which ends at `t+60 s` for start-labelled bars. The
current run uses `close[m−3]`, the last underlying close admissible at the option cutoff.
It keeps the immediately prior run's 181,829-row panel membership. Relative to that run,
discovery ΔB1 moves from +0.00258, +0.00288 and +0.00267 to the values above; validation
moves from −0.00152, −0.00092 and +0.00136. This before/after isolates the spot-input
correction at the pipeline level, but does not decompose individual B1 feature movements.

Whether the validation nulls refute the discovery effect is a question about power. The
validation MDEs are 0.00506 for `gamma_glm`, 0.00315 for `ridge_log` and 0.01198 for
`lightgbm_qlike`, against discovery ΔB1 estimates of 0.00256, 0.00287 and 0.00320.
Approximate session requirements under the same exploratory α = 0.05 contract are 125,
39 and 449. They are not requirements computed under the separate 0.00417 future
campaign budget. None of the three validation designs was equipped to detect its corresponding
discovery effect. These are ex-ante-style planning quantities, not post-hoc observed power.

Ten of the twelve contrasts sit below their own minimum detectable effect. Where a
contrast lies below that threshold, a wide interval is a statement about the design, not
proof that the market effect is zero. The retrospective evidence therefore shows that the
discovery result is not confirmed in validation and that validation lacked the precision
to settle effects of that size. That is absence of evidence, not evidence of absence.

### 5.2 Phase 8 exploratory bridge at the evidence cutoff

The owner-authorised bridge consumed its sole read on 2026-08-30 under the frozen
twenty-session primary window and thirty-session sensitivity. Its classification is
`MIXED_EXPLORATORY`, descriptive and non-confirmatory. The first post-cutoff audit replayed
the historical forecast cube exactly, but that cube contains forecasts rather than B0/B1
feature rows and therefore could not incorporate the corrected `t−120s` underlying clock.

The project subsequently rebuilt and rescored the same thirty already materialized
sessions under a precommitted, append-only post-hoc remediation. It collected zero new
sessions, reopened no sealed store and left the canonical one-shot read count at one. The
corrected grid has 11,700 origins versus 11,875 historically: 175 `origin_minute = 30`
rows are no longer admissible because a full trailing thirty-minute B0 window does not
exist at the `t−120s` cutoff. B1's minimum core-feature finite coverage is
11,664/11,700 = 99.6923%, while all twelve B2 core features are 100% finite; the B2 core
values and `rv30` are exact on every paired key.

Absolute QLIKE does not improve generally: only one of eight B1-inclusive primary cells
has lower paired loss after remediation. Scientific validity improves because the
inadmissible clock is removed. The corrected contrasts retain the earlier qualitative
pattern: all four ΔB1 estimates are positive and three of four descriptive Holm p-values
are below 0.05; all four ΔB2 conditional on B1 intervals cross zero and none is
descriptively significant. The complete cells, paired QLIKE comparison, coverage
distinction, custody and hashes are reported in
`reports/phase8a_exploratory_bridge_addendum_v13.md`.

### 5.3 Directional B2 extension and treatment-by-coverage attribution

The registered directional extension returned `DO_NOT_PURSUE` with
`pursue_rule_passed = false`; its stricter sign falsifier did not fire. That means the
selected directional lead was not strong enough to justify a new programme, not that its
population effect was proved zero. The spot-cutoff-remediated run did not reopen that 68-test
battery. It did rerun the preregistered 2 × 2 factorial that asks whether movement in the
joint statistic is attributable to treatment definition or data coverage. Each entry
below is `Wald / df / raw p / 40-test Holm p`.

| Treatment set / coverage | D 60m | D 120m | V 60m | V 120m |
| --- | ---: | ---: | ---: | ---: |
| Ext1 exact / August | 12.567 / 10 / 0.248901 / 1.000000 | 11.793 / 10 / 0.299176 / 1.000000 | 27.846 / 10 / 0.001910 / 0.068774 | 29.575 / 10 / 0.001005 / 0.038196 |
| Ext1 exact / complete | 12.981 / 10 / 0.224741 / 1.000000 | 17.623 / 10 / 0.061665 / 1.000000 | 27.846 / 10 / 0.001910 / 0.068774 | 29.575 / 10 / 0.001005 / 0.038196 |
| B2 panel 12 / August | 29.378 / 12 / 0.003461 / 0.110753 | 22.729 / 12 / 0.030119 / 0.813202 | 30.497 / 12 / 0.002349 / 0.079872 | 26.468 / 12 / 0.009209 / 0.267060 |
| B2 panel 12 / complete | 33.068 / 12 / 0.000945 / 0.036843 | 37.078 / 12 / 0.000217 / 0.008680 | 30.497 / 12 / 0.002349 / 0.079872 | 26.468 / 12 / 0.009209 / 0.267060 |

On the registered `log(Wald / df)` scale, the median absolute treatment-set main effect
is 0.405476 and the coverage main effect is 0.037680, a ratio of 10.76. The registered
classification is `TREATMENT_SET`, descriptively rather than causally because the sets are
not nested. It does not explain the historical validation decline: August and complete
coverage have identical V masks, and the 12-feature panel set does not restore the frozen
V 120-minute statistic. For that decline the result is
`NEITHER_TREATMENT_SET_NOR_COVERAGE`.

The exact Ext1 contract names `b2_5m_hawkes_innovation`, which no longer exists in the
panel. The producer records a `RECORDED_SEMANTIC_RENAME` to
`b2_5m_decay_intensity_innovation`, maps the historical label in memory, retains the
ten-column Ext1 coefficient identity and does not recompute the feature. The obsolete
column bytes are unavailable, so historical byte equality cannot be confirmed. The full
factorial, requested/resolved names and hashes are in
`artifacts/rp2_ext1_directional_factorial_v3/results.json`; it records
`sealed_cohorts_read=0`.

### 5.4 Calibration, and what the loss is rewarding

QLIKE penalises calibration error, so a feature block that repairs a biased conditional
mean is scored as information (§4.2; Patton 2011). The ladder measures that channel rather
than assuming it away: every contrast is recomputed on forecasts that have first been
Mincer–Zarnowitz recalibrated in logs, with the recalibration fitted strictly outside the
sample on which the contrast is then scored.

Recalibration now moves the option-state increment only modestly, and that shrinkage is
itself a finding. An earlier version of this section reported recalibration lifting every
cell and turning both smooth families positive in validation, +0.00635 for `gamma_glm` and
+0.00315 for `ridge_log`; most of that lift was a defect, not a channel — the
recalibration was undoing the smearing correction it was applied on top of, one of the six
repairs of decision 92. Under the B1 spot-cutoff-remediated bundle, recalibrated discovery ΔB1 is
+0.00275 for `gamma_glm`, +0.00287 for `ridge_log` and +0.00334 for
`lightgbm_qlike`; validation reads −0.00079, −0.00086 and +0.00155, none significant
(`rp2_block8_ladder/ladder.json`). These figures are diagnostics and not the study's
result: the recalibration is estimated from data outside the evaluation, and the
primary raw contrast remains the one reported in §5.1, on which the report's claims
rest. The baselines are not equally well calibrated across the two roles — the fitted
slope of the gamma family's B0 forecasts is 1.00 in discovery and 1.03 in validation, and
the tree family's is 1.02 against 1.11 — so the raw validation nulls and the recalibrated
readings are measuring partly different things, and neither alone settles what the option
surface is worth.

The flow block does not benefit from the same treatment. Recalibrated discovery ΔB2|B1
is +0.00018 for `gamma_glm`, +0.00028 for `ridge_log` and +0.00055 for
`lightgbm_qlike`. Their bootstrap intervals may be compatible with the recorded margins,
but the artifact explicitly labels that diagnostic
`EXPLORATORY_BOOTSTRAP_CI_WITHIN_MARGIN_NOT_TOST`. It is therefore not formal equivalence
and cannot be promoted through the retrospective sequential-budget sensitivity.

The general point is the one Patton (2011) supplies. Where families disagree, the report
does not pool them or elect the agreeable one; it reports each as measured and treats the
disagreement itself as evidence about the loss rather than about the market.

### 5.5 Field-standard baselines and the activity block

The activity block was also tested against the baselines the field would demand, on the
separate development ladder of the earlier gate programme — forty-five out-of-fold sessions
and 28,787 origin rows, so its loss levels are not comparable with the panel of §5.1. There
the HARQ implementation is the strongest baseline of the ladder (pooled out-of-sample QLIKE
0.18012 against HAR's 0.18041; both remeasured 2026-08-25 after the Int8
seasonality-covariate correction of decision 96, ordering unchanged), and adding the
nine activity features to HAR or to HARQ
makes forecasts marginally worse (−0.00068 and −0.00070; all cluster/Newey–West/wild
p ≥ 0.50)
(`docs/gate3_har_harq_ladder_v1.md`). This historical diagnostic does not establish a
universal absence of flow information; it shows that the registered activity block did not
improve those HAR/HARQ specifications on the measured sessions.

### 5.6 Operational timing result: the 60-second opening bound

Gate 5 produced a separate target-blind operational timing result; it is not a predictive
result and uses no target, forecast or loss. Across all six reconciled sessions,
2,418/2,418 live flow alerts had support inside the registered contract window. The
receipt-latency distribution preserves the registered exclusion of the 2026-08-21
collector-replay anomaly, leaving five clean sessions and 1,768 first valid receipts.

The New York opening hour contains 406 first receipts. Of these, 6/406 (1.48 per cent)
arrived more than 60 seconds after `created_at`; p99 was 60.216898 seconds, and 0/406
exceeded 120 seconds. The registered 60-second UW availability buffer therefore does not
hold as a strict conservative bound at the NY opening in this sample. The 120-second
sensitivity has no opening exceedance, but two of 95 receipts in hour 14 exceeded 120
seconds, so it is not a strict all-day bound in the observed sessions.

Five sessions and 406 opening receipts can falsify a zero-exceedance claim in the observed
sample; they cannot certify future sessions. The estimand is local
`receipt_utc − created_at`, not provider publication time or historical client receipt.
Accordingly, `created_at` remains `PROXY_ONLY_CROSS_CHANNEL`, backfill and revision remain
non-identifiable, and `PIT_V22_RECONCILIATION_BLOCKED` remains in force
(`artifacts/gate5_pit/uw_latency_campaign_20260902_v3.json`;
`docs/gate5_pit_foundations_v1.md`).

## 6. Discussion

Three statements survive the evidence assembled above. First, discovery ΔB1 is positive
with an interval excluding zero in all three fixed families, while ΔB2|B1 is smaller and
changes sign across families and roles; neither pattern is a universal information claim.
The separate HAR/HARQ diagnostic also finds no improvement from its activity block, the
directional rule returns `DO_NOT_PURSUE`, and Phase 8 adds no incremental B2 result on top
of B1. Second, the discovery result is not confirmed on the later validation sample, and
the design cannot say why: ten of the twelve contrasts sit
below their own minimum detectable effect, so the validation nulls are absence of evidence
and not evidence of absence. The report can state that it did not see the effect again; it
cannot state that the effect is gone, and it declines to. Third, what QLIKE reports depends
on how well the family being scored is calibrated, which is why the same increment moves
when the forecasts are recalibrated out of evaluation, and why no single family's number is
presented as the study's answer.

The honest reading of the programme is therefore a bounded one, and the bound is the
contribution rather than an apology for it. A study that reports a null without the
precision of the design that produced it has not measured anything; this one reports both,
and states the sessions each family would have needed. That accounting is what turns an
unreproduced effect into a specific, answerable question rather than a verdict, and it is
also what keeps the negative reading of the flow block honest: the cleanest null in the
study is still a null measured at a stated precision, not a demonstration that the flow
tape is empty of information.

The closing campaigns follow from the same logic, but neither is used to hold the report
open. Phase 8 is complete as a one-read `MIXED_EXPLORATORY` bridge and cannot be promoted
or reopened as a new canonical evaluation. Its same-session post-hoc remediation is a
sensitivity over already materialized bytes, not a second confirmation. Phase 9 (decision
58) remains a frozen, collecting, 60-session one-read test of
total contribution. Decisions 100–101
make it a prospective follow-up rather than an academic submission gate and correct its
planning denominator: the 24-session warm-up means that 60 complete sessions produce 36
scored sessions. At 80% power, the corrected endpoint MDE spans 0.01105–0.02507 under the
binding alpha 0.008333 across the four frozen planning scenarios. Rolling forward the two
misses recorded by decision 97 gives 2026-11-13 as the earliest nominal completion if
every later session is complete. The best-case three-week horizon contains only 19
complete sessions and zero scored sessions, so no valid Phase 9 result can exist by the
academic deadline. No Phase 9 outcome is included, and `sealed_cohorts_read=0`.

## 7. Threats to validity

The governing threat is that validation was not equipped to decide the question it was
asked. Inference is at session level, and validation contributes thirty-two evaluated
sessions against discovery's one hundred and fifty-six. The minimum detectable effects
that follow — 0.00506 for `gamma_glm`, 0.00315 for `ridge_log`, 0.01198 for
`lightgbm_qlike` — stand against discovery increments of +0.00256, +0.00287 and +0.00320,
and ten of the twelve contrasts sit below their own bound (§5.1). Every validation null
reported above is therefore absence of evidence: the report cannot claim that the option
surface or the point-in-time flow carries nothing, only that a design of this size would
not have seen them had they been there.

The threat is not one-sided. Validation ΔB2|B1 is negative for `gamma_glm` and
`ridge_log` but positive for `lightgbm_qlike`; all three intervals cross zero. The current
run therefore establishes neither incremental benefit nor harm from B2 in validation.
The family-dependent signs and wide intervals are part of the result, not permission to
select the agreeable family.

Model family is the second threat, exposed by the design rather than removed by it. The
three fixed families give discovery ΔB1 of +0.00256, +0.00287 and +0.00320, while
validation gives −0.00150, −0.00088 and +0.00280 and their minimum detectable effects
differ by a factor of 3.8. The family therefore fixes both the estimate and what the experiment
could have detected, and because all three are fitted to the same origins, their
agreement is not replication.

Scope is bounded and permanent. The panel holds 181,829 origins, but they come from six
mega-cap US equities on one exchange calendar, so the cross-section carries far less
independent information than the row count suggests, and nothing here extends to less
liquid underlyings, other option markets, or other session structures. The per-era and
leave-one-asset-out jackknives specified for this concern have not been re-estimated on
the current panel, so asset concentration is stated rather than bounded. The information
sets are representations, not the constructs they
name. In D/V, B1 reaches a minimum core-feature coverage of 0.9934 with no post-cutoff
observation; in the same-session Phase 8 remediation its minimum is 0.996923, with
`b1_risk_reversal_25` finite on 11,664 of 11,700 current-grid origins and every other core
feature finite on all origins. Its
quotes have a pooled median age of 550 s and a pooled 95th percentile of 1,725 s against
an 1,800 s window, and the implied rate could not be fitted on 43.1 per cent of origins —
no row was dropped for it — so a null on B1 is a null on a surface of that age and that
fit quality. B2 is one vendor's option-trade tape read through an availability proxy,
with an empty flow window on 0.23 per cent of measurements.

That availability threat is now measured rather than merely asserted. The five-session
receipt audit falsifies a zero-exceedance interpretation of the 60-second opening buffer,
but its short span cannot identify a future-session tail probability, and the separate
cross-channel design still cannot identify backfill or revision. The absence of opening
exceedances beyond 120 seconds is therefore a bounded sample result, not proof of a
universal provider-latency guarantee.

Finally, the chronological separation limits what the validation null can mean. It
preserves temporal ordering within each measurement, but adaptive use of V prevents a
confirmatory interpretation and a time split cannot distinguish regime change from a
smaller training sample or an absent effect. B0 QLIKE rises from 0.14522, 0.14576 and
0.14239 in discovery to 0.18347, 0.18724 and 0.21304 in validation. Randomly mixing
sessions would conceal that temporal-generalisation problem rather than solve it.

The Phase 8 remediation is also post-hoc: the original outcomes were known before the
corrected B0/B1 clock was applied. Its precommitted paired-grid rules prevent selective
reporting within the rerun, but they cannot restore the prospective blindness of the
historical one-shot execution. It supports a robustness interpretation only.

## 8. Conclusion and contribution

Does source-time options information improve out-of-sample RV30 forecasts? The current
evidence does not support one universal answer. Discovery ΔB1 is positive in all three
families, but validation is mixed and too imprecise to confirm an effect of that size.
ΔB2|B1 is small and changes sign by family and partition; compatibility with an
equivalence margin in selected exploratory cells is not a formal TOST result. The D/V
measurements are retrospective, validation was used adaptively, and the sequential budget
is only a conservative post-hoc sensitivity. They therefore remain exploratory.

The defensible contribution is the bounded measurement and its infrastructure: nested
information sets on identical origins, session-level uncertainty, explicit MDE accounting,
date-derived partition roles, one market-information cutoff, one XNYS expiry calendar and
source-time PIT rules that fail closed instead of claiming client latency they do not
observe. That machinery produced a substantive negative methodological result: the
60-second UW availability buffer is not a strict conservative opening bound in the five
clean sessions, while the 120-second opening sensitivity remains sample-bounded rather
than provider-certified. The remaining PIT v2.2 blocker is part of the result, not
something concealed by a headline. Phase 8 is complete and exploratory; its corrected same-session sensitivity
does not improve paired QLIKE generally and does not create a confirmatory result. Phase 9
continues to 60 as prospective
future evidence while the capstone is written and submitted from the evidence available at
its editorial cutoff.

### Future work: the sealed RP3 program (preregistered 2026-08-24)

The one question this report leaves open — whether the tree family's budget-clearing B2
increment is information or estimator artefact — has been converted from a wish into a
sealed program before any RP3 evaluation. `docs/rp3/PREREGISTRATION.md`
(SHA-256 `66906a88b0d8ff76d9bbc6556e0aa64e32de494254d2ebdccc49140fce7f77e7`, computed over the committed file as git stores it, LF line endings) registers a
closed list of two hypotheses on an evaluation window that starts where this study's
validation role ends (sessions ≥ 2026-07-18, most of which did not exist at seal time):
the primary is the prospective replication of the +0.00101 development cell, with B2
compressed to a single frozen linear index (theta sealed in
`artifacts/rp3/b2_index_theta.json`, SHA-256
`d3140451976ffb485a68c42ff109fcb8c5a434c810fed24055bf929ce09365b6`), read once at 662
evaluable sessions (estimated 2029-01-30) under a winner's-curse-halved sizing recorded in
`artifacts/rp3/sizing.json`; the secondary, gatekept behind the primary, is directional
information at 120 minutes. The program's own selection liabilities are declared inside
the preregistration rather than around it — including the candidate it killed before
sealing: the exploratory sweep favoured a 60-minute target, and the sizing measurement
found the frozen index's development effect there to be negative, a dead end recorded
permanently beside the road taken. The read's outcome, whatever it is, is committed to
publication with the same prominence as a positive.

## 9. Ethics and reproducibility

No human participants. Licensed raw data and credentials are never redistributed or
committed. Reproducibility for unlicensed examiners is provided as controlled
auditability: code, schemas, sanitised fixtures, SHA-256 manifests, access ledgers,
and aggregate outputs, under a locked Python 3.12 environment and a
thousand-test suite. Vendor labels are treated as observed events, never as trader
intent; no informed-trading, causal, or profitability claim is made anywhere in the
report.

## Appendices

A. Campaign register and contrast tables (`docs/results_reconciliation_v2.md`).
B. Studentized inference tables (`artifacts/gate1_inference/`).
C. Gate reports 1–12 (`docs/INDEX.md`).
D. Economic-significance tables (`artifacts/economic_significance/`).
E. Preregistration, freeze and target-blind planning hashes (Phase 9 freeze
   `artifacts/phase9/protocol_freeze.json`; corrected power/deadline audit
   `artifacts/phase9/power_deadline_audit_v1.json`).
F. Supervisor feedback mapping, restricted to source-verified comments; unverified
   paraphrases are excluded.
G. Primary run artifacts (`artifacts/rp2_v3/rp2-v3-20260831-b1-spot-cutoff-remediation/`: `scorecard.md`,
   `rp2_block8_ladder/ladder.json`, `rp2_block10_inference/inference.json`,
   `run_identity.json`) and the run verdict (`docs/rp2_v3/VERDICT.md`).
