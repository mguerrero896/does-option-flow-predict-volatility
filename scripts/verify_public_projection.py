"""Verify a clean public candidate without refitting research models or writing remote refs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SPANISH_TEXT = (
    "el los las del una uno unos unas para por con sin sobre esta este estos estas "
    "son fue fueron tiene tienen sigue siguen quedó queda antes después mismo misma "
    "sesiones resultados muestra ventana primario secundaria hipótesis prueba flujo "
    "figuras registro decisión evaluación pendiente fuera puede nunca ningún "
    "lectura reproducir alcance fuente fuentes datos conjunto además embargo cerrado"
)
ENGLISH_TEXT = (
    "the and of to in is are was were this that these those with without from for "
    "has have had remains remain before after same results sample window primary "
    "secondary hypothesis test flow figures registration decision evaluation pending "
    "outside can never reading reproduce scope source sources data set however closed"
)
SPANISH, ENGLISH = set(SPANISH_TEXT.split()), set(ENGLISH_TEXT.split())
INTERNAL_LABEL = re.compile(r"\b(?:mds650|capstone|codex|claude|chatgpt)\b", re.I)


def prose_text(text: str) -> str:
    """Exclude executable examples and link destinations from human prose."""
    text = re.sub(r"```.*?```|<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"\bmds650\.[a-z_][a-z0-9_.]*", " ", text)
    text = re.sub(r"\bsrc/mds650\b", " ", text)
    text = re.sub(r"\b(?:src/)?mds650/[a-zA-Z0-9_./-]+", " ", text)
    return re.sub(r"`[^`]*`|https?://\S+|\]\([^)]*\)", " ", text)


def language_counts(text: str) -> tuple[int, int]:
    """Conservative prose inventory; short or mixed documents also need review."""
    words = re.findall(r"[a-záéíóúüñ]+", prose_text(text).lower())
    return sum(word in SPANISH for word in words), sum(word in ENGLISH for word in words)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="Verification logs and receipt"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    if output.is_relative_to(root):
        parser.error("Logs must be outside the candidate to keep its checked tree clean")
    output.mkdir(parents=True, exist_ok=True)

    def git(*arguments: str) -> str:
        return subprocess.check_output(["git", *arguments], cwd=root, text=True).strip()

    if git("status", "--porcelain"):
        raise SystemExit("PUBLIC_CANDIDATE_MUST_BE_CLEAN")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"], cwd=root, check=True
    )
    documents = [
        name for name in git("ls-files").splitlines()
        if name.endswith(".md") or ".md.original" in name
    ]
    language = []
    internal_labels = []
    for name in documents:
        content = (root / name).read_text("utf-8-sig")
        if INTERNAL_LABEL.search(prose_text(content)):
            internal_labels.append(name)
        if name.startswith("docs/archive/"):
            continue
        spanish, english = language_counts(content)
        if spanish >= 5 and spanish > english:
            language.append({"path": name, "spanish_tokens": spanish, "english_tokens": english})
    commands = [
        [
            "-m",
            "pytest",
            "-q",
            "tests/test_gated_history_contract.py",
            "tests/test_mirror_internal_docs_contract.py",
            "tests/contract",
            "--junitxml=" + str(output / "contracts.xml"),
        ],
        ["scripts/scan_public_secrets.py", "--include-tags"],
    ]
    checks = []
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("MDS650_") and key not in {"PYTHONPATH", "MYPYPATH"}
    }
    environment.update(MDS650_PANEL_GUARD_MAY_SKIP="1", MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP="1")
    for index, command in enumerate(commands):
        result = subprocess.run(
            [sys.executable, *command], cwd=root, capture_output=True, check=False, env=environment
        )
        log = result.stdout + result.stderr
        (output / f"check_{index}.log").write_bytes(log)
        public_command = [
            part.split("=", 1)[0] + "=contracts.xml" if part.startswith("--junitxml=") else part
            for part in command
        ]
        checks.append(
            {
                "command": ["python", *public_command],
                "exit_code": result.returncode,
                "log_sha256": hashlib.sha256(log).hexdigest(),
            }
        )
        print(f"check {index}: exit {result.returncode}", flush=True)
    receipt = {
        "schema_version": "public-projection-verification-v1",
        "candidate": git("rev-parse", "HEAD"),
        "base": git("rev-parse", "origin/main"),
        "ancestor_preserved": True,
        "clean_tree": not git("status", "--porcelain"),
        "checks": checks,
        "markdown_documents": len(documents),
        "language_method": "Common-word screening; translation receipts verify numeric claims",
        "spanish_majority_documents_outside_archive": language,
        "internal_labels_in_markdown_prose": internal_labels,
        "remote_writes": 0,
        "scientific_model_fits": 0,
        "synthetic_fixtures_may_fit_models": True,
        "prospective_data_reads": 0,
        "licensed_evidence_mounted": False,
        "declared_public_tier_optouts": ["PANEL_GUARD_MAY_SKIP", "UW_LATENCY_FRESHNESS_MAY_SKIP"],
    }
    receipt["status"] = (
        "PASS"
        if (
            receipt["clean_tree"] and not language and not internal_labels
            and all(row["exit_code"] == 0 for row in checks)
        )
        else "FAIL"
    )
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", "utf-8")
    print(json.dumps(receipt, indent=2))
    if receipt["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
