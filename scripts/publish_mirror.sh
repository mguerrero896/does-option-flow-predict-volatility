#!/usr/bin/env bash
# Republish the GitHub mirror from the canonical (shallow) repo.
# As of 2026-08-18 the mirror is prepared for PUBLIC visibility: every path in
# scripts/_gated_exclude_list.txt (licensed-derived granular datasets) is stripped
# from the ENTIRE published history via git-filter-repo. Public material carries
# their SHA-256 pointers in data/GATED_DATA_POINTERS.json instead.
# See docs/consolidation_record_20260817.md for the graft rationale.
set -euo pipefail
# Tier-2 preflight (decision 63): a publish is REFUSED unless the full local
# gates pass, including the exact replica of the hosted hermetic job (ci-sim).
# This is what keeps red runs — and their failure emails — off GitHub.
echo "[publish] running mandatory tier-2 gates"
uv run python scripts/run_local_evidence_gates.py || {
    echo "PUBLISH REFUSED: tier-2 gates failed — nothing was pushed" >&2; exit 1; }
ROOT_COMMIT=2bcd0ca47a5205ebfb49bea88233353e32d66ef4
# Renamed 2026-08-26; the old repository is deleted, and an SSH alias is machine-
# specific, so this is overridable and defaults to the public HTTPS URL.
REMOTE="${MDS650_MIRROR_REMOTE:-https://github.com/mguerrero896/does-option-flow-predict-volatility.git}"
CANON=$(pwd)
# Two exclusion classes, one stripping pass:
#  - gated data (licensed-derived; pointer-tracked in data/GATED_DATA_POINTERS.json)
#  - internal working docs (local-only by decision; no pointers, just never published)
EXCLUDES=$(mktemp)
cat "$CANON/scripts/_gated_exclude_list.txt" \
    "$CANON/scripts/_mirror_internal_exclude_list.txt" | tr -d '\r' | grep -vE '^(#|$)' > "$EXCLUDES"
# Expand glob: lines against the canonical HEAD file list so the two integrity
# checks below keep comparing exact paths (git-filter-repo reads EXCLUDES
# directly and understands glob: natively).
EXCLUDES_EXPANDED=$(mktemp)
git ls-tree -r --name-only HEAD > "$EXCLUDES_EXPANDED.all"
grep -v '^glob:' "$EXCLUDES" > "$EXCLUDES_EXPANDED" || true
grep '^glob:' "$EXCLUDES" | sed 's/^glob://' | while read -r pat; do
    while IFS= read -r f; do
        case "$f" in $pat) echo "$f";; esac
    done < "$EXCLUDES_EXPANDED.all"
done >> "$EXCLUDES_EXPANDED"
sort -u "$EXCLUDES_EXPANDED" -o "$EXCLUDES_EXPANDED"

MIRROR=$(mktemp -d)/mirror
git replace --graft "$ROOT_COMMIT"
trap 'git replace -d "$ROOT_COMMIT" 2>/dev/null || true' EXIT
git init -q -b main "$MIRROR"
git fast-export --all --reencode=yes | git -C "$MIRROR" fast-import --quiet
# Strip gated data from every commit of the published lineage.
(cd "$MIRROR" && uvx git-filter-repo --force --invert-paths --paths-from-file "$EXCLUDES" >/dev/null)
# Check 1: no gated path may survive anywhere in the published history.
# The decision must not run through `head`: closing the pipe early makes grep
# die on SIGPIPE, pipefail turns the pipeline non-zero, and the `if` reads that
# as "no leak". Measured on this construction: clean detection at 1,000 leaked
# paths, silent false pass from ~4,000 up. The property was perverse — the more
# that leaked, the likelier the check passed. Collect first, decide after.
if [ ! -s "$EXCLUDES_EXPANDED" ]; then
    echo "PUBLISH REFUSED: the expanded exclude list is empty; nothing would be stripped" >&2
    exit 1
fi
LEAKED=$(cd "$MIRROR" && git log --all --name-only --pretty=format: | sort -u \
    | grep -Fxf "$EXCLUDES_EXPANDED" || true)
if [ -n "$LEAKED" ]; then
    echo "GATED PATH LEAKED INTO PUBLISHED HISTORY ($(printf '%s\n' "$LEAKED" | wc -l) path(s)):" >&2
    printf '%s\n' "$LEAKED" | head -5 >&2
    exit 1
fi
# Check 2: every non-gated file at canonical HEAD must match blob-for-blob.
DIFF=$(comm -3 \
    <(git ls-tree -r HEAD | awk '{print $3" "$4}' | grep -vFf <(awk '{print " "$0}' "$EXCLUDES_EXPANDED") | sort) \
    <(git -C "$MIRROR" ls-tree -r main | awk '{print $3" "$4}' | sort) | head -3)
if [ -n "$DIFF" ]; then
    echo "TREE MISMATCH (excluding gated paths):" >&2; echo "$DIFF" >&2; exit 1
fi
# Check 3: the hosted hermetic job must pass ON THE STRIPPED TREE. Running the
# replica on the canonical tree (tier-2) is not enough: tests that read files
# excluded from the mirror pass locally and fail on GitHub. This check runs the
# exact hosted command inside a clean checkout of the filtered mirror.
PUBCHECK=$(mktemp -d)/pub
git -C "$MIRROR" worktree add --detach "$PUBCHECK" main >/dev/null 2>&1 || git clone -q "$MIRROR" "$PUBCHECK"
echo "[publish] check 3: hermetic suite on the stripped public tree"
(cd "$PUBCHECK" && env -u MDS650_EVIDENCE_ROOT uv run --project . pytest tests -q --ignore=tests/unit/test_independent_replication_panel.py --cov=src/mds650 --cov-report=term --cov-fail-under=90) || {
    echo "PUBLISH REFUSED: hermetic suite FAILS on the stripped public tree" >&2; exit 1; }
# Check 4: never force-push a lineage that does not contain what is already
# published. The mirror is built from the canonical tree, which no longer
# projects the public repository — the RP2-v3 gates landed there as pull
# requests. docs/rp2_v3/MIRROR_HAZARD.md measures the two histories as disjoint,
# and --force means the remote would not refuse the loss.
# --check-tags covers the --tags push below: it force-updates every tag ref, and
# the tags are this project's frozen-evidence anchors. No --expect-remote here:
# passing $REMOTE as both the destination and the expectation compares a variable
# to itself and can never fire. The expectation belongs to a caller that knows
# the remote independently; the ancestry check is what protects this one.
uv run python "$CANON/scripts/publish_ancestry_guard.py" \
    --mirror "$MIRROR" --remote "$REMOTE" --branch main --check-tags || exit 1
git -C "$MIRROR" push --force "$REMOTE" main
git -C "$MIRROR" push --force "$REMOTE" --tags
echo "mirror published: canonical $(git rev-parse --short HEAD) -> mirror $(git -C "$MIRROR" rev-parse --short main) (gated data stripped)"
