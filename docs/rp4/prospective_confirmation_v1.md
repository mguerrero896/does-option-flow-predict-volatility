# Prospective replication of specification v4 — registration v1

**English translation. Historical seals refer to the preserved original bytes.**

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

Local registration: **2026-09-08T04:24:01.918499+00:00**. This registration applies the v4 test, without scientific changes, to future observations; **it is not a v5**. The historical result remains closed. The acquisition task was already enabled and, when this document was registered, its data directory did not yet exist. The hash establishes the bytes and the local receipt establishes the observed sequence; they neither constitute a third-party timestamp nor prove what information any other person might have known.

## Inherited specification, pinned by hash

The [v4 specification](specification_v4.md) and its [executable contract](../../artifacts/rp4_v4_a1/specification.json) are incorporated in full, SHA-256 `0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04`. The [effective v3 specification](../../artifacts/rp4_v3_a1_empty_window/specification.json), from which v4 inherits predictors and eligibility, has SHA-256 `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5`. The [registration receipt](prospective_confirmation_v1_receipt.json) also fixes separate hashes for their scientific fields and existing producers.

Primary RV15 and secondary RV5 are retained; nested sets B0 ⊂ B1 ⊂ B2 with 29/69/138 predictors; the six assets AAPL, AMZN, META, MSFT, NVDA and TSLA, with SPY and QQQ as controls; the linear log-ridge family and trees with a QLIKE objective. Transformations, presence and empty-window indicators, mechanism variables, common masks, the 120-second source threshold, 60-minute purge and embargo, weights, forecast bounds, seed, hyperparameter grids and selection on the last ten training sessions are retained. Variables, horizons, families and exclusions are not selected using this replication.

Training continues to expand by session using the permitted historical past, whose originals are already pinned, and preceding prospective sessions whose targets would already be observable under the inherited causal masks. The first 60 historical learning sessions are not reused as replication observations; neither is a second learning period of 60 new sessions imposed. Daily fits consume only their causal training data; aggregate prospective losses remain uninspected until each registered read. The 30-minute causal limits are retained even when predicting 15 and 5 minutes.

## Cohort and definition of a complete session

Inclusion begins with acquisitions by `OptionsVolatility-Daily-Collection` from **2026-09-09 08:00 Australia/Sydney**. That first trigger corresponds to market session **2026-09-08 America/New_York**, whose start is after this registration. Sample dates are always XNYS sessions, not Sydney civil dates. Sessions before 2026-09-08 are not part of the replication even if downloaded later. Daylight-saving changes are resolved by the registered calendar.

Take the first 20 complete, eligible sessions in chronological order. A session requires a complete options file, all eight observed-bar components, valid hashes and keys, full coverage of calendar-required minutes and valid materialisation under the same v4 rules for all six assets. Collector `PASS` establishes only downloaded components: it is insufficient to declare a session scientifically eligible. Coverage and eligibility must also be checked without inspecting signs, losses or p-values. RV15 and RV5 use the same mask and retain the original RV30 control. Eligible finite values are never substituted; a discrepancy halts preparation and is recorded in a new file.

Absences, interruptions and incomplete sessions are recorded in a census with objective reasons; they are not filled, duplicated or replaced with additional proxies. Days are not chosen by performance. Sealed cohorts are not used and their stores are not opened. Acquisition retains the proxy status of source time: downloading data after the close does not demonstrate historical client availability or actual intermediary inventories.

## Reads and decision rule fixed now

**Single primary read: first 20 complete sessions. Replication confirms if H1 and H2 reject in the linear family at 15 minutes.** H1 contrasts B1 against B0 and H2 contrasts B2 against B1; both require a positive mean difference and one-sided p ≤ 0.05, and H2 opens only if H1 rejects. If H1 does not reject, H2 remains closed and its p-value is diagnostic only. If the sequence does not reject both, report “does not confirm at the primary read”, with effects and intervals, without claiming equivalence or absence of an effect.

Retain QLIKE = y/f − log(y/f) − 1; means by asset/session and equal weights across assets and sessions; delta = baseline loss − expanded-model loss; percentage reduction = 100 × mean(delta) / mean(baseline loss). Retain the circular bootstrap with five-session blocks, 9,999 resamples, seed 20260907, centred null and +1 correction for the one-sided p-value, and a two-sided 95% percentile interval. Trees, RV5, median, trimmed mean and other registered diagnostics are reported with their signs without replacing the primary decision.

**Second read: the first 40 complete sessions cumulatively**, once only if reached before the administrative defence-delivery date. Calendar availability depends exclusively on that date, documented before opening the first read, never on its results. If no administrative date has been fixed, the second read remains scheduled for reaching 40 sessions. The v4 test is retained and presented as a stability follow-up, with nominal p-value and explicit comparison with the 20-session read. **It cannot rescue a negative first read or create a second opportunity for confirmation at 5%.** Nor is it described as independent of the first 20 sessions. This distinction retains a single confirmatory decision with the requested threshold without introducing an alpha correction that would change v4.

There are no interim reads, significance-based stopping, sign-dependent extension, switching to another family or selection of the best horizon. An adverse second read is disclosed even if the first confirmed. With fewer than 20 complete sessions there is no confirmatory decision. No fitting or inference is performed in this registration; the collector only acquires data and does not automatically schedule these reads.

## Custody and execution conditions

Each input retains its acquisition receipt, hash, session date and coverage census. Before any prospective fit, a new manifest will pin the authorised historical inputs, new inputs, code, environment, mask, v4 specification and this registration. Frozen files are not changed and output paths of closed executions are not reused. An error is documented with a new receipt; it does not permit discretionary repetition of a consumed read.

The [receipt](prospective_confirmation_v1_receipt.json) contains the output of `launch.ps1 -DryRun`, task and trigger state, this document's hash and the local observation that new data are absent. The specification, collector and existing scientific artifacts remain unchanged. This registration does not authorise publication or remote transmission.
