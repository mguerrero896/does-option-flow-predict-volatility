# Contributing

This repository is the working record of a completed study, which also carries a
preregistered prospective extension. Code contributions are not accepted: every
change must preserve hash-pinned frozen evidence and a one-read policy, and an
external patch cannot be verified against evidence that is not public.

**Issues and discussion are welcome.** Questions about method, requests for
clarification, and reports of errors in the published results are valuable and
will be answered.

Maintainers should read [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) before
changing code, evidence or documentation. It identifies the source-of-truth hierarchy,
safe execution planes, script-registration rule and required verification. The current
system map is [`docs/architecture.md`](docs/architecture.md).

## Before any push

Install the versioned fail-closed hook once per clone:

```bash
git config core.hooksPath scripts/hooks
```

Before pushing a branch, scan the candidate `HEAD` and public remote refs:

```bash
uv run python scripts/scan_public_secrets.py
```

The hook rejects a pushed ref whose tip tree contains any exact path in
`scripts/_gated_exclude_list.txt`. Push explicit reviewed refs; never use a blind
`git push --tags`, because local archive tags are custody records rather than publication
candidates. Publish a tag only from a clean public clone after
`uv run python scripts/scan_public_secrets.py --include-tags` passes there.

## If you are reproducing the analysis

The hermetic Tier 1 suite runs from a clean clone with no credentials:

```bash
uv sync --locked
MDS650_PANEL_GUARD_MAY_SKIP=1 uv run pytest tests -q --ignore=tests/unit/test_independent_replication_panel.py --cov=src/mds650 --cov-report=term --cov-fail-under=90
```

The flag allows only explicitly guarded licensed-panel checks to skip. Provider calls,
Supabase end-to-end checks and Tier 2 panel verification remain separate; a Tier 1 pass is
not evidence that those external planes passed. See the README evidence and data-access
section. The exact skip count is not a stable interface.

## Reporting a problem with the results

Open an issue quoting the artifact digest you are questioning. Every published
number traces to a hashed artifact, so a disagreement can be located exactly.
