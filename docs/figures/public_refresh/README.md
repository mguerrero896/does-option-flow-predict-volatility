# Public research diagrams

These four diagrams describe the published research programme and its reproduction
boundary. The JSON files are the versioned Archify sources. The SVG files are
static exports for Markdown; each HTML file is a standalone reader with light and
dark themes, zoom and export controls.

| Diagram | Static figure | Source | Standalone reader |
| --- | --- | --- | --- |
| Original question to prospective replication | [SVG](proposal_to_replication.workflow.svg) | [JSON](proposal_to_replication.workflow.json) | [HTML](proposal_to_replication.workflow.html) |
| Public verification and licensed reproduction | [SVG](reproducibility_map.architecture.svg) | [JSON](reproducibility_map.architecture.json) | [HTML](reproducibility_map.architecture.html) |
| Programme timeline through RP4 v4, with the closed v5 extension noted | [SVG](programme_timeline.architecture.svg) | [JSON](programme_timeline.architecture.json) | [HTML](programme_timeline.architecture.html) |
| Registration, seals and numbered corrections | [SVG](registration_seals.workflow.svg) | [JSON](registration_seals.workflow.json) | [HTML](registration_seals.workflow.html) |

The timeline orders events along one path. Spacing does not encode elapsed time,
and arrows do not imply independent replications or causal relationships. Unlabeled
workflow arrows mean the next displayed stage; their endpoints already state the
action. Conditional gate branches retain explicit labels.

## Evidence and interpretation

| Diagram statement | Public source and qualification |
| --- | --- |
| Earlier nulls precede the conditional RP4 finding | [RP2 final report](../../rp2/FINAL_REPORT.md), [PIT successor claims and limits](../../pit_v22_claims_and_limitations_v2.md), [Phase 8 disposition](../../sealed_cohorts_disposition_v1.md). The Phase 8 bridge was read once on 2026-08-30; its result is mixed and exploratory. |
| Primary RV15, 419 sessions, linear B2/B1 QLIKE reduction +0.623%, p = 0.0032 | [Saved primary statistics](../../../artifacts/rp4_v4_b4/primary_statistics.csv), selecting `horizon_minutes=15`, `window=primary`, `family=log_ridge_harq`, `contrast=B2_over_B1`. The saved percentage 0.622794096399778 rounds to +0.623%. |
| Saved two-sided Holm sensitivity = 0.0248 | The same row's `p_holm_bilateral`. This adjusts four contrasts within the saved horizon/window; it does not correct historical search across versions. |
| Fourth evaluation; final 25 sessions do not confirm | [RP4 v4 results and limitations](../../rp4/results_v4.md). Reused windows are disclosed, and forecast loss is not trading alpha. |
| Closed RP4 v5 extension at RV15; v4 remains the headline | [Saved exploratory extension](../../rp4/results_v5.md), status COMPLETE. It uses the historical sessions and is not independent replication or a direct v5/v4 test. |
| RP4 prospective reads use 20, 40 and 335 new sessions | [Prospective amendment 3](../../rp4/prospective_confirmation_v1_amendment_3.md). The 45-session D analysis pools 25 observed and 20 new sessions at the first look. It is not another prospective look. |
| RP3 is sealed; estimated read 2029-01-30 at 662 evaluable sessions | [RP3 preregistration](../../rp3/PREREGISTRATION.md). This is a protocol statement, not verification of a live counter or a completed future read. |
| Public aggregates are distinct from licensed granular inputs | [Data access policy](../../../data/DATA_ACCESS.md) and [reproduction runbook](../../rp4/OPERATING_GUIDE.md). Public verification does not reproduce missing provider values. |

No prospective observations, raw provider inputs or model-training runs were used
to create these diagrams. The current layer's figures do not change sealed
protocols, result files or earlier evidence.

## Verify and regenerate

From the repository root, with Node.js installed:

```sh
node docs/figures/public_refresh/reproduce.mjs --verify
```

This checks all 12 source/HTML/SVG hashes and byte counts in the
[manifest](manifest.json), without any additional package or market-data access.

Regeneration additionally requires an existing **Archify 2.16** installation and
Chrome or Chromium. Set `ARCHIFY_HOME` to that skill's directory, then run:

```sh
node docs/figures/public_refresh/reproduce.mjs --render
node docs/figures/public_refresh/reproduce.mjs --verify
node docs/figures/public_refresh/reproduce.mjs --contact-sheets
```

The renderer runs Archify validation, atomic delivery and `visual-check`, and uses
the delivered reader's native canonical SVG export. It does not install or update
software. HTML and SVG hashes are expected to match under the recorded tool and
browser versions; a different renderer or browser can require a reviewed manifest
update. It never silently updates the expected hashes.

Each delivered HTML passed **9/9 showcase checks, 0 composition errors and 0
warnings**. Automated containment was checked at 1440×900, 1600×1000, 1920×1080
and 2048×1320. The light/dark contact sheets at the smallest and largest sizes were
inspected separately for labels, routes, node fit and balance. The manifest records
these results; automated `visual-check` receipts correctly keep visual review
pending until a person or image-capable reviewer inspects the captures.

Generated contact sheets, screenshots and raw local tool receipts are excluded
from version control. The manifest retains only sanitized receipts and hashes.
The classic Archify style preserves rounded nodes, directional arrows and dashed
boundaries; its semantic colors and typography are those of the installed renderer.
