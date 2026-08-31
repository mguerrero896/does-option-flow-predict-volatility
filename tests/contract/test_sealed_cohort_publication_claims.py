"""Published Phase 8 counts must agree with the versioned custody evidence."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from tests.withdrawn_claims import carries_supersession_notice, normalize

REPO = Path(__file__).resolve().parents[2]
RESULT = REPO / "artifacts/phase8_bridge/result_20260830_v1.json"
CUSTODY = REPO / "artifacts/phase8_bridge/one_shot_custody_20260830_v3.json"
AUTHORIZATION = REPO / "artifacts/phase8_bridge/owner_authorization_20260830_v1.json"
DISPOSITION = REPO / "docs/sealed_cohorts_disposition_v1.md"

# Chronological registers retain earlier states so later decisions remain auditable.
REGISTERS = {"docs/methodology_decisions.md"}
PHASE8 = re.compile(r"\bphase\s*8\b", re.IGNORECASE)
SESSION_COUNT = re.compile(r"\b(\d+)\s*(?:of|/)\s*(\d+)\b", re.IGNORECASE)
READ_COUNTS = (
    re.compile(r"\bsealed_cohorts_reads?\s*=\s*(\d+|zero|one)\b", re.IGNORECASE),
    re.compile(r"\bread_count\s*=\s*(\d+|zero|one)\b", re.IGNORECASE),
    re.compile(r"\b(\d+|zero|one)\s+scientific\s+reads?\b", re.IGNORECASE),
    re.compile(r"\breads?\s+(?:remain(?:s)?|=|:)\s*(\d+|zero|one)\b", re.IGNORECASE),
)
SESSION_WORD_COUNTS = (
    re.compile(r"\b(\d+)\s+sessions?\b", re.IGNORECASE),
    re.compile(r"\bsessions?\s*(?:=|:)\s*(\d+)\b", re.IGNORECASE),
)
SCOPED_SNAPSHOTS = (
    "during rp2-v3 development",
    "at this run's execution snapshot",
    "at this run’s execution snapshot",
)


def _carries_lifecycle_notice(text: str) -> bool:
    head = normalize("\n".join(text.splitlines()[:25]))
    return carries_supersession_notice(text) or "historical_measurement_not_current_claim" in head


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _phase8_evidence() -> tuple[int, int]:
    result = _load(RESULT)
    custody = _load(CUSTODY)
    authorization = _load(AUTHORIZATION)

    session_counts = {
        result["store_preflight"]["completed_count"],
        result["store_preflight"]["sessions"],
    }
    read_counts = {
        result["sealed_cohorts_read"],
        custody["sealed_cohorts_read_after"],
        custody["access_ledger"]["read_count"],
    }
    assert len(session_counts) == 1, f"Phase 8 session evidence disagrees: {session_counts}"
    assert len(read_counts) == 1, f"Phase 8 read evidence disagrees: {read_counts}"
    assert authorization["authorize_read_and_evaluation"] is True
    assert authorization["sealed_cohorts_read_before"] == custody["sealed_cohorts_read_before"] == 0
    assert custody["output"]["overall_classification"] == "MIXED_EXPLORATORY"
    return session_counts.pop(), read_counts.pop()


def _tracked_markdown() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "README.md", "STATUS.md", "docs", "reports", "specs"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(path for path in result.stdout.splitlines() if path.endswith(".md"))


def _as_int(value: str) -> int:
    return int(value) if value.isdigit() else {"zero": 0, "one": 1}[value.lower()]


def _table_contradictions(text: str, sessions: int, reads: int) -> list[str]:
    contradictions: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        folded = [normalize(cell) for cell in cells]
        if not {"cohort", "acquired", "scientific reads"}.issubset(folded):
            continue
        columns = {name: folded.index(name) for name in ("cohort", "acquired", "scientific reads")}
        for row in lines[index + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            values = [cell.strip() for cell in row.strip().strip("|").split("|")]
            if len(values) != len(cells) or not PHASE8.search(values[columns["cohort"]]):
                continue
            acquired = SESSION_COUNT.search(values[columns["acquired"]])
            observed_reads = re.search(
                r"\b(\d+|zero|one)\b", values[columns["scientific reads"]], re.I
            )
            if acquired and tuple(map(int, acquired.groups())) != (sessions, sessions):
                contradictions.append(f"table acquired={acquired.group(0)}")
            if observed_reads and _as_int(observed_reads.group(1)) != reads:
                contradictions.append(f"table scientific reads={observed_reads.group(1)}")
    return contradictions


def _contradictions(text: str, sessions: int, reads: int) -> list[str]:
    contradictions = _table_contradictions(text, sessions, reads)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        phase_mentions = list(PHASE8.finditer(line))
        if not phase_mentions:
            continue
        context = normalize(" ".join(lines[max(0, index - 1) : index + 3]))
        if any(marker in context for marker in SCOPED_SNAPSHOTS):
            continue
        for match in SESSION_COUNT.finditer(line):
            observed, total = map(int, match.groups())
            count_words = re.search(r"\b(?:sessions?|acquired|completed)\b", line, re.I)
            if total != sessions and not count_words:
                continue
            if (observed, total) != (sessions, sessions):
                contradictions.append(f"line {index + 1}: sessions={match.group(0)}")
        for pattern in SESSION_WORD_COUNTS:
            for match in pattern.finditer(line):
                if any(
                    start <= match.start(1) < end
                    for start, end in (mention.span() for mention in phase_mentions)
                ):
                    continue
                if int(match.group(1)) != sessions:
                    contradictions.append(f"line {index + 1}: sessions={match.group(1)}")
        for pattern in READ_COUNTS:
            for match in pattern.finditer(line):
                value = next(group for group in match.groups() if group is not None)
                if _as_int(value) != reads:
                    contradictions.append(f"line {index + 1}: reads={value}")
    return contradictions


def test_versioned_phase8_evidence_agrees() -> None:
    assert _phase8_evidence() == (30, 1)


def test_published_phase8_counts_are_current_or_clearly_historical() -> None:
    sessions, reads = _phase8_evidence()
    failures = []
    for relative in _tracked_markdown():
        if relative in REGISTERS:
            continue
        text = (REPO / relative).read_text(encoding="utf-8")
        contradictions = _contradictions(text, sessions, reads)
        if contradictions and not _carries_lifecycle_notice(text):
            failures.append(f"{relative}: {', '.join(contradictions)}")
    assert not failures, (
        "published documents contradict the versioned Phase 8 session/read evidence "
        "without a lifecycle notice near the top:\n" + "\n".join(failures)
    )


def test_disposition_opens_with_the_phase8_lifecycle_reconciliation() -> None:
    sessions, reads = _phase8_evidence()
    head = normalize("\n".join(DISPOSITION.read_text(encoding="utf-8").splitlines()[:25]))
    required = (
        "phase 8 inventory row",
        "superseded on 2026-08-30",
        f"{sessions}/{sessions}",
        f"{reads} authorized scientific read",
        "mixed_exploratory",
        "decision 102",
        "owner_authorization_20260830_v1.json",
        "one_shot_custody_20260830_v3.json",
        "result_20260830_v1.json",
        "architecture.md",
    )
    assert carries_supersession_notice(head)
    assert not [phrase for phrase in required if phrase not in head]


@pytest.mark.parametrize(
    "claim",
    (
        "Phase 8 acquired 29 of 30 sessions.",
        "Phase 8 sessions=29.",
        "Phase 8 sealed_cohorts_read=0.",
        "Phase 8 completed with zero scientific reads.",
    ),
)
def test_guardian_recognises_contradictory_count_spellings(claim: str) -> None:
    assert _contradictions(claim, 30, 1)
