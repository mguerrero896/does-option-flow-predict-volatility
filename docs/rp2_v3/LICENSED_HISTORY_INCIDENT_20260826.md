# Data-handling incident, 2026-08-26

A public disclosure, kept deliberately short. Operational detail — commands,
backup locations, machine paths — is not published, because publishing it serves
no reader and creates the next exposure.

## What happened

Two derived data panels built from licensed market data were committed to this
repository, then deleted from the working tree. Deleting a file from the tree
does not remove it from Git history, so both remained retrievable by anyone who
cloned the repository, for six days.

The panels held origin-level rows of realized-volatility features computed from
licensed 1-minute bars. They were derived works of vendor data and were never
intended for publication; the repository's own data-availability policy lists
that class of file as gated.

## Scope

- **Exposure window:** 2026-08-20 to 2026-08-26.
- **Affected:** two derived panels. No credentials, no personal data of third
  parties, and no other licensed dataset were involved.
- **Discovery:** an internal adversarial audit of the published history, not an
  external report.

## What was done

The published history was rewritten to remove the files, the repository was made
private during remediation, and the affected repository was subsequently deleted
and replaced. Removal was verified from a clean clone: no licensed blob is
reachable from any reference.

## What prevents a repeat

The pre-existing guard checked the *working tree* — it ran `git ls-files` and
therefore could not see a deleted-but-committed file. Two guards were added and
run in continuous integration on every commit:

- `tests/test_gated_history_contract.py` scans reachable **history**, not the
  tree, for granular data and for operator tooling.
- The same test refuses to pass on a shallow checkout, because a one-commit
  clone cannot see the history it is supposed to be auditing.

Both are ordinary tests: they fail the build, on the branch, before a merge.

## Vendor position

The exposed material was derived features, not vendor data as delivered, and the
exposure was closed within six days of its creation. The author is available to
discuss the matter with any affected provider.
