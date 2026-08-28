# Data roots and absolute paths

Licensed evidence lives outside the repository. Maintained entrypoints resolve that store
through `src/mds650/config.py`; historical one-shot scripts may retain the path recorded by
their frozen provenance.

## Current precedence

| Setting | Meaning | Resolution |
| --- | --- | --- |
| `MDS650_DATA_ROOT` | Required production store | If the configured path ends in `data`, the shared resolver returns its parent; otherwise it uses the path unchanged. |
| `MDS650_EXTERNAL_ROOT` | Optional sandbox/test override | Replaces the effective root for the current process without changing the production root. |
| `MDS650_RP2_STORE_ROOT` | Optional RP2-specific store | Overrides RP2 only; otherwise RP2 uses the production root. |
| Explicit CLI path | Entry-point-specific bounded input/output | Takes effect only where that script documents the flag. |

`MDS650_EXTERNAL_ROOT` is not the production fallback. It exists so tests, rehearsals and
redirected runs cannot write to the production store. If neither it nor a valid production
root is available when an operation begins, maintained code fails with
`MDS650_DATA_ROOT_REQUIRED`.

## Maintained versus historical scripts

- Maintained entrypoints obtain roots from the shared configuration or explicit arguments.
- Scheduled-task registrars resolve repository files from `$PSScriptRoot`; they do not
  publish a workstation-specific user path.
- Frozen campaign scripts can retain historical absolute defaults when changing the script
  would invalidate the provenance of an already completed run. Their presence is not a
  pattern for new code and not permission to rerun them.

A new repeatable script must use the shared resolver or an explicit flag. A new script must
not embed a developer username, drive layout or assumed worktree location.

The behavior above is pinned by `tests/unit/test_data_root_config.py`; the maintained script
inventory is `scripts/README.md`.
