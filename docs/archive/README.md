# Historical archive

These records preserve earlier wording, numerical claims, registrations and
corrections. The current reading starts at the [numbered index](../INDEX.md) and
[RP4 v4 results](../rp4/results_v4.md). Historical Spanish text is retained here;
English summaries explain the role and current disposition of each layer.

| Collection | Contents and provenance |
| --- | --- |
| [Defense correction history](rp4/DEFENSE_PACKAGE/INDEX.md) | Original package, revision 2 and corrections 1–6, with a summary for each layer. Correction 7 has a complete current English presentation and retained source bindings. |
| [Earlier reports and protocols](public_history/INDEX.md) | Closed RP4 v1–v3 reports, registrations, audit notes and earlier data plans, with English summaries and the original source map. |
| [V3 translation sources](rp4/results_v3_original/README.md) | Full original v3 report and producer, quantitative and diagnostic invariance evidence. |
| [Presentation source map](rp4/presentation_originals/original_paths.json) | Original v4/final reports, figures, protocols and their hashes. Current English copies retain the scientific values. |
| [Earlier general documentation](public_refresh_baseline/original_paths.json) | Previous decisions, validity matrix and historical report wording, preserved before present-scope corrections. |

An `.original` file retains exact source bytes when public redistribution is safe.
Where a source contains a private locator or operational metadata, the public tree
contains a separately named `.public` derivative and a
[redaction receipt](../../artifacts/rp4_public_refresh/archive_redactions.json).
That receipt verifies the derivative's actual hash and records the original hash
as provenance; it does not assert that redacted and original bytes are identical.
Private originals remain unchanged. Numeric and selector checks are independent
of the presentation redaction.

Public Git history preserves its existing ancestry. This archive does not change
the scientific status of earlier results, reopen a consumed read or amend a seal.

## Historical machine locators and integrity

Three historical JSON artifacts retain their original machine-location strings
because those strings participate in a partition seal or a bound evidence record.
They are historical provenance, not instructions to access the original machine.
The partition has a verified canonical self-hash; the v22 manifest is pinned by a
self-hashing claim ledger; the sourcebound v23 manifest is pinned by the sealed
preregistration and its readiness validator. These bindings are distinct from
membership in the frozen-artifact registry. The other five JSON files contain
ordinary location metadata or observational source-index hashes, so their
location values alone are replaced with neutral placeholders.

The [per-file decision receipt](../../artifacts/rp4_public_refresh/historical_locator_decisions_v1.json)
records all nine decisions, original Git-blob and checkout hashes, publication
hashes, JSON pointers and hashes of original location values. Private originals
remain retained. Masked-content checks verify that all other JSON values and
every other log byte are unchanged. Existing JSON attributes preserve the public
LF representation; the log now has its own scoped LF attribute.

| Historical artifact | Decision | Integrity basis |
| --- | --- | --- |
| [Canonical validation log](../../artifacts/canonical_validation_v1/full_pytest.stdout.log) | Redact four location prefixes | No fixed file seal found; remaining log content is identical. |
| [Bootstrap incident](../../artifacts/independent_replication/evaluation_incidents/20260811_bootstrap_contract.json) | Redact two location values | Observational evidence-index hashes identify the original source. |
| [Target acquisition summary](../../artifacts/independent_replication/target_acquisition_summary_v1.json) | Redact one location value | Observational evidence-index hashes identify the original source. |
| [Research partition](../../artifacts/rp2_block1_partition/partition.json) | Preserve bytes | The canonical partition seal includes its location field. |
| [Market acquisition metadata](../../artifacts/rp2_validation_market/acquisition.json) | Redact one location value | Its stored data hash covers the separate data object, not this JSON document. |
| [Target-blind v22 manifest](../../artifacts/target_blind_v22/target_blind_common_predictor_manifest_v22.json) | Preserve bytes | Exact source pin inside the self-hashing historical claim ledger. |
| [Target-blind v23 manifest](../../artifacts/target_blind_v23/target_blind_common_predictor_manifest_v23.json) | Redact two location values | No fixed container seal found in the inspected bindings. |
| [Committed target-blind v23 manifest](../../artifacts/target_blind_v23_committed_20260812/target_blind_common_predictor_manifest_v23.json) | Redact two location values | No fixed container seal found in the inspected bindings. |
| [Sourcebound target-blind v23 manifest](../../artifacts/target_blind_v23_sourcebound_20260812/target_blind_common_predictor_manifest_v23.json) | Preserve bytes | Exact manifest-file pin in the sealed preregistration and readiness check. |

The sourcebound manifest already had a CRLF checkout and a distinct LF public Git
blob before this correction. Both historical identities are recorded separately;
preserving its location strings does not claim those hashes are equal or repair
the existing portability limit of a raw-byte source seal. No registry entry,
scientific value, authorization or execution state is changed here.

The [historical sequential-testing policy](../sequential_multiplicity_policy_v1.md)
also retains one hypothetical quotation in its original wording. Its SHA-256 is
`32920643476da1ee7271acd5f25876a0d2e49bad0634c01e19219cc3d06ef38f`, bound by the frozen
bridge contract's provenance. The author-voice screen exempts only that exact
quotation at that exact file hash; active narrative and editable draft text use
impersonal or single-author wording. This preserves historical evidence without
presenting the quotation as current author voice.
