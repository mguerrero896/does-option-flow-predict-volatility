# RP4 — reproduction and local verification runbook

**English translation. Historical seals refer to the preserved original bytes.**

The current scientific reading is [RESULTADO_FINAL.md](RESULTADO_FINAL.md). The closeout is v4: a sequential advantage at RV15 in the linear family, not a uniform advantage in both families or an independent replication. This document changes no specifications, data, models, results or authorisations.

## 1. Three different operations

| Operation | What it demonstrates | What it does not do |
| --- | --- | --- |
| Verify the public copy | Byte equality against the pins of this closeout | Does not validate absent licensed data or recalculate statistics |
| Verify local custody | The preceding checks plus hashes of private results and logs cited by six B2/B3 receipts | Does not revisit every component, load panels or fit models |
| Rerun producers with originals | Historical materialisation and execution procedure, subject to original roots and receipts | Does not turn reused sessions into independent evidence |

A complete rerun from scratch **was not performed in this review: UNVERIFIABLE**. A copy with sanitised paths or names does not by itself replace the hash-pinned originals. Evaluation supervisors have no `--output-root` option: their roots come from the specification. Do not edit those roots, hashes or receipts to force a rerun.

## 2. Local configuration without publishing paths or credentials

Run from the original checkout root. `RP4_PYTHON_ENV` must be configured locally with the path of the existing environment; this document neither installs packages, downloads data nor displays its value. UW/FMP originals, rates, dividends, events, panels and receipts require local access under the relevant licences. Do not copy keys or licensed files into the repository.

```powershell
$repositoryRoot = (Get-Location).Path
if (-not $env:RP4_PYTHON_ENV) { throw 'Configure RP4_PYTHON_ENV locally first' }
$env:UV_PROJECT_ENVIRONMENT = $env:RP4_PYTHON_ENV
$env:PYTHONPATH = @(
    $repositoryRoot
    (Join-Path $repositoryRoot 'src')
    (Join-Path $repositoryRoot 'scripts')
    (Join-Path $repositoryRoot 'artifacts/rp4_code')
    (Join-Path $repositoryRoot 'artifacts/rp4_v2_code')
    (Join-Path $repositoryRoot 'artifacts/rp4_v3_code')
) -join [IO.Path]::PathSeparator
$env:MYPYPATH = $env:PYTHONPATH
$env:PYTHONIOENCODING = 'utf-8'
$env:OMP_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
```

The closed environment records Python 3.12.12; LightGBM 4.7.0, NumPy 2.5.2, pandas 3.0.5, Polars 1.44.1, PyArrow 25.0.1 and SciPy 1.18.0. The expected lockfile is `960c8a2638cdf39be44acb6d06b0e355eceab4e6658357f089f2b9aa159d61d0`. Source: [v3 release](../../artifacts/rp4_v3_a2/evaluation_release.json) and [v4 RV15 release](../../artifacts/rp4_v4_a2/evaluation_release_rv15.json). An absent environment is not remedied by updating those dependencies.

## 3. Gates without models or inference

These new audit commands are read-only and use only the standard library. Public mode explicitly omits hashes of files outside the checkout; local mode requires the originals but only reads their bytes. Output aliases avoid displaying their paths. A byte change produces exit 1. These gates were verified in the original closeout checkout. Receipts contain original roots: moving or sanitising a copy requires a separate check of the path and hash map. This gate does not certify that portability.

```powershell
uv run --offline --frozen --no-sync python -B artifacts/rp4_cleanup_review/inventory_review.py --verify-public
if ($LASTEXITCODE -ne 0) { throw 'Public custody check failed' }
uv run --offline --frozen --no-sync python -B artifacts/rp4_cleanup_review/inventory_review.py --verify-licensed
if ($LASTEXITCODE -ne 0) { throw 'Local custody check failed' }
```

Verified in this closeout: 140 public checks and 192 checks including private results/logs, both with exit 0. These are not necessarily 192 distinct files: each receipt checks its dependencies again. The six receipts, their releases, code, results and logs are pinned, together with the documents/CSVs listed in `PINS`. This gate does not verify the complete checkpoint graph or the intrinsic integrity of the data.

The tests for this verifier use synthetic metadata fixtures:

```powershell
uv run --offline --frozen --no-sync python -B -m pytest -q -p no:cacheprovider artifacts/rp4_cleanup_review/test_inventory_review.py
uv run --offline --frozen --no-sync ruff check artifacts/rp4_cleanup_review/inventory_review.py artifacts/rp4_cleanup_review/test_inventory_review.py
uv run --offline --frozen --no-sync ruff format --check artifacts/rp4_cleanup_review/inventory_review.py artifacts/rp4_cleanup_review/test_inventory_review.py
uv run --offline --frozen --no-sync python -B -m mypy --explicit-package-bases --follow-imports=silent artifacts/rp4_cleanup_review/inventory_review.py artifacts/rp4_cleanup_review/test_inventory_review.py
```

Do not use `--aggregate-only` as a hash gate: although it does not fit models, it recalculates inference. Nor should a supervisor with a missing receipt be used as a harmless verifier: it can initiate fits.

## 4. Historical execution commands

The following commands retain the original technical module namespace, as permitted by the publication contract. They are existing supervisor commands, **not executed during this review**. The base history is retained; this runbook does not require migrating it or creating another publication destination. Licensed originals and their roots remain separate requirements.

### v3, RV30

The effective panel requires gamma materialisation, comparison by keys and empty-window recoding. The [A2 receipt](../../artifacts/rp4_v3_a2/receipt.json) retains the executed commands, exits 0 and hashes for those three operations. The local v3 root is the original `data_root` value in the effective specification; it can be read into a variable without printing it. Do not substitute the earlier candidate panel or the panel before recoding.

Before the supervisor, the historical A2 sequence was as follows. Aliases are resolved from original JSON files and are not printed. The first two programs reject an already completed output; do not delete their manifests to make them pass. The gamma producer also writes its comparisons by key; the second command attributes only the candidate dividend difference.

```powershell
$v3Root = (Get-Content artifacts/rp4_v3_a1/specification.json -Raw | ConvertFrom-Json).data_root
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_code/materialize_gamma.py --spec artifacts/rp4_v3_a1/specification.json --spec-sha256 49b625a4dbca7b725a6b38defc25e76109be7b280d711355a55ce97a7443048b --output-root $v3Root --workers 4
if ($LASTEXITCODE -ne 0) { throw 'Gamma materialisation failed or is already complete' }
$comparisonScript = Join-Path $v3Root 'operations/audit_candidate_carry.py'
if ((Get-FileHash $comparisonScript -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'dccf6d542ef261e982124f22223148d4a8975899927f35c9e95bf5db2b399ace') { throw 'The original comparator changed' }
uv run --offline --frozen --no-sync python -B $comparisonScript
if ($LASTEXITCODE -ne 0) { throw 'Gamma comparison failed or is already complete' }
uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_code/empty_windows.py --spec-sha256 930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5
if ($LASTEXITCODE -ne 0) { throw 'Empty-window recoding failed' }
```

Historical exits: 0, 0 and 0. Gamma producer SHA-256 `2f59184b5a36b301252bb11eaf779c8128cef0f45266368f44b1a7d35f3644a3`; recoder SHA-256 `42c5bdc76fe1432a9d0fa2517ac157d4c02237da1ae8e0b331d1c960203564a5`. The comparator has a [custody copy](../../artifacts/rp4_v3_a2/audit_candidate_carry.py), but its historical command uses the local original and depends on its pinned inputs: execution from an isolated public distribution is **UNVERIFIABLE**. Do not invoke `--register`: registration already exists and its times/hashes are immutable.

```powershell
$v3Hash = '930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5'
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v3_code.execute --spec-sha256 $v3Hash --prepare-only
if ($LASTEXITCODE -ne 0) { throw 'Preflight v3 failed' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v3_code.execute --spec-sha256 $v3Hash --window primary
if ($LASTEXITCODE -ne 0) { throw 'Primary v3 failed' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v3_code.execute --spec-sha256 $v3Hash --window confirmation
if ($LASTEXITCODE -ne 0) { throw 'Confirmation v3 failed' }
```

The original supervisor fixes **4 shards × 4 threads**. With a valid final `COMPLETE` receipt it compares hashes and returns `WINDOW_ALREADY_COMPLETE`; it does not create a new execution. Without a final receipt, it resumes valid components and calculates outstanding work. Do not delete receipts, components or locks to force the fitting path.

The original v3 closeout retains failures in the jump secondary and adverse MZ recalibration. The [final secondary closeout](results_v3_revision2.md) documents separate numerical passes and the combined 419-session result; that result is not obtained by simply rerunning the v3 supervisor. Its [addenda](v3_secondary_implementation_addendum_v1.md) and [Newton resolution](v3_secondary_newton_addendum_v1.md) remain the references for those separate producers; original failures are never silently replaced.

### v4, primary RV15 and secondary RV5

The v3 panel and mask are inherited, with targets `rv_15` and `rv_5` constructed by keys. The fixed order is primary RV15, confirmation RV15, primary RV5, confirmation RV5. The 30-minute time endpoints are retained for conservative purging; the mask does not change by horizon.

The [A2 v4 receipt](../../artifacts/rp4_v4_a2/receipt.json) retains the original target-preparation exit 2 and its pinned resolution: it must not be described as an original passing preflight. The resolution distinguishes the six finiteness discrepancies outside the mask and does not alter eligible finite values.

The target and resolution sequence precedes `--prepare-only`. The original local receipt `operations/targets_stage_receipt.json`, under the v4 root, has SHA-256 `055d9b432a1765acf22ca78a5dc3ad476fd9118c6afb98c07cdf09edb5ade4b2`. It also retains two initial attempts with exit 1; the following command is the final producer version, which wrote the sidecar with exit 2, not 0.

```powershell
$v4Root = (Get-Content artifacts/rp4_v4_a1/specification.json -Raw | ConvertFrom-Json).data_root
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.materialize_targets --spec artifacts/rp4_v4_a1/specification.json --spec-sha256 0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04 --producer-sha256 8c6f9acc1dd3d995bea1ca75456c8fda6d4b6da1dc0b734dfbc23917b1265ce6 --output-root $v4Root --workers 4
# Historical record: exit 2. This does not authorise continuing after any new error.
if ($LASTEXITCODE -ne 2) { throw 'State differs from the investigated historical materialisation' }
$targetManifest = Join-Path $v4Root 'targets/manifest.json'
if ((Get-FileHash $targetManifest -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'ae4c1e7b104c5f2cee2402ded5d0515e04e5264759bf70f0e1098432806c8316') { throw 'Manifest differs from the investigated one' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_a2.resolve_target_mask --manifest-sha256 ae4c1e7b104c5f2cee2402ded5d0515e04e5264759bf70f0e1098432806c8316
if ($LASTEXITCODE -ne 0) { throw 'Target resolution is incomplete' }
```

The historical resolution finished with 0; its producer has SHA-256 `093e1906df0b3e098c3c6981c7762b39b7b84e03d916e108cd11e23ded1c898f`. Materialisation and resolution write new files and their metadata include timestamps: these commands do not promise to recreate the same manifest byte for byte from scratch. Historical reproduction requires the preserved originals; pins are not replaced to hide that difference. Both A2 stages use four workers in their historical commands and were not executed during this review.

```powershell
$v4Hash = '0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04'
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 15 --prepare-only
if ($LASTEXITCODE -ne 0) { throw 'Preflight RV15 failed' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 5 --prepare-only
if ($LASTEXITCODE -ne 0) { throw 'Preflight RV5 failed' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 15 --window primary
if ($LASTEXITCODE -ne 0) { throw 'Primary RV15 failed' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 15 --window confirmation
if ($LASTEXITCODE -ne 0) { throw 'Confirmation RV15 failed' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 5 --window primary
if ($LASTEXITCODE -ne 0) { throw 'Primary RV5 failed' }
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_v4_code.execute --spec-sha256 $v4Hash --horizon 5 --window confirmation
if ($LASTEXITCODE -ne 0) { throw 'Confirmation RV5 failed' }
```

The supervisor fixes **8 shards × 4 threads, at most 32 model threads**, and a global lock. The two-thread limit for the documentation gate does not change that historical contract. Do not execute fits with a two-thread budget assuming the variables above automatically reduce the supervisor. Complete receipts are idempotent; an incomplete closeout is not restarted by deleting evidence. V4 does not fit MZ, quantiles or jump classifiers.

## 5. Expected pins and observed timings

| File / alias | Expected SHA-256 |
| --- | --- |
| Effective v3 specification | `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5` |
| v3 release | `5e3046af023c9f41380307d62537aa4e8fc7514b23d51a95ea1f960ee23fe5bb` |
| Effective v3 panel, local original | `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637` |
| v4 specification | `0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04` |
| RV15 release | `7b5499579a66a468f040966d22824501ec1c65c29fefb848b40366bfd1f2351a` |
| RV5 release | `efeb22b33d992d453a4d766c93b5434e4f3f73271f350b50268a8289c365b08d` |
| v4 target panel, local original | `b2357a10a8a4955499e94b576b7853129e957ad70702da09bebbc9b6befd35db` |
| v4 target resolution | `05ff5f4b8127238dc9fb8371e530c12a1d2bbf23c30ef1363edf0f829b87722f` |
| timing.csv | `b23fcdcc6ffcabb088176e678a95829ea255b9db148d47fe448958112658e483` |

The panel hashes in this table come from the releases: the documentary gate does not reread their contents. The supervisor preflight does check them before permitting fits.

| v4 execution | Observed seconds | Minutes, seconds / 60 |
| --- | ---: | ---: |
| RV15 primary | 2940.2563865 | 49.0043 |
| RV15 confirmation | 517.0510889 | 8.6175 |
| RV5 primary | 3121.5861441 | 52.0264 |
| RV5 confirmation | 487.3992208 | 8.1233 |

Source: [timing.csv](../../artifacts/rp4_v4_b4/timing.csv), four rows from Windows 11, 32 logical CPUs and 66,184,798,208 bytes of physical memory. These are evaluation/aggregation times for those executions, not download or complete reconstruction times. They do not guarantee timings on another machine. The total observed v3 time is absent from that CSV and its B2/B3 receipts: **UNVERIFIABLE** in this review; it is not inferred from modification times.

## 6. Coefficients by horizon

The [aggregate B2 coefficient CSV](../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv) contains 1,518 rows, with horizons of 30, 15 and 5 minutes and both windows; its SHA-256 is `150fdf4398072496ef64547df580053907a117921d2c214f9b3c82446254e9be`. The [presence-indicator CSV](../../artifacts/rp4_closeout_audit/b2_presence_coefficient_summary.csv) contains 654 rows and has SHA-256 `9d4fc01b00af2ea25ab34b44276c481cf963be83edcc8f4b31ad114e1e6ab5e7`. Both are verified by the preceding gate.

```powershell
Import-Csv artifacts/rp4_closeout_audit/b2_coefficient_summary.csv |
    Where-Object { $_.horizon_minutes -eq '15' -and $_.window -eq 'primary' } |
    Select-Object column,kind,N_sessions,mean,absolute_mean,active_sessions
Get-FileHash artifacts/rp4_closeout_audit/b2_coefficient_summary.csv -Algorithm SHA256
```

These coefficients apply to transformed inputs, standardised only on training data and bounded at ±5 deviations, before smearing and output bounds. `absolute_mean` is the mean absolute value, not the absolute value of the mean. A dropped column has a coded zero contribution, not an estimated null effect. These are not an ablation, causal importance or portfolio exposure. The granular session-level CSV remains outside the public projection.

The closed extraction was produced with `uv run --offline --frozen --no-sync python -B artifacts/rp4_closeout_audit_code/audit_closed.py` (exit 0, 23.6588847 seconds recorded). It was not repeated here. Its writer is immutable and contains time metadata: invoking it again on existing output is not equivalent to a guaranteed clean reconstruction. Source: [extraction receipt](../../artifacts/rp4_closeout_audit/public_checks_receipt.json).

## 7. Preservation and closeout

The navigation/cleanup review is in [CLEANUP_REVIEW.md](CLEANUP_REVIEW.md). The [inventory](../../artifacts/rp4_cleanup_review/inventory.json) is a bounded snapshot, not deletion authorisation. The [receipt for this review](../../artifacts/rp4_cleanup_review/receipt.json) contains executed commands, exit codes, tests, scope and hashes. No data were published and no tasks were activated. `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE` and `capital_go=false` are retained.

## Gate before any publication

Before uploading a branch to the public repository, run `tests/test_gated_history_contract.py`, `tests/contract` and `scripts/scan_public_secrets.py --include-tags` in a clean worktree of that branch. The incident on 2026-09-08 (`INCIDENT_20260908_fit_selection.md`) occurred because the local gate omitted the first check.
