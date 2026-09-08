# Closed v5 public evidence

The [allowlist receipt](allowlist_receipt.json) identifies every copied aggregate,
source file and custody record by path and SHA-256. The completed five-family
snapshot contains 419 sessions at 15 minutes. The later sensitivity remains
explicitly post hoc; neither replaces the primary v4 conclusion.

The imported tables contain aggregate metrics and frequencies. Per-origin
forecasts, targets, licensed prices, session fit bounds and coefficient payloads
were not copied. Reading this public subset does not reproduce the private
forecast audit or prove future acquisition or prospective eligibility.

The full [English report](../../docs/rp4/results_v5.md) preserves adverse results,
unavailable families, source discrepancies and the history of cost amendments.
The English renderer reads only preserved Markdown originals and the custody map:

```powershell
uv run --frozen --no-sync python -m scripts.build_rp4_v5_english
```

The default checks the four English documents. Add `--write` to regenerate only
those presentation files. The historical audit/publishing sources are provided
for inspection and retain their original scientific behavior; they were not run
as part of this translation. Public path redactions require their own provenance
receipt and do not inherit the original byte hashes.

The original Part 34 receipt and sidecar remain in the historical archive. The
[public receipt](../rp4_v5_part34/public_receipt_v1.json) retains all 25 historical
pins and distinguishes original bytes, translated or redacted derivatives, and
references not distributed with this release. A private operational ledger is
represented only by its identity and historical hash. The earlier methodology
snapshot and decision 136 clarification and seal are also not distributed.

After final presentation and path projection, regenerate this derived receipt:

```powershell
uv run --frozen --no-sync python -m scripts.build_rp4_v5_public_receipt --write
```

Without `--write`, the command checks it. The new receipt uses LF, so its raw
SHA-256 matches the frozen registry's normalized digest. Publication registers
only this new receipt path; all earlier registry entries remain unchanged. The
historical source registry is not a replacement for the public registry, which
also contains separately published entries. Hashes of public derivatives do not
prove access to the omitted sources or reproduce the private forecast audit.
