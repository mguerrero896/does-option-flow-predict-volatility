# Extension — the B2 autopsy: where does the information die?

**Status:** `EXECUTED — 2026-08-24` · label `EXPLORATORY_DIAGNOSTIC` · role **D only**
**Artifact:** `artifacts/rp2_b2_autopsy/results.json`
**Script:** `scripts/rp2_b2_autopsy_extension.py`
**Run:** panels of `rp2-v3-20260824-remeasure`, same partition, common mask and 60/40
chronological cut as Block 10, so every delta lands next to a published number.

EXPLORATORY. Nothing here is a confirmatory result; no sealed cohort was read. The
diagnostics were run once, on development data only, to decide what the RP3
preregistration should freeze — and that decision is recorded before any virgin data is
touched.

---

## The question

Block 7's DML says the B2 flow block carries information beyond B0+B1. Block 10's
remeasured ladder says only one of the three frozen families converts any of it into
forecast improvement (`lightgbm_qlike` ΔB2|B1 = +0.00108; `gamma_glm` −0.00002). An
information set that is real to a debiased estimator but useless to two of three
forecasters has died somewhere between the panel and the loss. This extension walks the
chain one link at a time; each diagnostic is built so its outcome discards one hypothesis.

## Design

All three diagnostics share one construction: the residual of log-RV30 given B0+B1 is
estimated on training rows only (closed-form ridge, penalty 10⁻³ per row), and the twelve
B2 columns are compressed into a **single index** fitted to that residual. The final model
sees `[B0+B1, index]` — one extra column instead of twelve.

- **D1 — estimation cost.** The index is linear (ridge coefficients θ). One degree of
  freedom cannot overfit; if D1 converts where twelve raw columns did not, the killer was
  estimation cost, and the remedy is dimension reduction.
- **D2 — non-linearity.** Same residual, but the index is a small deterministic LightGBM
  (15 leaves, 120 rounds, pinned seed). If D2 beats D1, the information is non-linear in
  B2 and a linear compression throws it away.
- **D3 — localisation.** The per-session gain of the best candidate is correlated with
  the session's ex-ante flow state (`b2_5m_premium`). Concentration in high-flow sessions
  means the path forward is conditioning on events, not averaging over the tape.

Inference is Block 10's own machinery: session-aggregated QLIKE deltas,
wild-cluster/block-bootstrap intervals (seed 650), the common evaluation mask and its
digest recorded in the artifact.

## Results

### D1 and D2 — six contrasts, role D

| Family | Index | ΔQLIKE | 95% CI | p (wild cluster) | MDE |
|---|---|---|---|---|---|
| `gamma_glm` | linear | +0.00012 | [−0.00021, +0.00046] | 0.5677 | 0.00049 |
| `gamma_glm` | tree | −0.00550 | [−0.00822, −0.00310] | 0.0005 | 0.00374 |
| `ridge_log` | linear | +0.00018 | [−0.00006, +0.00043] | 0.2344 | 0.00036 |
| `ridge_log` | tree | −0.00347 | [−0.00561, −0.00157] | 0.0005 | 0.00299 |
| `lightgbm_qlike` | linear | +0.00101 | [+0.00032, +0.00176] | 0.0010 | 0.00105 |
| `lightgbm_qlike` | tree | −0.00183 | [−0.00341, −0.00034] | 0.0255 | 0.00215 |

Three findings, one per link of the chain:

1. **The linear index reproduces the tree's increment.** For `lightgbm_qlike`, one
   linear column recovers +0.00101 [+0.00032, +0.00176] against the +0.00108 the
   published remeasure obtained from all twelve B2 columns. The information the boosted
   family extracts from B2 *is* a linear index of B2 — the tree's increment carries no
   interaction structure a single θ cannot express.
2. **The GLMs do not move with one parameter either.** `gamma_glm` and `ridge_log` gain
   nothing from the linear index (+0.00012 and +0.00018, both intervals straddling zero).
   Estimation cost is therefore *not* what killed them: give them the information for the
   price of one degree of freedom and they still cannot use it. Their failure is
   structural — the increment lives in a part of the conditional distribution their link
   and loss do not reward — which is why RP3's primary test names `lightgbm_qlike` alone
   rather than pretending three families were ever in play.
3. **Extra flexibility destroys instantly.** The tree index is *negative* in all three
   families, in two of them by several times the published effect. A low-capacity
   non-linear compressor fitted to the same residual on the same rows overfits at once.
   The linear index is not a convenience; it is the only compression that survived.

### D3 — where the benefit lives

For the best candidate (`lightgbm_qlike` + linear index), the session-level gain
correlates with ex-ante flow at Spearman ρ = +0.111, and the mean gain in the top
flow quintile is **+0.00286** against **+0.00054** in the remaining sessions — a
roughly fivefold concentration where the options tape is actually active.

## What this feeds into the RP3 preregistration

- **The frozen form of the primary test.** ΔB2|B1 on RV60 in `lightgbm_qlike`, with B2
  entering as **one linear index whose θ is frozen at training time** — because D1 shows
  the linear index is sufficient and D2 shows anything richer self-destructs.
- **One family, declared as such.** The GLM nulls are structural redundancy, not missing
  power; carrying them into the sealed read would spend multiplicity on tests known to be
  dead.
- **An honest power note.** Even the winning contrast (+0.00101) sits at its own MDE
  (0.00105); the preregistered expected effect is halved for the winner's curse.
- **A recorded lead, not a third test.** The flow-quintile concentration suggests
  event-conditioned evaluation, but the RP3 test list is closed at two. D3 is logged here
  as the exploratory basis for any *future* programme, nothing else.

The selection history that led here — 36 targets swept in extension 1, `y_rv_60` the only
RV target alive in both roles — is declared in
`artifacts/rp2_ext1_mechanism_utility/mechanism_utility.json` and is part of why the
expected effect is discounted, not hidden.
