# Block 7 — the decisive experiment: DML orthogonalisation of B2

**Status:** `SUPERSEDED_BY_RP2_V3`. Sections 1-5 are the 2026-08-19 cascade narrative and are
kept unaltered for the audit trail: a reader who followed a citation to an RP2-v2 number must
still find it here. **Every figure in sections 1-5 is superseded** by section 0, and the ones
that were never supported by any artifact are labelled in place.
**Measured on `rp2-v3-20260822-114000`** (scientific hash `5c6a4c0e2b661e91`, commit `da2fb7b`)
**Current artifact:** `artifacts/rp2_v3/rp2-v3-20260822-114000/rp2_block7_dml/dml.json`
(`dml_sha256 = 030b2e358f9cb8534c0cdfb14cc36993051d06ea61ed087bee4f038d8ec0e286`)
**Superseded artifact:** `artifacts/rp2_block7_dml/dml.json`
(`dml_sha256 = 01775dcb89b76979b5e0024126ac4bcaff1eef69cbe6b270a95df3364db8272a`, generated
2026-08-19) — still present, still hashed, never overwritten.
**Code:** `src/mds650/rp2/dml.py`, `scripts/rp2_block7_dml.py`
**Tests:** `tests/unit/test_rp2_dml.py`; `tests/contract/test_block7_narrative_matches_artifact.py`
checks every figure in section 0 against the run this header names.

Register row: `docs/rp2_v3/SUPERSEDED_RESULTS.md`, entries dated 2026-08-23.

---

## 0. What the current run measures

Cross-fitted over five contiguous time blocks with a one-session purge, clustered by session.
Read off `artifacts/rp2_v3/rp2-v3-20260822-114000/rp2_block7_dml/dml.json`; nothing below is
transcribed from an older run.

| Universe | Origins | Sessions | Nuisance design columns | Folds |
|---|---|---|---|---|
| D | 152,954 | 389 | 33 | 5 |
| V | 31,678 | 80 | 33 | 5 |

### Joint cluster-robust Wald

`core` is the ten preregistered treatments; `full` is `B2_CORE`, which the current code fits at
**twelve** treatments (`full_b2_treatment_count = 12`), not the fifty-eight of section 4.
`delta log RV30` is written without its Δ so that the contract test parses this table by exact
string; it is the same outcome section 2 calls `Δ log RV30`.

<!-- BLOCK7_CURRENT_JOINT_START -->

| Design | Universe | Outcome | Origins | Clusters | Wald | p |
|---|---|---|---|---|---|---|
| `core` | D | `log RV30` | 152,954 | 389 | 98.75420 | 9.67324e-17 |
| `core` | D | `log jump30` | 152,954 | 389 | 18.34069 | 0.0494815 |
| `core` | D | `delta log RV30` | 152,954 | 389 | 98.75420 | 9.67324e-17 |
| `core` | V | `log RV30` | 31,678 | 80 | 5.79616 | 0.832088 |
| `core` | V | `log jump30` | 31,678 | 80 | 18.76234 | 0.0433873 |
| `core` | V | `delta log RV30` | 31,678 | 80 | 5.79616 | 0.832088 |
| `full` | D | `log RV30` | 152,954 | 389 | 99.51768 | 6.92052e-16 |
| `full` | D | `log jump30` | 152,954 | 389 | 24.43711 | 0.0177274 |
| `full` | D | `delta log RV30` | 152,954 | 389 | 99.51768 | 6.92052e-16 |
| `full` | V | `log RV30` | 31,678 | 80 | 29.87842 | 0.00291253 |
| `full` | V | `log jump30` | 31,678 | 80 | 29.22711 | 0.00364519 |
| `full` | V | `delta log RV30` | 31,678 | 80 | 29.87842 | 0.00291253 |

<!-- BLOCK7_CURRENT_JOINT_END -->

The structural identity of section 2 still holds and is still a correctness check:
`delta log RV30` and `log RV30` agree to every digit in all four designs, because
`log RV_back30` sits inside the B0 nuisance set and the two residuals are numerically the same
vector after partialling out.

### Which features carry it, on the current run

Core design, outcome `log RV30`.

<!-- BLOCK7_CURRENT_TREATMENTS_START -->

| Treatment | D: theta (t, p) | V: theta (t, p) |
|---|---|---|
| `b2_5m_vega_flow` | +0.00200335 (t = +1.141, p = 0.2547) | +0.000306926 (t = +0.075, p = 0.9403) |
| `b2_5m_gamma_flow` | +0.000529249 (t = +0.355, p = 0.7224) | -0.000863364 (t = -0.294, p = 0.7694) |
| `b2_5m_delta_flow` | -0.00922768 (t = -4.507, p = 8.705e-06) | -0.000952107 (t = -0.283, p = 0.7779) |
| `b2_5m_premium` | +0.0796761 (t = +4.958, p = 1.065e-06) | +0.0111175 (t = +0.897, p = 0.3723) |
| `b2_5m_trades` | -0.0761583 (t = -4.653, p = 4.49e-06) | -0.0268922 (t = -1.164, p = 0.248) |
| `b2_5m_decay_intensity_innovation` | +0.00680615 (t = +6.998, p = 1.144e-11) | +0.00392339 (t = +1.657, p = 0.1014) |
| `b2_5m_d_iv` | -0.00400245 (t = -2.094, p = 0.03695) | -0.0015063 (t = -0.333, p = 0.7397) |
| `b2_5m_buy_premium_share` | +0.00196079 (t = +0.846, p = 0.3979) | +0.00442264 (t = +0.743, p = 0.4594) |
| `b2_5m_strike_hhi` | -0.00899289 (t = -3.723, p = 0.0002261) | +0.000603169 (t = +0.132, p = 0.8955) |
| `b2_5m_otm_premium_share` | +0.00341522 (t = +1.591, p = 0.1124) | +0.000466685 (t = +0.081, p = 0.9356) |

<!-- BLOCK7_CURRENT_TREATMENTS_END -->

**No treatment clears 0.05 in both universes.** The smallest validation p-value of the ten is
0.1014. The joint core test does not reject in validation at all (p = 0.832), which is a weaker
validation result than the 0.0623 of the superseded run rather than a stronger one. Nothing here
replicates across universes, and the claim that anything does is withdrawn.

Three of the ten change sign against the superseded table, and one of the three keeps its
significance while doing so: `b2_5m_trades` moves from θ = +0.056656 (t = +5.32) to
θ = −0.0761583 (t = −4.653) in discovery. `b2_5m_premium` changes sign in validation only, and
`b2_5m_vega_flow` in discovery only. `b2_5m_buy_premium_share`, one of the two treatments the
superseded narrative called replicated, is null in both universes now (t = +0.846, t = +0.743).
`b2_5m_delta_flow` — a Greeks-weighted quantity section 3 called null in both universes — is
the third-strongest discovery treatment on the current run.

### Claim ledger

Every figure sections 1-5 publish, checked against the artifact those sections cite and against
the run this page names. `UNSUPPORTED` means the figure reproduces against **no** artifact in
this tree — not the one the page cites, not the current one, and not any of the 375 JSON
artifacts under `artifacts/`.

| Where | Claim | Against the cited 2026-08-19 artifact | Verdict |
|---|---|---|---|
| §1 table | D 89,889 origins / 230 sessions | artifact says 90,549 / 383 | `SUPERSEDED` — the pair does exist, in `artifacts/rp2_ext1_mechanism_utility/mechanism_utility.json` (pre-rebuild panel), not in block 7's own artifact |
| §1 table | V 31,131 origins / 80 sessions | artifact says 18,230 / 80 | same, same file |
| §1 table | 38 nuisance features | artifact says 49 | `UNSUPPORTED` — no artifact in the tree carries 38; the only values recorded are 49 (2026-08-19) and 33 (RP2-v3) |
| §2 | core Wald 241.71 / p 2.99e-46 in D; 17.59 / 0.0623 in V | matches to five decimals | `REPRODUCED` against the cited artifact, `SUPERSEDED` by §0 (98.75 / 9.67e-17 and 5.80 / 0.832) |
| §2 | jump Wald 14.10 / p 0.169 in D; 19.92 / 0.03 in V | matches | `REPRODUCED`, `SUPERSEDED` by §0 (18.34 / 0.0495 and 18.76 / 0.0434) |
| §2 | the structural identity of `Δ log RV30` and `log RV30` | holds | `REPRODUCED` and still holds on the current run |
| §2 | all ten treatment rows | match to five significant figures | `REPRODUCED`, `SUPERSEDED` by §0 |
| §2 | "only `b2_5m_trades` carries the same sign at conventional significance in both" | true of that artifact | `SUPERSEDED` — on the current run nothing does, and `b2_5m_trades` has the opposite sign in D |
| §2 | "Validation's B0 carries no market-wide state" | — | `SUPERSEDED` — decision 75 added `validation_market` (`src/mds650/rp2/bars.py:58-62`); the current artifact's V nuisance set carries `SPY_rv_30`, `SPY_ret_30`, `QQQ_rv_30` and `QQQ_ret_30`, and is the same 32-feature list as D's |
| §3 | vega, gamma and delta flow "are null in both universes" | true of that artifact | `SUPERSEDED` — `b2_5m_delta_flow` is p = 8.7e-06 in D on the current run |
| §3 | what survives is the intensity innovation and the buy-side premium share | true of that artifact | `SUPERSEDED` — the intensity innovation survives in D (t = +6.998) and the buy-side share does not (t = +0.846) |
| §4 | full-block D Wald 501.87, p 5.9e-72 | artifact says **486.71399, p 4.9535e-69** | `UNSUPPORTED` |
| §4 | full-block V Wald 548.92, p 4.4e-81 | artifact says **576.71477, p 1.60728e-86** | `UNSUPPORTED` |
| §4 | 58 treatments | artifact agrees (`full_b2_treatment_count = 58`) | `REPRODUCED`, `SUPERSEDED` — the current code fits 12 and the 58-treatment design is not reproducible today |
| §4 | full-block D jump p = 0.031 | artifact says **0.0152657** | `UNSUPPORTED` |
| §4 | core D jump p = 0.224 | artifact says **0.168617** | `UNSUPPORTED` |
| §4 | "the same universe returns p = 0.059 on the ten-treatment core test" | its own §2 says 0.0623 | `UNSUPPORTED` — internally inconsistent with the same page |
| §5 | core D rejects at p = 6 × 10⁻³⁹ | artifact says **2.9915e-46** | `UNSUPPORTED` |
| §5 | core V returns p = 0.059 | artifact says **0.0623294** | `UNSUPPORTED` for block 7; 0.05938 is the V figure in `artifacts/rp2_ext1_mechanism_utility/mechanism_utility.json` |

The verdict `H_B2,J recorded as not supported` rested on the two `UNSUPPORTED` jump figures, so
it is **withdrawn rather than replaced**. What the current run measures is stated in §0 and
nothing here upgrades it to a verdict: both jump p-values sit just below 0.05 nominally, no
multiplicity adjustment over the three outcomes is recorded in the artifact, and the programme's
alpha budget lives in block 10.

---

## 1. The question this block answers, and the one it does not

> *"The correct question is not whether a model with B2 happens to have lower loss, but
> whether B2 contains information that cannot be reconstructed from B0+B1."*

Partialling-out double machine learning:

```
m(X) = E[Y | B0, B1]      g(X) = E[B2 | B0, B1]
Ỹ = Y − m̂⁽⁻ᵏ⁾(X)          B̃2 = B2 − ĝ⁽⁻ᵏ⁾(X)          Ỹ = θᵀ B̃2 + ε
```

Nuisance functions are cross-fitted over **five contiguous time blocks with a one-session
purge** — never random folds — and inference is clustered by session, because five-minute
origins share overlapping thirty-minute targets and treating them as independent would shrink
every standard error by roughly √66.

**What a rejection of `H₀: θ = 0` means:** there is a population-level linear relationship
between residualised B2 and the residualised outcome. **What it does not mean:** that a model
using B2 forecasts better out of sample. Block 8 answers that separately, and the two answers
differ — which is the main scientific content of this program.

`SUPERSEDED` — current counts are in §0. The nuisance count in this table is `UNSUPPORTED`: no
artifact in the tree records 38.

| Universe | Origins | Sessions | Nuisance features | Folds |
|---|---|---|---|---|
| D | 89,889 | 230 | 38 | 5 |
| V | 31,131 | 80 | 38 | 5 |

## 2. Primary result — significant in discovery, absent in validation

`SUPERSEDED`. Every figure in this section reproduces exactly against
`artifacts/rp2_block7_dml/dml.json` and is replaced by §0.

Ten economically distinct treatments from the 5-minute window. Joint cluster-robust Wald:

| Outcome | D (383 clusters) | V (80 clusters) |
|---|---|---|
| `log RV30` | Wald 241.71, **p = 2.99e-46** | Wald 17.59, p = 0.0623 |
| `log jump30` (H_B2,J) | Wald 14.10, p = 0.169 | Wald 19.92, p = 0.03 |
| `Δ log RV30` (H_B2,ΔRV) | Wald 241.71, p = 2.99e-46 | Wald 17.59, p = 0.0623 |

> **Structural identity, not a duplicate row.** `Δ log RV30 = log RV30 − log RV_back30`, and
> `log RV_back30` is inside the B0 nuisance set. After partialling out B0+B1 the two
> residuals are numerically identical, so the two tests must coincide. This is a correctness
> check on the implementation, and it means **H_B2,ΔRV is not a separate hypothesis** once
> the baseline already contains the trailing realized variance.

### Which features carry it

| Treatment | D: θ (t, p) | V: θ (t, p) |
|---|---|---|
| `b2_5m_premium` | +0.053763 (t = +6.10, p = 2.64e-09) | -0.012157 (t = -0.65, ns) |
| `b2_5m_strike_hhi` | -0.18605 (t = -4.81, p = 2.14e-06) | +0.084708 (t = +0.91, ns) |
| `b2_5m_decay_intensity_innovation` | +0.0017087 (t = +4.35, p = 1.78e-05) | +0.00023915 (t = +0.29, ns) |
| `b2_5m_delta_flow` | -0.00064111 (t = -4.03, p = 6.85e-05) | -0.00026684 (t = -0.98, ns) |
| `b2_5m_otm_premium_share` | +0.036015 (t = +1.68, ns) | +0.036227 (t = +0.77, ns) |
| `b2_5m_trades` | +0.056656 (t = +5.32, p = 1.81e-07) | +0.092638 (t = +3.13, p = 0.00244) |
| `b2_5m_buy_premium_share` | +0.063958 (t = +2.74, p = 0.00653) | +0.00083511 (t = +0.01, ns) |
| `b2_5m_vega_flow` | -0.0001246 (t = -0.80, ns) | +1.0422e-05 (t = +0.03, ns) |
| `b2_5m_gamma_flow` | +8.1485e-05 (t = +0.81, ns) | +8.4811e-06 (t = +0.04, ns) |
| `b2_5m_d_iv` | -4.0094 (t = -1.50, ns) | +0.1084 (t = +0.03, ns) |

**On the rebuilt panels the joint test is overwhelming in discovery and does not reach
significance in validation** (p = 0.0623 against a 0.05 threshold). Only `b2_5m_trades`
carries the same sign at conventional significance in both.

`SUPERSEDED` — on `rp2-v3-20260822-114000` no treatment clears 0.05 in both universes, and
`b2_5m_trades` carries the *opposite* sign in discovery.

This is a change from what this document previously reported, and it is a consequence of the
data corrections rather than of a different estimator: early-close sessions had been discarded
by a quality gate reading a fabricated 390-minute grid, two acquisitions overlapped on 24
session-assets so their origins were double-weighted, B1 is now built against a measured
forward and an exact tenor, and B1's snapshot window no longer overlaps the flow windows it is
being compared against.

The treatment named `b2_5m_hawkes_innovation` in the previous table is the same measure under
its honest name, `b2_5m_decay_intensity_innovation`: its baseline, excitation and decay were
fixed inputs, nothing was estimated, and there is no branching ratio behind it (decision 68's
companion rename).

**Read the discovery column against decision 75.** Validation's B0 carries no market-wide
state — SPY and QQQ bars exist for discovery sessions only — so its baseline is *weaker*, and a
weaker baseline should make a B2 increment easier to find, not harder. It is absent anyway.

`SUPERSEDED` — this paragraph preserves a defect that decision 75 already corrected. The
`validation_market` store (`src/mds650/rp2/bars.py:58-62`) supplies SPY and QQQ across the
validation sessions precisely so that the two baselines match, and the current artifact's V
nuisance set is the same 32-feature list as D's, `SPY_rv_30` and `QQQ_rv_30` included. The
asymmetry the paragraph reasons from no longer exists, so neither does the argument.

## 3. The finding, stated plainly

`SUPERSEDED` — see the claim ledger in §0. Half of this section survives the current run and
half is reversed: the intensity innovation is the strongest discovery treatment (t = +6.998),
the buyer-initiated premium share is null in discovery (t = +0.846), and `b2_5m_delta_flow`,
named here as null in both universes, is significant in discovery (p = 8.7e-06).

**It is the *timing* and the *direction* of option flow that carry incremental information,
not its Greeks-weighted size.**

Vega, gamma and delta flow — the exposure-weighted quantities the program's §6.1 proposed as
the primary redesign, and the ones a practitioner would name first — are null in both
universes. What survives is:

* `hawkes_innovation` — how far the current arrival intensity exceeds its own recent
  conditional expectation, i.e. an unexpected *burst*; and
* `buy_premium_share` — the fraction of premium that was buyer-initiated.

That has a coherent reading. A sudden, unexpected cluster of buyer-initiated option trades is
informative about the next thirty minutes of realized variance in a way that the same dollar
value of vega, arriving smoothly, is not. It also explains why the incumbent B2 found nothing:
five-minute counts of trades and premium cannot represent an intensity innovation at all, and
did not carry a side split.

This is the program's §1 explanation **5** — *"the current aggregation destroys the signal"* —
confirmed on its own terms. But see Block 8: the recovered signal is real and too small to
matter, which is §1 explanation **6**.

## 4. The full-block test is reported and then set aside

`SUPERSEDED`, and four of its figures are `UNSUPPORTED` against the artifact this page cites.
The 58-treatment design is not reproducible with the current code, which fits twelve
(`full_b2_treatment_count = 12`). The Wald statistics and p-values in the table below appear in
no artifact in this tree; the cited 2026-08-19 artifact records **D 486.71399, p 4.9535e-69**
and **V 576.71477, p 1.60728e-86** for the same cells.

| Universe | Treatments | Clusters | Wald | p |
|---|---|---|---|---|
| D | 58 | 383 | 501.87 | 5.9 × 10⁻⁷² |
| V | 58 | **80** | 548.92 | 4.4 × 10⁻⁸¹ |

**The V row is not trustworthy and is not used.** With 58 treatments and 80 clusters, the CR0
cluster-robust covariance is built from 80 outer products of a 58-vector; it is close to rank
deficient, and its pseudo-inverse inflates the Wald statistic. A p-value of 10⁻⁸¹ on 80
trading days is a symptom of that, not evidence — and it is the clearest possible illustration
of why: the same universe returns p = 0.059 on the ten-treatment core test, where the
covariance is well conditioned. The rule applied here is that the treatment count must stay
well below the cluster count, which the core test satisfies (10 ≪ 80) and the full block does
not.

The rule survives; its application does not. The current `full` design carries twelve
treatments against 80 validation clusters, so the rank-deficiency argument no longer bites and
the V row is no longer discarded on those grounds. The `p = 0.059` this paragraph attributes to
its own core test is `UNSUPPORTED`: §2 of this page says 0.0623 and the artifact agrees with §2.

The D full-block row (58 treatments, 383 clusters) is better conditioned; it is reported as
supporting, never as primary. Its jump result (p = 0.031) is the only support `H_B2,J`
receives anywhere, and it does not survive the core test (p = 0.224), so **`H_B2,J` is
recorded as not supported**.

`UNSUPPORTED` — the cited artifact records 0.0152657 for the full-block jump test and 0.168617
for the core one. Neither 0.031 nor 0.224 appears in any artifact, so the verdict built on them
is withdrawn rather than replaced; §0 states what the current run measures and stops there.

## 5. Advance rule

`SUPERSEDED`, and both of its p-values are `UNSUPPORTED` against the artifact this page cites
(which records 2.9915e-46 in D and 0.0623294 in V).

**"Preliminary incremental evidence": PASS in discovery only.** `H₀: θ = 0` is rejected for
the core B2 block in discovery at p = 6 × 10⁻³⁹ — B2 contains structure that B0 and a full
arbitrage-aware B1 surface cannot reconstruct in that sample.

**It does not carry to the second sample** (p = 0.059, and only `b2_5m_trades` keeps its sign
at conventional significance). Neither sample is confirmatory (decision 67), so this is one
exploratory result that does not reproduce in a second exploratory sample — which is weaker
than the previous version of this document claimed, and the claim of replication is withdrawn.

Whether the discovery structure is worth anything is Block 8's question, and the answer there
is still no.

**On the current run the shape of that conclusion is unchanged and its evidence is weaker on
both sides.** Discovery still rejects — Wald 98.75, p = 9.67e-17 — and validation now fails to
reject by a wide margin rather than a narrow one, at p = 0.832 instead of 0.0623. No treatment
clears 0.05 in both universes, so there is nothing left to withdraw a replication claim about.
