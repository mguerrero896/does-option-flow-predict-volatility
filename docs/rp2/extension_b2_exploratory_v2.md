# B2 exploratory campaign v2 — a learned index from the raw tape, against theta

**Label: EXPLORATORY_DIAGNOSTIC.** Authorized by the owner 2026-08-25 (decision 95),
run once by `scripts/rp2_b2_exploratory_v2.py` (extract → train → evaluate) on the
`rp2-v3-20260824-remeasure` panels and the block-1 tape inventory, D and V roles only
(the inventory ends at 2026-07-17 by construction — no sealed session exists in it).
Artifact: `artifacts/rp2_b2_exploratory_v2/results.json` (self-hash
`a27743a098fe66e9…`), bound to this document by
`tests/contract/test_b2_exploratory_v2_doc_matches_artifact.py`.

## The question

Campaign v1 searched recombinations of the twelve hand-crafted B2 aggregates and
found none that beat the frozen index. v2 asked the one axis v1 could not: **does the
raw full-tape event stream — the ~25 fields per option trade that the twelve
5-minute summaries compress away — carry rv30 information beyond theta?** A small
encoder (7,233 parameters: per-event MLP → masked attention pooling → scalar head;
capacity minimal by D2's lesson) was trained on the D-train fold only, over windows
of the last 30 minutes of events (≤256 events, 13 robust features each; 2,814
asset-session shards extracted from ~85 GB of tape). Its output — one learned scalar
per origin, hashed — entered the same CPU-deterministic harness as v1: anchor first,
one look at V (**disclosed as V's third exploratory look**: v1 spent the first two
windows' worth), BH q-values across the three registered candidates, the incumbent
`B0+B1+theta` as the bar.

## The anchor held — again

R0→R1 on D-test = **+0.001015**, wild p **0.0010**: the committed number, reproduced
by this campaign's own fits. On V the incumbent echoes at +0.001010 (p 0.063), as in
v1.

## Results — every registered candidate, both windows, both baselines

ΔQLIKE, session-clustered; wild-cluster p in parentheses; q = BH across the three V
contrasts against the incumbent.

| Candidate | D-test vs incumbent | V vs incumbent | q (V) | D-test vs base | V vs base |
| --- | --- | --- | --- | --- | --- |
| l1_learned_only | +0.00032 (0.229) | +0.00006 (0.852) | 0.852 | +0.00133 | +0.00107 |
| l2_learned_plus_theta | +0.00001 (0.967) | −0.00055 (0.068) | 0.103 | +0.00102 | +0.00046 |
| l3_full_stack | −0.00029 (0.145) | −0.00079 (0.009) | 0.028 | +0.00073 | +0.00022 |

## Verdict

**The raw-tape axis is closed, at this design point.** The learned index alone
matches theta out of sample but does not beat it (l1: +0.00006 against the incumbent,
noise). Stacking it **hurts**: l2 degrades the incumbent on V and l3 — the full stack
with v1's second index — is *significantly worse* (−0.00079, q 0.028). More capacity
over the same signal degrades out-of-sample skill: the exact conclusion the D2
diagnostic reached for trees, now replicated for a learned representation of the raw
stream. The twelve hand-crafted aggregates plus a linear compression appear to
capture what this tape, at this horizon, has to give.

Read together with v1: the frozen theta index has now survived **eight registered
challengers across two campaigns** (five recombinations, one learned representation,
two stackings). The strongest surviving lead for any future RP4 remains v1's
**second orthogonal linear index** — and v2 sharpens that lead's interpretation: the
second direction is in the *aggregates*, not in the raw stream the aggregates
compress.

## What this cannot mean

Nothing here is confirmatory, and a negative exploratory result does not "close" the
raw-tape axis for all designs — longer windows, other horizons, or pretraining
objectives were not in the registered list and remain unexplored. What is binding:
the RP3 seal, its closed two-test list, and the look counter at 0 are untouched, and
any future claim — positive or negative — about tape representations belongs to a
new preregistered program.

## Hazards carried forward

- V is not virgin and this was its third disclosed exploratory look; its ~80 sessions
  underpower effects of this size.
- The encoder is one design point (30-minute windows, 256 events, 7k parameters,
  MSE-on-residual objective); the negative is evidence about this point, not the axis.
- GPU training is not bit-reproducible; the learned index is frozen as a hashed
  artifact (`learned_index_sha256` in the results), and every contrast above is
  CPU-deterministic given it.
