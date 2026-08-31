# Gate 5 same-channel reconciliation proposal v1

> **PROPOSAL ONLY — IMPLEMENTATION NOT AUTHORIZED.** Do not acquire provider data,
> activate a task or construct this route without a separate owner resource decision.

## Decision the design would unlock

Backfill and revision become identifiable only when the live log and the later replay
represent the same individual-trade channel with stable event identities and versioned
payload hashes. The proposed route would record sanitized live receipt envelopes from
that channel, then compare them with a later same-channel full tape. The existing
replay-only receipt-log script is not a live collector and does not satisfy this design.

The minimum implementation would need:

1. a live individual-trade collector with crash-safe append, heartbeat and exact local
   receipt timestamps;
2. a later same-channel tape fetch and immutable source fingerprints;
3. a join contract distinguishing absent-live, added-later and payload-changed events;
4. the existing alert path for stale heartbeats, poll failures and latency outliers;
5. a target-blind aggregate artifact containing rates and quantiles only.

No outcomes, predictions or losses belong in this route.

## Resource envelope

The request estimate assumes six assets, one request per asset per minute and a
390-minute regular session. That is `6 × 390 = 2,340` base requests per session;
30 sessions require 70,200 requests before pagination and retry. A 20% operating
allowance gives 84,240 requests. This is a planning bound, not a statement about the
provider's current endpoint or plan: batching, pagination, rate limits and monetary
price have not been verified and require a current provider quote before authorization.

The known later tape is approximately 1.4 GB per session. Tape-only retention is about
42 GB for 30 sessions. If the live same-channel stream is conservatively budgeted at the
same scale, two copies require about 2.8 GB per session or 84 GB for 30 sessions; a 20%
working-space allowance raises the operational budget to about 100.8 GB. Compressed
sanitized receipts may be materially smaller, but that should be measured, not assumed.

For a session-level failure mode occurring with probability 10%, at least 29 independent
sessions are needed for a 95% chance of seeing it once:
`1 - (1 - 0.10)^29 = 95.29%`. Thirty sessions raise that probability to 95.76%; 20
sessions provide only 87.84%. Recommend 30 sessions as an operational-detection floor,
not as a precision or power guarantee. Dependence across days and rarer failure modes
would require a larger campaign.

## Recommendation

Proceed only if the owner accepts the verified provider quota/price, approximately
101 GB of working storage, and a 30-session collection horizon. Otherwise retain the
current `PROXY_ONLY_CROSS_CHANNEL` boundary. This proposal deliberately changes no
task, credential, data subscription or scientific state.
