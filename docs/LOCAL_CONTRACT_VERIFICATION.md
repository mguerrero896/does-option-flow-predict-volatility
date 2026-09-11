# Completing the public report's omitted contracts locally

A clean public clone cannot inspect excluded licensed files. Its omissions are
not passes. The matching local verification runs the exact omitted node IDs,
with no skip exemptions, and fails unless every selected test passes.

The 69 omissions in the 2026-09-12 public report comprise 56 historical evidence
contracts, 11 RP2 panel identity/feature contracts, one RP4 event transcription
contract and one UW operational snapshot freshness contract.

## Configuration

Set the following directories in the local process environment; do not publish
their values or copy licensed inputs into the public checkout:

| Variable | Required contents |
| --- | --- |
| `MDS650_EVIDENCE_ROOT` | Historical `artifacts/` evidence tree used by the 56 contracts. |
| `MDS650_RP2_PANEL_ROOT` | Four `artifacts/rp2_block*/` panels matching the exact sizes and SHA-256 in `artifacts/rp2_panel_pointers.json`. It may differ from the historical evidence root. |
| `MDS650_DATA_ROOT` | Existing Massive cache, Phase5 stability inputs and Phase6 source bars. |
| `MDS650_EXTERNAL_ROOT` | Operational `uw_latency/sessions/` store. |
| `MDS650_REPO_ROOT` | Preserved Git repository containing the source commit bound to the Phase5 method freeze. |
| `MDS650_RP4_AUDIT_ROOT` | The two `artifacts/rp4_market_audit/` CSVs whose exact hashes are recorded by the historical defense evidence. |

After inspecting the selected contracts' access scope, run:

```sh
uv run --frozen python scripts/verify_omitted_contracts.py --selection-junit ../public-verification/contracts.xml --expected-count 69 --output-dir ../local-contract-verification
```

The output directory must be new and outside the repository. The receipt binds
the input JUnit hash, exact node IDs, tested commit and dirty-tree status. The
full private log stays local. Exit zero requires exact test coverage and zero
failures, errors or skips. This is not a full scientific refit or all Tier2 tests.
No Supabase request or scheduled task is invoked by this scoped command.

## Corrections exposed by execution

The RP4 test previously searched only inside the checkout. It now supports the
explicit external root and verifies both source hashes before reading CSV rows.
Supplying a missing or altered input fails; it does not become a skip.

The UW test exposed genuinely stale operational authority. V4 recorded seven
reconciliations; the same session window now has thirteen. V5, published as a new
dated artifact, includes the later reconciliations without overwriting v4. Here
`as_of_date=2026-09-02` bounds **session dates**, not the time at which a later
reconciliation became available. V5 is a September12 observation of that closed
historical window, not a reconstruction of knowledge available on September2.
The original report's six-clean-session measurements remain explicitly historical.
The freshness test still compares regenerated values and inventory exactly; no
hash-only substitute or relaxed tolerance was introduced.

The rerun checks already-produced historical outputs and operational latency;
it does not acquire data, refit models, consume a one-shot claim or access a new
sealed cohort. Public omission counts may remain unchanged on machines without
licensed inputs even when the corresponding local checks are complete.
