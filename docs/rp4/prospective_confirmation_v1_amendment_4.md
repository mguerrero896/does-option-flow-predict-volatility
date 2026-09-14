# Prospective v4 replication — amendment 4 to registration v1

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

**Local seal: 2026-09-13T23:45:22.011930+00:00.** Owner-authorised on 2026-09-14, before any late acquisition or prospective replication read. This is a local record of bytes and sequence, without an independent third-party timestamp. The [receipt](prospective_confirmation_v1_amendment_4_receipt.json) and [sidecar](prospective_confirmation_v1_amendment_4.sha256) bind this document and its antecedents. No prospective targets, losses or results were read to prepare it.

## Complete seal chain

| Document | UTC seal | Document SHA-256 |
|---|---|---|
| [v1](prospective_confirmation_v1.md) | 2026-09-08T04:24:01.918499+00:00 | `317530c37d2785bb0ce0bfd6a947fc034c78a02bbd5bb102fd17efe8f91b977d` |
| [Amendment 1](prospective_confirmation_v1_amendment_1.md) | 2026-09-08T04:31:58.752153+00:00 | `036f81894975a1e452fb2817c7f3989ed89dd6fe601a9378587d70559d3c7bb3` |
| [Amendment 2](prospective_confirmation_v1_amendment_2.md) | 2026-09-08T05:27:15.316335+00:00 | `b545c36faa4a48764a3433b008d859780a2116f5275a8553b95765d3a2d50cf9` |
| [Amendment 3](prospective_confirmation_v1_amendment_3.md) | 2026-09-08T06:56:21.897094+00:00 | `4981a6ff9c40f498b192628df9c20db7a5e4877468c1ca0587fd472dc31401d6` |

These are the literal historical seals of the preserved original documents, not the hashes of their English translations. All earlier documents, receipts and sidecars remain intact. The new receipt separately records the current repository bytes and the preserved originals, including the amendment 3 context addendum.

## Incident record

The incident report records five failed scheduled executions at 10:00 Australia/Sydney on **2026-09-09, 2026-09-10, 2026-09-11, 2026-09-12 and 2026-09-13**, reported with launcher exit code **2**, `LAUNCHER_FAILED`. The reported root cause was `SOURCE_HASH_MISMATCH`: local commit `20d2e80f`, dated 2026-09-08T08:18Z, changed the pinned `pyproject.toml` approximately ten hours after the collector setup recorded at 2026-09-07T22:07Z. That setup timestamp is distinct from the v1 scientific seal above. The drift concerned an import-sorting configuration addition, but the launcher's byte-integrity gate correctly refuses any changed pin.

**Evidence boundary:** the task-event export retained at this amendment contains only 11–13 September and records native return code **2147942402 (0x80070002)**, not literal launcher exit 2. The five-date/code-2 account and reproduction of the hash-mismatch cause come from the incident report; they are not independently reconstructed from those three native event records. The retained native log begins on 2026-09-10T09:05:25.8004236Z. Separately, the task-info observation reports last run 2026-09-13T00:00:01Z with result 2, supporting that last launcher-level code. The discrepancy between event and task-info codes remains explicit.

The registered `pyproject.toml` bytes were restored with SHA-256 `f7a62af5dcb1a35ce4c4f52df305ed0f574a0fff7806aba4a07f957fd6fb4b56`; the substituted bytes were preserved in `pyproject.public_checkout.20d2e80f.bak`. All **16** registered source pins and the registered configuration hash were verified during this amendment. A second reported blocker, `DAILY_INSUFFICIENT_FREE_SPACE`, occurred with free disk space below the registered **100 GiB** minimum. The initial manual operation records all nine components missing and `PARTIAL`; the incident report identifies the disk cause. Authorised disk release was recorded separately. This amendment authorises no deletion.

The subsequent unchanged registered launcher acquired market session **2026-09-11** with `PASS`, nine components, no missing components and zero target reads or model fits in its metadata. Acquisition success is not a prospective scientific result or a final eligibility verdict. Sessions **2026-09-08, 2026-09-09 and 2026-09-10 were not acquired on their scheduled days**.

Custody is identified by filenames, without private locations: the setup `execution_receipt.json` and its [public receipt](../../artifacts/rp4_daily_collector_setup/public_receipt.json); `machine_config.json`; the retained `task_events.json` export and `task_info_observation.json`; `pyproject.public_checkout.20d2e80f.bak`; `DELETION_RECEIPT_20260914.json`; launcher logs `20260913T1949395245221Z.log` and `20260913T2002528680332Z.log`; operation receipts `20260913T195233695400Z.json` and `20260913T200553703847Z.json`; session manifest `2026-09-11.json`; and the new operational `incident_20260909_20260913.json`. The [public incident evidence](prospective_confirmation_v1_amendment_4_incident.json) retains observed metadata, source hashes and the distinction between incident-report testimony and direct checks. Private custody files are not distributed; their hashes are provenance commitments, not independently accessible public evidence.

## Late acquisition rule (owner-authorised 2026-09-14)

The owner authorises one late acquisition procedure for **2026-09-08, 2026-09-09 and 2026-09-10**, derived by copying the registered `collector.py`. It uses the same registered configuration, components, provider sources, per-component SHA-256 integrity checks and manifest format. Each late session manifest additionally records `acquired_late=true` and its actual `acquired_at_utc`. The registered collector and its 16 pinned files remain unchanged. The separate procedure and its dry-run receipt are retained locally; they are operational custody, not a replacement scientific specification.

No eligibility rule, common mask, estimand, test, threshold, model, source-time cutoff or reading calendar changes. No targets or losses may be inspected during acquisition. If a component is unavailable from its source or incomplete, record the session as **`UNAVAILABLE_LATE`**, preserve the failed acquisition evidence and exclude it under the unchanged completeness rules. **No imputation, replacement source or substitute session is permitted.** One-use custody prevents replaying the late procedure for a session whose acquisition attempt has already started.

Complete eligible late sessions count chronologically within the first **20/40/335** only when this amendment was sealed **before their acquisition and before any prospective replication read**. The existing 20-session primary, conditional 40-session stability read, final cumulative 335-session read and once-only A/B/C/D schedule remain governed by amendments 1–3; this amendment adds no read. While late acquisition is pending, counting starts with 2026-09-11. No later inclusion may rewrite an already-read cohort or its verdict.

Acquisition occurs after those sessions' market closes. Under the registered **source-time proxy**, the timing input is the tape timestamp rather than the download time; late downloading therefore does not change the registered PIT rule or cutoff. **This is a limitation of the proxy, not a guarantee of contemporaneous receipt, an unchanged provider vintage or execution availability.** Original receipt-time availability cannot be recovered by a late download.

Before **each** session, a fresh disk check must show at least **105 GiB** free and at least the registered **100 GiB** remaining after allowing **1.7 GB (1,700,000,000 bytes)** for that session. This estimate is not a cap on actual size; the registered free-space checks still apply. If either condition fails, do not start acquisition: record **`PENDING_DISK_SPACE`**. An execution record, if subsequently needed, is a **new** `prospective_confirmation_v1_amendment_4_execution_receipt.json`; the seal receipt is never rewritten. At sealing, `late_acquisition_executed=false`.

## Limits

Late acquisition is a declared deviation from acquiring the latest closed session every day. It supplies neither evidence of historical execution availability nor prospective confirmation. Power assumptions, thresholds, eligibility, the registered hierarchy and all prior verdict-retention rules remain unchanged. No prospective replication read has occurred, according to the owner-authorised incident record; direct checks here cover only collection metadata and file integrity, not every person's knowledge. The local seal is not an independent timestamp.
