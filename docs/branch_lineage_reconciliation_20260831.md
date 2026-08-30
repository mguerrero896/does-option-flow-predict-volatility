# Branch-lineage reconciliation (2026-08-31)

## Why this record exists

Repository recreation left scientific and operational work under disjoint commit graphs.
Merging those graphs would restore stale state and bypass the selective public-history
boundary. Deleting the refs without content comparison would risk losing valid work.

This record compares each retained tip with `origin/main` at
`947ea908a0d217099b184d8578cee4cb7de1b0d0`. A branch name is not evidence of content
custody; the dispositions below use merge bases, tree comparison, patch identity and
current contract coverage.

## Disposition

| Archived topic | Retained tip | Lineage | Disposition |
| --- | --- | --- | --- |
| `public-science-remediation` | `f7af480b0a36acc1b97b34b5f5a4a4df765884de` | Disjoint | Phase 8 v1 material is superseded by the consumed v2 bridge, result and dispersion audit. Replaying it would regress one-read custody. |
| `canonical-convergence` | `cf55943ec64ff02965470f8c352679ce7e06ebb2` | Disjoint | Selective only. Current canonical state and Supabase history supersede its evidence snapshots. Panel identity, critical coverage, active path portability and the read-only ACL audit were replayed; stale tooling records remain audit-only. |
| `local-knowledge-remediation` | `75860216c3ebc98c6d30a6ea5b92d7490aa5421b` | Disjoint | No unique science. The Phase 9 reboot runbook and knowledge scripts are local operations records retained by the archive tag. |
| `remediation-20260821` | `3dc873d15e22bb34c356aad36b0445dc3a26e769` | Disjoint | Current `main` contains the ancestry, watchdog, collector and task-liveness controls or stronger successors. Claude/SpecKit integration and an obsolete migration remain audit-only. |
| `post-rewrite-remediation-20260828` | `8022599b822f208eea0a02316bf08f999a176e5a` | Base `7eed06c2` | Selective replay. Supabase authentication is superseded by PR #18. Critical-producer coverage and exact panel-byte identity are recovered in the current line. |
| `public-hermetic-fixtures` | PR #12 head `8660fae70416e863d959c77029cef0f2a23a33ca` | Rewritten | Tree-equivalent content is in `main`; no replay. |
| `actions-node24` | PR #13 head `71e3c84692866e93afff10633374db757c70ad29` | Rewritten | Tree-equivalent content is in `main`; no replay. |

The five `archive/*` tags are local custody refs, not public release refs. They preserve
the source objects without making a disjoint historical graph part of `main`.

## Selective replay boundary

The replay restores:

- 100% line and branch coverage for seven critical scientific producers;
- fail-closed tests for replication inputs, temporal validation, RP2 scorecards and frozen
  RP3 forecasters;
- byte-length and SHA-256 verification for every declared RP2 panel, including an explicit
  external panel root that does not weaken evidence-root completeness;
- configured roots for every active indexed Python entrypoint, with no workstation drive
  literal; and
- the read-only Supabase ownership/default-ACL verification query.

Four producer guards from `b81bca079f9c581dfc6029fb1a92be329edcc7b1` are not replayed.
The complete `src/mds650` tree is part of the Phase 8 dispersion-audit closure frozen at
`294b4d6ef9c5d822b900f37557b204f39b4b4fa39a1d23e1ee7cc09e4c3f369c`. Changing those
bytes would invalidate the current closure contract. Their tests remain with the archive
tag; a successor producer version must carry them if that source tree is reopened.

No scientifically eligible result or missing scientific producer remains solely on a
disjoint branch after this selective replay.

## Reproduction commands

```powershell
git fetch --prune origin
git merge-base origin/main <ref>
git rev-list --left-right --count origin/main...<ref>
git diff --shortstat origin/main <ref>
git cherry -v origin/main <ref>
git worktree list --porcelain
git ls-remote --heads origin
git ls-remote --tags origin
```
