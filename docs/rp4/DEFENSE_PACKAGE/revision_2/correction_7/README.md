# Defense — forecast horizon and information visibility

This English presentation preserves the complete historical defense, its repaired secondary endpoints and their limits. It distinguishes the proposal's original objective from the declared horizon extension. Cross-horizon comparisons are descriptive within the stated family and window; they do not establish an optimal horizon.

The PIT cutoff determines which information is admissible in predictors without changing the target horizon. Separately assigned visibility sensitivities are documented as an assignment; this package does not inspect or claim their readiness, execution or results. Subsequent programme extensions are described on the [repository front page](../../../../../README.md); the historical closure statements below retain their original context.

Read the [executive summary](executive_summary.md), its [print edition](executive_summary.pdf), the [examiner questions](examiner_qa.md), the [claims matrix](claims_matrix.csv) and the [presentation script](defense_slides.md). The [horizon and clock evidence](horizon_pit_evidence.json) preserves original saved fields, selectors and literal source quotations. The [secondary-endpoint revision](../../../results_v3_revision3.md) and [saved bilateral/Holm sensitivity](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_5/README.md) retain their results.

The [translation receipt](translation_receipt.json) explicitly separates this English presentation from the [unchanged historical package](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_7/README.md). Every original numerical binding is retained in the matrix: its original claim, selector, rendering and artifact hash are unchanged, while a separate column supplies English number formatting. Duplicate Spanish-summary bindings and external historical-document bindings remain identified. The complete existing English summary page is extracted from the original PDF; its text and numbers are not rewritten.

The [manifest](evidence_manifest.json), [content receipt](receipt.json), [checksums](SHA256SUMS), [layout receipt](summary_layout_receipt.json) and [verification receipt](verification_receipt.json) make these boundaries reviewable. The English Markdown is the presentation source; the [public producer](../../../../../scripts/build_rp4_english_defense.py) regenerates its matrix and custody records. This translation adds no losses, fits, intervals or scientific results and changes no scientific registration.

Rebuild and check the presentation after installing the repository's locked development environment:

```sh
uv run --frozen --no-sync python scripts/build_rp4_english_defense.py
uv run --frozen --no-sync python scripts/build_rp4_english_defense.py --check
```

To recreate the English PDF page, use the separately resolved PDF utility:

```sh
uv run --with pypdf==6.10.0 --frozen --no-sync python scripts/build_rp4_english_defense.py --pdf
```

The original full claim inventory remains in the archived matrix; the current matrix retains every original numerical binding, including entries outside these presentation documents. The new verification receipt reports the exact scope tested.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
