# Documentation

**Start at [`INDEX.md`](INDEX.md).** It is the curated map: current methods, evidence
boundaries, reproduction contracts and literature, each labelled with its lifecycle
status.

## Why this directory is large

This directory holds the project's full research record, not a tidied summary of it. It
contains superseded protocol versions, dated decision records, incident write-ups and
audit findings alongside current methodology.

That is deliberate. Published results cite specific documents by SHA-256, and frozen
artifacts reference these paths directly. Deleting or relocating a superseded document
would break the chain that lets a reviewer verify what was decided, when, and on what
evidence. A protocol that was replaced is kept precisely so the replacement can be
audited against it.

**A filename suffix does not establish authority.** `_v1` next to `_v22` tells you the
order they were written, not which one governs. Use `INDEX.md` and the machine-readable
[`data/CANONICAL_STATE.json`](../data/CANONICAL_STATE.json) to determine what is current.
Where any document disagrees with the canonical state, the canonical state wins.

## Orientation

| If you want | Read |
| --- | --- |
| What the project found and claims | [`../README.md`](../README.md) |
| The current machine-checked state | [`../STATUS.md`](../STATUS.md) |
| The curated documentation map | [`INDEX.md`](INDEX.md) |
| To run or extend the code | [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) |
| How the system fits together | [`architecture.md`](architecture.md) |
| What could still be wrong | [`threats_to_validity_matrix_v1.md`](threats_to_validity_matrix_v1.md) |
| Withdrawn results and why | [`rp2_v3/SUPERSEDED_RESULTS.md`](rp2_v3/SUPERSEDED_RESULTS.md) |

Do not reorganize by moving frozen files between directories.
