# Verification notebooks

Two self-contained Jupyter notebooks recompute the report's published results from the
aggregate files in this repository. They fit no model, read no licensed data and need no
account or API key: every input CSV is embedded in the notebook and checked by SHA-256
against the files under `artifacts/` before any calculation.

| Notebook | Reading time | What it checks | Colab |
|---|---|---|---|
| [`quick_verification.ipynb`](quick_verification.ipynb) | about 10 minutes | The headline tables of the report: primary 15-minute contrasts, the final-window decision, reference models and complementary errors, plus a claims ledger that compares every printed value with the recomputed one. | [Open](https://colab.research.google.com/drive/1k9eTbP5fv7LlWVEyP1Kydbonzif52rZC) |
| [`extended_walkthrough.ipynb`](extended_walkthrough.ipynb) | about 30 minutes | Everything above, plus coverage, session-level distributions, subset and regime diagnostics, inference sensitivity, availability cutoffs, the placebo, a second standard-library implementation, the regenerated report figures and a 443-row claims ledger. | [Open](https://colab.research.google.com/drive/1XhEt3VMt_wj7br8PRf3j88DTXFQhJ_rw) |

Run either notebook from the top (`Runtime → Restart session and run all` in Colab, or
`Kernel → Restart & Run All` in Jupyter). Each ends with an execution receipt that lists
the input fingerprints, the recomputed contrasts and the software versions. A ledger row
that does not match the report stops the notebook.

The embedded inputs correspond to the repository release cited in the report; the
contract test `tests/contract/test_verification_notebooks.py` fails if any embedded
fingerprint stops matching the repository file it names.

What the notebooks cannot do: rebuild predictors, refit models or rerun bootstrap
inference. Those steps use licensed minute-level data described in
[`docs/reproduce.md`](../docs/reproduce.md) and [`data/DATA_ACCESS.md`](../data/DATA_ACCESS.md).

## Retained legacy notebooks

`canonical_rv30_defense.ipynb` and `research_pipeline.ipynb` are earlier, Spanish-language
notebooks from the thirty-minute evaluation of a previous research programme. They are kept
byte-for-byte because archived defence documents under `docs/archive/` link to them and the
public archive map records their identities. Both are superseded by the two notebooks above
and are not part of the current evidence; do not use them to check the report.
