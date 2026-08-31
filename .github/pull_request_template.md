## Why

<!-- State the defect or risk and why this change is necessary. -->

## What

<!-- State the smallest change that resolves it. -->

## RED evidence

<!-- Paste the base commit SHA, exact command, non-zero exit code, and failure signature observed before the production change. -->

## GREEN evidence

<!-- Paste the final commit SHA, the same command, zero exit code, and passing output observed after the production change. -->

## Scientific integrity

- [ ] No sealed cohort was read
- [ ] RED and GREEN evidence above use the same test command
- [ ] All information sets fail closed
- [ ] Same evaluation mask used for nested comparisons
- [ ] Before/after scorecard attached
- [ ] No frozen artifact overwritten
- [ ] Superseded artifacts explicitly recorded

## Verification

- [ ] Ruff
- [ ] mypy
- [ ] hermetic pytest
- [ ] local evidence gates
- [ ] Review on latest commit
