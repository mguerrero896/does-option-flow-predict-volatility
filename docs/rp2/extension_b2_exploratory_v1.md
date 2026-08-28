# B2 exploratory campaign v1 — five registered candidates against the frozen index

**Label: EXPLORATORY_DIAGNOSTIC.** Nothing in this document is confirmatory. Authorized
by the owner 2026-08-25 (decision 94), run once by
`scripts/rp2_b2_exploratory_campaign.py` on the `rp2-v3-20260824-remeasure` panels,
D and V roles only (2024-08-02..2026-07-17 — no sealed session touched). Artifact:
`artifacts/rp2_b2_exploratory/results.json` (self-hash `4800b840d22523c2…`), bound to
this document by `tests/contract/test_b2_exploratory_doc_matches_artifact.py`.

## The question, and the discipline

RP3 froze a single linear index (theta) as the best committed extraction of B2. This
campaign asks whether a better extraction exists — under the discipline that separates
exploration from significance-hunting: a **closed list of five candidates registered
before any measurement ran**, selection on the D-role 60/40 chronological fold, **one
walk-forward look at V** with Benjamini–Hochberg q-values across the five, and the
incumbent `B0+B1+index` as the bar. The registered success bar for RP4 candidacy:
positive against the incumbent on V with q ≤ 0.10, and positive on D-test.

## The anchor held

Before believing any candidate, the campaign re-measured the sealed sizing contrast
with the same harness (same fitter and calling convention, seed 650, block-10 common
mask): R0→R1 on D-test = **+0.001015**, wild-cluster p **0.0010** — the committed
number, reproduced exactly. On V, the incumbent's effect echoes at **+0.001010**
(p 0.063, ~80 sessions). V is not virgin — this is context for RP3's hypothesis, not
evidence about it.

## Results — every registered candidate, both windows, both baselines

ΔQLIKE, session-clustered; wild-cluster p in parentheses; q = BH across the five V
contrasts against the incumbent.

| Candidate | D-test vs incumbent | V vs incumbent | q (V) | D-test vs base | V vs base |
| --- | --- | --- | --- | --- | --- |
| c1_flow_regime | +0.00056 (0.076) | +0.00074 (0.305) | 0.762 | +0.00157 | +0.00175 |
| c2_vol_regime | +0.00014 (0.338) | +0.00019 (0.509) | 0.848 | +0.00115 | +0.00120 |
| c3_curvature | +0.00018 (0.032) | −0.00007 (0.734) | 0.918 | +0.00120 | +0.00094 |
| c4_sparse | −0.00012 (0.587) | +0.00001 (0.976) | 0.976 | +0.00089 | +0.00102 |
| c5_second_index | +0.00062 (0.004) | +0.00082 (0.070) | 0.352 | +0.00164 | +0.00183 |

## Verdict

**No candidate clears the registered bar.** The frozen theta index remains the best
committed extraction of B2, and RP3 — its seal, its closed two-test list, its look
counter at 0 — is untouched by this campaign.

Two positive-signed **recorded leads** survive for a future program:

1. **The second orthogonal index (c5)** is the strongest: fitted on the residual after
   the first index has spoken, it is positive with the same sign in both windows
   (D-test +0.00062, p 0.004; V +0.00082, p 0.070) and would roughly double the
   increment over base (+0.00183 vs the incumbent's +0.00101 on V). Read plainly: B2
   appears to carry a **second linear direction** the single theta misses. With ~80 V
   sessions the look is underpowered, and q = 0.35 keeps it honest.
2. **The flow-regime interaction (c1)** — the D3 lead — stays positive in both windows
   but noisy. Its genealogy matters: D3 itself was post-selection, and this campaign
   is its first out-of-fold check.

And one demonstration of why the bar exists: **curvature (c3)** was significant on
D-test (p 0.032) and sign-flipped on V — the exact selection noise the one-look
protocol is built to execute.

## What this means for a future RP4 — and what it cannot mean

A hypothetical RP4 primary would be: *ΔQLIKE of `B0+B1+index+index2` over
`B0+B1+index` on RV30, block-10 common-mask universe, frozen artifacts, virgin
window*. Getting there requires everything RP3 required: a frozen second-index
artifact fit on data available at freeze time, winner's-curse-halved sizing, its own
preregistration, and a sealed read on sessions no decision has seen. Nothing in this
campaign — and nothing in any future exploration of D/V — can shortcut that path.
The numbers above are leads. The only place a claim can be born is a sealed program.

## Hazards carried forward

- V is not virgin (it shaped RP2's published measurements); its role here is a
  disciplined out-of-fold check, not confirmation.
- V holds only ~80 sessions: the one-look is underpowered for effects of this size
  (the incumbent's own +0.00101 reads p 0.063 there).
- c1 inherits D3's post-selection optimism; c5's residual construction reuses the
  train fold that fit theta — both are reasons the RP4 path, not this document, is
  where belief gets earned.
