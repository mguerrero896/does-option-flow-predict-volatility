# Disabled Windows daily collection

This is a separate, target-blind collection task. It neither evaluates a model nor changes an existing research result. The setup does not download data, read provider credentials, start a scheduled task, or create the collection data directory.

## Contract

- Task name: `OptionsVolatility-Daily-Collection`.
- The task and its daily trigger are created with `Enabled=false` in the submitted XML. On-demand starts are also disabled. There is no enable-then-disable interval and no `RunNow` call.
- Nominal future schedule: once daily at 22:00 UTC. The existing XNYS calendar selects only the latest session whose official close plus 30 minutes has passed. Holidays, daylight saving time and early closes are handled by that calendar, not by a fixed New York closing hour.
- One UW full-tape ZIP and one bounded FMP one-minute response for each of AAPL, AMZN, META, MSFT, NVDA, TSLA, SPY and QQQ. No other provider endpoints, historical catch-up or automatic model runs are included.
- The ZIP receives the existing CRC and schema checks. Raw FMP responses and canonical normalized regular-session bars are retained. Missing bars are counted, never filled; acquisition success is not a claim of complete minute coverage or feature eligibility.
- Five total attempts per missing component per execution, with waits of 1, 2, 4 and 8 seconds. Successful components are verified by hash and reused. A failed component is recorded while the others continue. The next authorized execution still selects only the latest closed session; it does not backfill older missing dates.
- One nonblocking kernel lock per session and Windows `IgnoreNew` prevent overlapping collection. Manifests are atomic and immutable; changes to completed bytes fail closed. Numeric libraries are limited to two threads; jobs run sequentially.
- Free space below 100 GiB blocks new writes/download chunks. This collector never removes caches or licensed data.
- The existing acquisition module supplies the calendar, retry, root-boundary and hashing helpers. The canonical FMP provider/normalizer and ZIP validator are reused. The small root-aware stream and lock adapters do not alter their frozen modules or global roots.

## Privacy and future runtime

Machine configuration and submitted/registered XML are stored only under the excluded `private/` setup directory. They contain local executable paths and the local account SID, but no provider keys. The launcher pins its configuration and source files before doing any work. Its action never contains credentials.

On a future explicitly enabled run, a new data root is initialized with a marker and a protected ACL allowing only the configured account, local Administrators and SYSTEM. Existing unrelated directories are rejected. Logs, raw payloads and manifests remain under that private root. The launcher only inherits existing process/user/machine provider variables; it does not read an env file or configure passwords. Exceptions and public receipts never include response bodies, headers, credential values or full request URLs.

The task uses `InteractiveToken` and least privilege: collection requires that account to be logged in. Credential availability, provider entitlement, actual download success and unattended operation are **NO VERIFICABLE** in this disabled setup. No network probe or collection execution is used to claim otherwise. The future trigger and task would both need deliberate activation; this deliverable leaves both disabled.

Source-time timestamps remain a proxy, not proof of historical client availability. UW open-interest vintage is not inferred. Raw row quality beyond ZIP CRC/schema is not evaluated here. There are no RV objectives, feature panels, predictions or inferential results in this workflow. Existing scheduled tasks, frozen research artifacts and `phase9` are left unchanged.

## Commands

All commands run from the configured checkout with the existing Python 3.12 environment. No dependency installation is performed.

```powershell
uv run --offline --frozen --no-sync python -B -m pytest artifacts/rp4_daily_collector_code/test_collector.py -q -p no:cacheprovider --basetemp artifacts/rp4_daily_collector_setup/test_tmp
uv run --offline --frozen --no-sync ruff check artifacts/rp4_daily_collector_code
uv run --offline --frozen --no-sync ruff format --check artifacts/rp4_daily_collector_code
```

`register_disabled.ps1` takes explicit local repository, data-root, uv and Python-environment parameters. These machine paths and the full executed command are kept in the private execution receipt. The installer refuses an existing task of the same name or an existing collection root. If native registration is denied, it preserves the disabled XML and reports `NO_VERIFICABLE_NATIVE_REGISTRATION` with the actual error class, HRESULT and error identifier.

`launch.ps1 -DryRun` verifies configuration/source pins and performs only calendar planning. Its dry-run branch returns before data-root creation, ACL changes, credential access or network I/O. A clock override is allowed only for a collector dry-run, never collection.

## Evidence boundary

`public_receipt.json` and `public_manifest.json` describe the actual setup, test outcomes and artifact hashes. The private receipt preserves the complete machine commands and registration XML. No private paths, account identifiers, credentials or licensed data are included in the public projection.

`RESEARCH_ONLY`; `NOT INVESTMENT ADVICE`; `capital_go=false`.
