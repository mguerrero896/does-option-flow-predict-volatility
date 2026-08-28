"""Every tracked source file says what it looks like it says.

Three defects of one shape reached this repository: a regex whose `\b` had become a literal
U+0008 so the scan matched nothing and passed, a SQL separator whose `E'\n'` had become a
line break so what joined two records depended on the checkout's line endings, and a
generated module whose `"\n".join(...)` had become an unterminated string. All three came
from writing source through a layer that processes escapes, and none of them is visible by
reading the diff.

Each has its own detector, because each survives the others.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: Text a human writes and a machine parses. Binary and data files are excluded: a parquet
#: is full of bytes below 0x20 and means nothing by it.
TEXT_SUFFIXES = frozenset({".py", ".sql", ".md", ".json", ".yml", ".yaml", ".toml", ".txt"})

#: Tab, newline and carriage return are how text is laid out. Everything else below 0x20 is
#: an escape that was resolved one layer too early.
ALLOWED_CONTROL = frozenset({0x09, 0x0A, 0x0D})


def _tracked(suffixes: frozenset[str], *, at_least: int) -> list[Path]:
    """Tracked files of these kinds, with a floor each caller sets for itself.

    A scan reports nothing when the tree is clean and when the scan is broken, so every one
    of these tests states how many files it expects to look at. The floor belongs to the
    caller: this repository has hundreds of Python files and two SQL files, and a single
    threshold would either wave the narrow scans through or fail on them forever.
    """

    listed = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    assert len(listed) > 200, f"git listed {len(listed)} files, which is not this repository"
    files = [REPO / name for name in listed if Path(name).suffix in suffixes]
    found = [path for path in files if path.is_file()]
    assert len(found) >= at_least, f"expected at least {at_least} files, scanned {len(found)}"
    return found


def test_no_source_file_carries_a_resolved_escape() -> None:
    """A `\b` that became U+0008 disarmed a scan for two rounds without failing anything."""

    offenders: list[str] = []
    for path in _tracked(TEXT_SUFFIXES, at_least=200):
        raw = path.read_bytes()
        for offset, byte in enumerate(raw):
            if byte < 0x20 and byte not in ALLOWED_CONTROL:
                line = raw[:offset].count(b"\n") + 1
                offenders.append(f"{path.relative_to(REPO)}:{line} contains {byte:#04x}")
                break
    assert not offenders, "control characters where an escape was meant:\n" + "\n".join(offenders)


def test_every_python_file_parses() -> None:
    """An escape resolved inside a string literal usually ends it early."""

    broken: list[str] = []
    for path in _tracked(frozenset({".py"}), at_least=150):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as error:
            broken.append(f"{path.relative_to(REPO)}:{error.lineno}: {error.msg}")
    assert not broken, "files that do not parse:\n" + "\n".join(broken)


def test_no_sql_escape_literal_spans_a_line() -> None:
    """`E'` followed by a line break is valid SQL and is never what was written.

    PostgreSQL reads `E'...'` as an escape string, so `E'\n'` is a newline and a literal
    line break inside the quotes is *also* a newline — plus a carriage return on a CRLF
    checkout. The two are indistinguishable in a diff and not in behaviour.
    """

    # E only opens an escape literal when it is NOT part of a word: `NEGATIVE',`
    # ends with E + a CLOSING quote and is fine; `statements, E'` at end of line
    # is the corruption this guards against. The lookbehind encodes that lexing
    # rule; without it every string ending in ...E false-positived (2026-08-25,
    # first time the test ever saw the verbatim applied migrations).
    unterminated = re.compile(r"(?<![A-Za-z0-9_])E'[^']*$")
    offenders = [
        f"{path.relative_to(REPO)}:{number}"
        for path in _tracked(frozenset({".sql"}), at_least=2)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if unterminated.search(line)
    ]
    assert not offenders, "escape literals broken across lines:\n" + "\n".join(offenders)


def test_shell_scripts_have_no_carriage_returns_in_the_working_tree() -> None:
    """`.gitattributes` declares `*.sh text eol=lf`; this checks the file ON DISK.

    An attribute added after a file was already checked out does not re-smudge it.
    On 2026-08-26 `scripts/publish_mirror.sh` still carried 98 CRLF line endings in
    the working copy while its committed blob was clean LF, and `git status` called
    it unmodified. bash tolerated the trailing CR on that machine; the audit finding
    this rule exists for is that elsewhere it does not.
    """
    carriage_return = bytes([13])
    offenders = [
        str(path.relative_to(REPO))
        for path in sorted(REPO.glob("scripts/*.sh"))
        if carriage_return in path.read_bytes()
    ]
    assert not offenders, (
        "shell scripts carry CR bytes on disk despite `*.sh text eol=lf`; the "
        "attribute does not re-smudge an existing checkout. Fix with "
        "`rm <file> && git checkout -- <file>`: " + ", ".join(offenders)
    )
