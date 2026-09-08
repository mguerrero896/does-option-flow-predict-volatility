## Reading the complete result

**English translation. Historical seals refer to the preserved original bytes.**

The RP4 execution is complete; the robust global hierarchy is not demonstrated. In the primary window B1 improves the average in both families, but B2 worsens it in both. In confirmation, log-OLS shows B2 > B1 > B0 on average (+2.6647% and +4.1837% incremental QLIKE reductions); LightGBM improves with B1 (+4.4713%) and worsens when B2 is added (-1.8127%). None of the eight contrasts in the two tables has a Holm p-value below 0.05.

Stability is also uneven: in confirmation, the second time block is negative for both log-OLS increments, and log-OLS B1 becomes -0.00076519781 when the third block is removed. LightGBM B2 is negative after removing any of the three blocks. Having more available information does not guarantee that the estimator extracts a stable improvement from it.

In the primary window, 2025-05-15 contributes 99.94095565% of the sum of session QLIKE losses for log-OLS B2. Two forecasts, in MSFT and TSLA, reach the fixed floor of 1e-12. The diagnostic reproduces aggregate loss by asset from saved forecasts. The session remains in every primary figure; there was no refit or floor change. Fit-rank metadata are insufficient to causally attribute the extreme to a particular variable. Evidence: [diagnostic](../../artifacts/rp4_b2/tail_diagnostic.json).

Percentile intervals and centred two-sided p-values are not inversions of the same test. Their asymmetry explains why, for two confirmation contrasts, the percentile CI excludes zero while the raw p-value exceeds 0.05. Both are reported as specified; the Holm p-values in that window are 0.2312 or 0.6470. The confirmation event secondary has only two sessions: its mean is reported, not an additional inferential confirmation.

## Data and coverage actually executed

Registered files and their exact columns remain in the [accepted inventory](../../artifacts/rp4_inventory_v1/REPORT.md). The [specification](specification_v1.md) fixes nested sets of 29, 71 and 136 predictors, plus a common intercept and asset contrasts. The 25 cells allow NaN; other variables are mandatory. Quality, age and latency diagnostics are not used as predictors.

A2 contains 185,729 origins and 479 sessions: 181,829 registered origins plus 3,900 reconstructed from 20 to 31 July. There are 185,715 finite RV30 values; 14 windows are excluded for missing observed bars (seven AAPL and seven TSLA). Of 83,509 matches to registered targets, 83,502 retain finite pairs after that check and agree exactly, with zero maximum and mean difference. Neither target windows nor the UW gap were filled.

RV30 reuses the rp2_block3 bar indexing. With bars labelled at their start, the last bar used ends one minute after the nominal target_end label; session splits and the 60-minute embargo comfortably separate that minute. The target was not changed to improve results. Comparisons use asset, session_date and origin_minute.

ATM coverage at 8–30 days in A2 is 99.7577–99.7836%, not the initially stated 100%. Minimum extreme-wing coverage with maturity ≥8 days is 82.86868%. In the 25-session extension, those figures are 100% and 93.84615%, respectively. All cells are retained, including sparsely populated ones: [A2 coverage](../../artifacts/rp4_a2/coverage.csv) and [extension coverage](../../artifacts/rp4_b1/coverage.csv).

B1 completed 331 jobs: 280 FMP asset-sessions, 25 UW sessions, 11 phase9 copies, six dividend jobs, six earnings jobs, two Treasury years and one FOMC calendar. Final missing items: zero. The 54 original phase9 files were revalidated by hash without modification. The extension adds 9,750 finite RV30 values, without excluded asset-session blocks in materialisation. After applying the same predictor mask to all six evaluation cells, 5,360 confirmation origins remain, 54.9744% of those 9,750. Exclusions are not confused with missing downloads or resolved through unregistered imputation.

The complete panel has 195,479 rows. Exact equality of the 185,729 development rows before and after the join was checked by keys and after rereading the parquet. New dividend responses produced zero historical rate/cash differences in the compared development data. New Greeks use actual rates and dividends; the old Greek columns in registered B2 retain their historical r=q=0 convention, disclosed in A1.

## Traceability and stages

| Stage | Verified closeout | Commit |
| --- | --- | --- |
| INIT | Branch from origin/main; decision 128, inventory and generated state | 0d98e79a |
| A1 | Specification and decision 129 before evaluation | 9748d246 |
| A2 | Development materialisation and RV30 comparison | 643b5226 |
| B1 | Complete inputs and immutable-join check | fdd12c5e |
| B2 | 418 primary sessions, exit 0 | 71a491b3 |
| B3 | 25 confirmation sessions, exit 0 | 852d6133 |

Exact commands, observed codes and stage hashes are in [A1](../../artifacts/rp4_a1), [A2](../../artifacts/rp4_a2/receipt.json), [B1](../../artifacts/rp4_b1/receipt.json), [B2](../../artifacts/rp4_b2/receipt.json) and [B3](../../artifacts/rp4_b3/receipt.json). Original exit codes lost in transport from some A2 workers remain UNVERIFIABLE; subsequent manifests, hashes and the join command were verified. Software PASS is not statistical significance.

| Artifact | SHA-256 |
| --- | --- |
| Markdown specification | 24a0fe96ba917bf284cbc0eda3f64f7ab3f41ede665f7021a9be20bdbeebd03d |
| JSON specification | 865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5 |
| A2 development panel | 51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949 |
| B1 complete panel | ecb1c6cce76cb6464d3cdf3d4ef409c60e204adf2df22fba6851e32199819d93 |
| Evaluator, both windows | 0064e37bebb00a0fb2550682e0c5590d64f16d88b2dfd9a4403b9ea82946ff14 |
| Primary result | d311d2773ae195968a59cea7d4e0c68dcf35d5d80e005c6cc0f1e028496d2eb2 |
| Confirmation result | 76816cf06a6483c009f9f148728c02ee39d065e7926fbf44dd80fa27dbf29ad7 |

Evaluator CSVs contain CRLF endings; they are preserved byte for byte with Git `-text` attributes rather than changing an already calculated artifact. Git whitespace checking uses `cr-at-eol` to recognise those endings as terminators. B1 history ZIPs contain code versions only; licensed data and origin-level forecasts remain private. The B4 closeout records final verification of the report, figures and Git bytes.

## Activated daily operation

Name: **RP4 daily collection**. Active Tuesday through Saturday at 09:10, Australia/Sydney, with a new RP4 root. The application allows one follow-up per task: this task's follow-up was updated, retaining its internal ID and a copy of the earlier configuration. The separate K3 collector was not modified, and phase9 remains intact.

Daily mode was executed on the last closed session, 2026-09-04: 24 PASS jobs, zero missing items, exit 0. It reused received files by hash. Manifest SHA-256: `270d3b92cb2bad3914f942efe2c66c7afbe1da91f1bcdc0c26f4ae76e081eaa2`. This verifies the collection command; it does not establish in advance that the scheduler will activate in future while the computer is off or the provider is inaccessible.

Collection adds bars and tape; it does not refit models or rewrite this report. Exogenous v1 snapshots remain preserved, and a later analytical extension must bind the exogenous inputs corresponding to its dates. There is no automatic publication, capital operation or additional purchase. The [runbook](operations_v1.md) contains the environment and recovery procedure.
