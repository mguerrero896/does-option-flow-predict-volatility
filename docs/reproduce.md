# Reproduce public checks and figures

The public repository contains source code, aggregate results, registered protocols,
translated reports and provenance records. The commands below verify those public
materials. They do not fetch licensed observations, refit the scientific models or
read a prospective cohort.

## Clean environment and contracts

Use Python 3.12, Git and an existing installation of `uv`. Clone the repository,
enter its directory and install the committed dependency lock:

```sh
git clone https://github.com/mguerrero896/does-option-flow-predict-volatility.git
cd does-option-flow-predict-volatility
uv sync --frozen
git config --local core.hooksPath scripts/hooks
uv run --frozen python scripts/scan_public_secrets.py --check-hook
env -u MDS650_EVIDENCE_ROOT -u MDS650_EXTERNAL_ROOT -u MDS650_DATA_ROOT MDS650_PANEL_GUARD_MAY_SKIP=1 MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP=1 uv run --frozen pytest tests/contract tests/test_gated_history_contract.py tests/test_mirror_internal_docs_contract.py -q
uv run --frozen python scripts/scan_public_secrets.py --include-tags
```

Contract tests check artifact identities, scientific reporting, source timing,
archived evidence, translated numerical claims and internal Markdown links. Some
checks explicitly skip when their licensed oracle or optional training dependency
is unavailable; a skip is not evidence that the missing computation passed.
The `env` command uses the same public tier boundary as hosted CI and can be run
in Git Bash on Windows. The publication dry run below also isolates inherited
private evidence settings automatically; it records both declared opt-outs.

## Reports, hashes and database inputs

```sh
uv run --frozen python scripts/build_rp4_english_defense.py --check
uv run --frozen python -m scripts.build_rp4_v5_english
uv run --frozen python -m scripts.build_rp4_v5_public_receipt
uv run --frozen python scripts/verify_rp4_public_metadata.py
uv run --frozen pytest tests/contract/test_canonical_state_current.py -q
uv run --frozen python scripts/sync_supabase_catalog.py --rp4-v4 --dry-run
```

These checks read public files. The defense producer validates its claim matrix and
manifest; the v5 producer checks the complete translation against archived evidence;
the state contract checks generated status; the loader's dry run validates the three
fixed source hashes and 24/36/3 rows without contacting or writing the database.
The [database receipt](../artifacts/rp4_public_refresh/supabase_receipt.json) separately
records the actual authenticated write, full readback and anonymous read verification.

An archived original's hash identifies its historical bytes. Where private locators
required a public derivative, the [redaction record](../artifacts/rp4_public_refresh/archive_redactions.json)
stores separate original and public hashes. The original pin does not assert byte
equality with the derivative. The archive resolver and numerical contracts enforce
that distinction.
Historical publication-implementation and administrative sources remain private. Their expected
pins and explicit non-distribution are recorded; their bytes cannot be verified
from this clone. Every source selected for a numerical claim must still be present
and its value checked. A missing unregistered source fails the public contract.

## Regenerate research figures from saved CSVs

The [RP4 figure guide](figures/rp4/README.md) gives the CSV inputs, exact regeneration
command and translation receipt. Rendering uses existing producers and saved
aggregates; it does not recompute bootstrap inference or fit a model. Original
figures and their historical hashes are retained in the archive.

```sh
uv run --frozen --no-sync python docs/figures/rp4/reproduce_english.py --verify
uv run --frozen --no-sync python docs/figures/rp4/reproduce_english.py --render
```

The first command checks hashes without writing; the second regenerates six SVGs
from five CSVs. Optional PNG rendering uses the existing Sharp installation and
recorded fonts described in the figure guide.

The four new programme diagrams have versioned Archify JSON sources. With Node.js:

```sh
node docs/figures/public_refresh/reproduce.mjs --verify
```

This checks all 12 JSON/HTML/SVG hashes. Regeneration also requires the recorded
Archify installation and Chrome/Chromium, configured with `ARCHIFY_HOME`:

```sh
node docs/figures/public_refresh/reproduce.mjs --render
node docs/figures/public_refresh/reproduce.mjs --verify
```

See the [diagram guide](figures/public_refresh/README.md) for recorded renderer
versions and visual validation. Different browser versions can change rendered
bytes; inspect a difference before accepting a new manifest.

## Verify a publication candidate without remote writes

On a clean branch descending from `origin/main`, use an output directory outside
the clone. Git Bash can run the mirror's verification-only entry point:

```sh
bash scripts/publish_mirror.sh --dry-run --output-dir ../public-verification
```

The command runs the public contracts, full-history exclusion check, secret scan
including tags and Markdown language screening, then writes logs and a receipt.
It exits before publication operations. Use the recorded commit and logs to state
which candidate was checked; a check on an earlier commit does not validate later edits.

## What requires licensed inputs

Reconstructing feature panels, per-origin forecasts and complete model fits requires
the original provider observations, exact calendars, source availability fields,
frozen input hashes and the recorded execution environment. Public aggregate losses
cannot reconstruct those observations. Access to the licensed bucket remains
private and managed under the [data access policy](../data/DATA_ACCESS.md).

The [historical execution guide](rp4/OPERATING_GUIDE.md) records the original commands and
their portability limits. Relocating and translating documents does not constitute
an identical rerun of a closed registered execution. Prospective cohorts and their
read authorizations remain governed by their own protocols.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
