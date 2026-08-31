"""Standing tripwire: no licensed-derived dataset may reach the public mirror.

Every tracked parquet larger than the fixture threshold must be listed in
scripts/_gated_exclude_list.txt (which publish_mirror.sh strips from the whole
published history). A new granular artifact committed without registering it
here fails the suite BEFORE it can leak into the public repository.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXCLUDE_LIST = REPO / "scripts" / "_gated_exclude_list.txt"
FIXTURE_ALLOWED_PREFIXES = ("artifacts/pilot_preview/fixture_",)
AGGREGATE_MAX_BYTES = 512 * 1024  # tiny stability/audit summaries are aggregates
PRE_PUSH_HOOK = REPO / "scripts" / "hooks" / "pre-push"


def _portable_bash() -> str:
    git = Path(shutil.which("git") or "git")
    git_bash = git.parent.parent / "bin" / "bash.exe"
    if git_bash.is_file():
        return str(git_bash)
    if shell := shutil.which("bash"):
        return shell
    raise FileNotFoundError("bash is required to exercise the versioned pre-push hook")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _push_fixture(tmp_path: Path) -> tuple[Path, str, str, str]:
    repo = tmp_path / "push-fixture"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "contract@example.invalid")
    _git(repo, "config", "user.name", "Contract Test")

    gated_path = EXCLUDE_LIST.read_text(encoding="utf-8").split()[0]
    (repo / "scripts").mkdir()
    (repo / "scripts" / "_gated_exclude_list.txt").write_text(
        f"{gated_path}\n", encoding="utf-8"
    )
    (repo / "README.md").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "clean")
    clean_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    gated_file = repo / gated_path
    gated_file.parent.mkdir(parents=True, exist_ok=True)
    gated_file.write_text("synthetic gated fixture\n", encoding="utf-8")
    _git(repo, "add", "-f", gated_path)
    _git(repo, "commit", "-qm", "archive fixture")
    archive_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, gated_path, clean_sha, archive_sha


def _run_pre_push(repo: Path, ref: str, sha: str) -> subprocess.CompletedProcess[str]:
    payload = f"{ref} {sha} {ref} {'0' * 40}\n"
    return subprocess.run(
        [_portable_bash(), PRE_PUSH_HOOK.as_posix(), "origin", "unused"],
        cwd=repo,
        input=payload,
        capture_output=True,
        text=True,
    )


def test_gitignore_covers_every_gated_path_in_a_clean_clone(tmp_path: Path) -> None:
    repo = tmp_path / "ignore-fixture"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text(
        (REPO / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8"
    )
    gated = EXCLUDE_LIST.read_text(encoding="utf-8").split()
    for path in gated:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic gated fixture\n", encoding="utf-8")
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-z", "--stdin"],
        cwd=repo,
        input="\0".join(gated) + "\0",
        capture_output=True,
        text=True,
    )
    matched = {path for path in result.stdout.split("\0") if path}
    assert result.returncode == 0 and matched == set(gated), (
        "every gated path must be ignored by a clean clone; "
        f"missing={sorted(set(gated) - matched)}"
    )


def test_pre_push_rejects_archive_tip_with_gated_data(tmp_path: Path) -> None:
    repo, gated_path, _, archive_sha = _push_fixture(tmp_path)
    result = _run_pre_push(repo, "refs/heads/archive", archive_sha)
    assert result.returncode != 0
    assert gated_path in result.stderr


def test_pre_push_allows_clean_tip(tmp_path: Path) -> None:
    repo, _, clean_sha, _ = _push_fixture(tmp_path)
    result = _run_pre_push(repo, "refs/heads/main", clean_sha)
    assert result.returncode == 0, result.stderr


def test_every_large_parquet_is_gated() -> None:
    excluded = set(EXCLUDE_LIST.read_text(encoding="utf-8").split())
    tracked = subprocess.run(
        ["git", "ls-files", "*.parquet"], capture_output=True, text=True, cwd=REPO
    ).stdout.split()
    leaks = []
    for path in tracked:
        if path in excluded or path.startswith(FIXTURE_ALLOWED_PREFIXES):
            continue
        if (REPO / path).stat().st_size > AGGREGATE_MAX_BYTES:
            leaks.append(path)
    assert not leaks, (
        "Granular parquet(s) not registered in scripts/_gated_exclude_list.txt "
        f"(would leak to the public mirror): {leaks}"
    )


QUOTE_LEVEL_COLUMNS = {
    "bid",
    "ask",
    "midpoint",
    "sip_timestamp",
    "quote_time_utc",
    "provider_timestamp_ns",
    "premium",
    "trade_price",
}

#: The RP3 evaluation bank's shape: frozen forecasts next to realizations — the
#: comparison-READY dataset the one-read policy exists to keep sealed. An adversarial
#: review (2026-08-25) verified a bank parquet passes both rules above (tens of KB,
#: none of the quote-level columns), so its shape gets its own rule: any tracked
#: parquet or CSV carrying a frozen-forecast column beside a realization column is a
#: leak, wherever it sits in the tree.
BANK_SHAPE_COLUMNS = {"b1_plus_index", "signed_return_120"}


def granular_leaks(repo: Path, paths: list[str], *, excluded: set[str]) -> list[str]:
    """Return the parquet paths carrying quote-level columns that nobody registered.

    Size is a proxy for granularity and a poor one: a single session of option
    quotes compresses well below the aggregate threshold. Columns are the actual
    signal, and they are the same ones the CSV rule already uses.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    leaks = []
    for path in paths:
        if path in excluded or path.startswith(FIXTURE_ALLOWED_PREFIXES):
            continue
        target = repo / path
        if not target.exists():
            continue
        try:
            names = {name.lower() for name in pq.read_schema(target).names}
        except (OSError, pa.ArrowInvalid):
            # Unreadable cannot be certified as safe, so it counts as a leak.
            leaks.append(path)
            continue
        if names & QUOTE_LEVEL_COLUMNS or names & BANK_SHAPE_COLUMNS:
            leaks.append(path)
    return leaks


def test_no_quote_level_csv_reaches_the_mirror() -> None:
    """Row-level market data (real contracts, timestamps, prices) must be gated
    regardless of file size — found live in b1_iv_failures_20d.csv (2026-08-18)."""
    excluded = set(EXCLUDE_LIST.read_text(encoding="utf-8").split())
    tracked = subprocess.run(
        ["git", "ls-files", "*.csv"], capture_output=True, text=True, cwd=REPO
    ).stdout.split()
    leaks = []
    for path in tracked:
        if path in excluded or path.startswith(FIXTURE_ALLOWED_PREFIXES):
            continue
        with (REPO / path).open(encoding="utf-8", errors="replace") as handle:
            header = {column.strip().lower() for column in handle.readline().split(",")}
        if header & QUOTE_LEVEL_COLUMNS or header & BANK_SHAPE_COLUMNS:
            leaks.append(path)
    assert not leaks, (
        "CSV(s) with quote-level market data not registered in "
        f"scripts/_gated_exclude_list.txt: {leaks}"
    )


def test_pointers_cover_the_exclude_list() -> None:
    import json

    pointers = json.loads(
        (REPO / "data" / "GATED_DATA_POINTERS.json").read_text(encoding="utf-8")
    )
    pointer_paths = {entry["path"] for entry in pointers["files"]}
    excluded = set(EXCLUDE_LIST.read_text(encoding="utf-8").split())
    assert excluded == pointer_paths, (
        "exclude list and GATED_DATA_POINTERS.json disagree: "
        f"only-excluded={sorted(excluded - pointer_paths)} "
        f"only-pointers={sorted(pointer_paths - excluded)}"
    )


# ---------------------------------------------------------------------------
# Schema tripwire for parquet.
#
# The size rule above catches a large granular parquet. It cannot catch a small
# one: the six unregistered aggregates in this tree are 5 to 16 KB, so a single
# session of option trades would sit far under the 512 KB threshold and pass.
# CSVs already get a column check; parquet got none. These tests close that gap
# with synthetic fixtures, so the assertion does not depend on a granular file
# ever existing in the public line.
# ---------------------------------------------------------------------------


def _synthetic_parquet(path: Path, columns: dict[str, list[object]]) -> Path:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(columns), path)
    return path


def test_unregistered_granular_parquet_is_a_leak(tmp_path: Path) -> None:
    """A new per-contract parquet nobody registered must fail the gate."""
    _synthetic_parquet(
        tmp_path / "artifacts" / "new_capture" / "option_quotes.parquet",
        {"bid": [1.0], "ask": [1.2], "sip_timestamp": [1], "symbol": ["SPY"]},
    )
    leaks = granular_leaks(
        tmp_path, ["artifacts/new_capture/option_quotes.parquet"], excluded=set()
    )
    assert leaks == ["artifacts/new_capture/option_quotes.parquet"]


def test_small_granular_parquet_is_still_a_leak(tmp_path: Path) -> None:
    """Below the size threshold is not below the licence."""
    target = _synthetic_parquet(
        tmp_path / "artifacts" / "new_capture" / "trades.parquet",
        {"premium": [900.0], "trade_price": [1.5]},
    )
    assert target.stat().st_size < AGGREGATE_MAX_BYTES, "fixture must be under the size rule"
    assert granular_leaks(tmp_path, ["artifacts/new_capture/trades.parquet"], excluded=set())


def test_registered_granular_parquet_is_not_a_leak(tmp_path: Path) -> None:
    """Correctly registered is the contractual path, and must stay quiet."""
    _synthetic_parquet(
        tmp_path / "artifacts" / "new_capture" / "option_quotes.parquet",
        {"bid": [1.0], "ask": [1.2]},
    )
    path = "artifacts/new_capture/option_quotes.parquet"
    assert granular_leaks(tmp_path, [path], excluded={path}) == []


def test_aggregate_parquet_is_not_a_leak(tmp_path: Path) -> None:
    """The six unregistered aggregates in this tree must keep passing."""
    _synthetic_parquet(
        tmp_path / "artifacts" / "methodology" / "stability.parquet",
        {"model": ["har"], "rank": [1], "score": [0.5]},
    )
    aggregate = ["artifacts/methodology/stability.parquet"]
    assert granular_leaks(tmp_path, aggregate, excluded=set()) == []


def test_fixture_prefix_stays_exempt(tmp_path: Path) -> None:
    """The synthetic pilot_preview fixtures are shaped like real data on purpose."""
    path = "artifacts/pilot_preview/fixture_20260721/option_quotes.parquet"
    _synthetic_parquet(tmp_path / path, {"bid": [1.0], "ask": [1.2]})
    assert granular_leaks(tmp_path, [path], excluded=set()) == []


def test_public_line_has_no_unregistered_granular_parquet() -> None:
    """The live assertion: run the schema rule over what is actually tracked."""
    excluded = set(EXCLUDE_LIST.read_text(encoding="utf-8").split())
    tracked = subprocess.run(
        ["git", "ls-files", "*.parquet"], capture_output=True, text=True, cwd=REPO
    ).stdout.split()
    leaks = granular_leaks(REPO, tracked, excluded=excluded)
    assert not leaks, (
        "Parquet(s) carrying quote-level columns and not registered in "
        f"scripts/_gated_exclude_list.txt: {leaks}"
    )
