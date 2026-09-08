# RP4 v5 — technical amendment 2, attempt A3

**English translation. Historical seals refer to the preserved original bytes.**

Miguel, 2026-09-08. Parts 18→17→17b read completely in that order and subsequent direct message: 15% memory reserve. New registration before the CPU probe and relaunch. RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.

Decision 134, specification v5, A1, amendment 1/A2 and their results are preserved byte for byte. The previous registration is not reinterpreted. v4 retains the headline; v5 remains historical development with disclosed cost amendments.

## Authorised changes and scope of this run

RV15 only and five families, in this order: seasonal persistence, log-HAR, log-ridge-HARQ, log-ElasticNet and LightGBM-QLIKE. The selector and top2 ensemble use only these five families. The dense network is **deferred for cost, not evaluated in A3**; metrics and frequencies are unavailable, never zero performance. A1 did have a partial fit and A2 a network probe: both are disclosed. RV5/RV30 are deferred; any subsequent network appendix requires results separate from the current five and is outside this launch.

LightGBM returns to the original CPU producer `rp4_v2_code.models.fit_lightgbm`, v4 grid `[15,31,63]`, `deterministic=True`, the other v5 parameters unchanged and seed 20260908. Threads per estimator=floor(32/F). A2 GPU measured 193.2075962 s per session with all three information sets and extrapolated 22.49 h for RV15; the network measured 242.4896918 s and extrapolated 28.22 h. GPU is dropped for cost. The cited v4 comparison (~19 s per session and set) has a different measurement scope: no speedup is attributed before observing the new CPU probe.

ElasticNet retains `precompute=True`, `max_iter=500000`, `tol=1e-6`, cyclic selection, alpha=[0.0001,0.01,1] and l1_ratio=[0.1,0.5,0.9]. A1 already precomputed Gram; it is not a new improvement attributable to A3. A2 exclusions for non-convergence are inherited only for alpha 0.0001, with stage/cause/iterations/dual gap and the next convergent candidate in the same internal ranking for refit. Other alpha values do not receive that exception. All cells are recorded. MLP configurations inherited in JSON are a parameter archive for the appendix; the adapter rejects fitting them in this run.

## Scientific invariants

No changes to assets, panels, B0/B1/B2 (29/69/138 variables), eligibility, common RV30 mask, PIT 120 s, partition 2026-08-01, warm-up of 60 sessions, 419 development sessions, purge of 60 min or internal validation over 10 sessions. Only train|test is materialised; each selection/preprocessing uses only earlier training/validation. QLIKE, equal asset/session aggregation, circular bootstrap block 5/9999/seed 20260908, H1→H2, Holm across two chains and Bonferroni×5 bound are retained. This bound does not correct all adaptive search; no amendment turns development into prospective confirmation.

## Memory and registered estimate

A2 matrices and targets are verified by SHA256 and opened as read-only mmap shared across processes; only the session window and required information set are copied. Memory is released between sets and sessions. Torch is not loaded. Probe: RV15/2026-07-31, five families and B0/B1/B2, 32 threads, CPU affinity 0–23. Its predictions are not reused as tournament records. Peak is the process's maximum working set, corroborated by RSS samples every 10 ms.

Allocatable=min(free physical RAM, free Windows commit). The direct message replaces 0.7 with 0.85: **F=min(8,floor(0.85×allocatable/measured peak))**. Record bytes, rounding and F; if F<1, do not allocate an impossible worker. If F=1, run with 32 threads. Own CPU affinity 0–23 respects CPU 24–31 reserved by the parallel task; 32 software threads do not imply 32 available CPUs.

Prior estimate: measured seconds per family×419/F. Reference range 1–2 times, without a promised bound; window size, threads and external load affect actual time. `execution.json` fixes F/threads/measurements; `estimate_reported.json` binds the notice to the user. Amendment and code are committed locally before the run. Parameters are not changed after observing results.

## Unattended execution and deliverables

Independent launch through hidden Start-Process, log under `artifacts/rp4_v5_run_a3_20260908/logs/`. `progress.json` at that root reports running/done/failed, error, time, counts by family/RV15, F/threads and ETA. Ordinary update every 10 seconds (required maximum 5 min). Per-session receipts verify identity, hash and seal; the same command resumes without refitting complete sessions. Mutual exclusion per run and shard. Up to 3 attempts per worker with every error recorded; persistent failure requires diagnosis.

Each family publishes a partial table after 419 sessions, with snapshot/receipt/hash. Selector inference only after 419×5 records. Final control: repeat the first session RV15/2024-10-28 under another shard identity with the same F/threads for all five families; binary identity of CPU forecasts is required. CPU/GPU control does not apply to A3 because it does not fit on GPU. The A2 probe is disclosed. A final receipt is written and hourly progress, completion or failure reported.

No prospective or sealed cohorts are read. No push. The live `results_v5.md` report is updated while retaining every previous snapshot and the A1 historical archive. Code, specification, authorisations and environment are bound by hashes in `artifacts/rp4_v5_a3/freeze.json`.
