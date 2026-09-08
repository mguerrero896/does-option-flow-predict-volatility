"""Read-only reference inventory and byte-custody checks; no model imports."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PINS = dict(
    [
        (
            "docs/rp4/RESULTADO_FINAL.md",
            "6d629b2416601af39a6e7f4fc0f04db1455b6c20ba4c298e7fb21a6ed00b2b19",
        ),
        (
            "docs/rp4/data_and_execution_v1.md",
            "33f1ecc18aedc6ef0831bf237da4db4be0edf531a6421329b507bff82ef7f6dd",
        ),
        (
            "docs/rp4/results_v2.md",
            "8e940aac0660c5027b1ffd4b7d9abcf59ec8fe2e2156d7010b18a227b459a4cf",
        ),
        (
            "docs/rp4/results_v3.md",
            "86703434ae2d1d8e2ef3a9c59ae9737f3a4e4c8460234076b794e04ac2deee1f",
        ),
        (
            "docs/rp4/results_v3_revision2.md",
            "05f263b019a74a8591f3840d69aa86947f5cc9bf343eb85d5a30601e8a0f142e",
        ),
        (
            "artifacts/rp4_v3_a1_empty_window/specification.json",
            "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5",
        ),
        (
            "artifacts/rp4_v3_a2/evaluation_release.json",
            "5e3046af023c9f41380307d62537aa4e8fc7514b23d51a95ea1f960ee23fe5bb",
        ),
        (
            "artifacts/rp4_v3_b2/receipt.json",
            "60c6f893a9f1b3f23b6737e6f022766e5a603b4225b4292359337356288178af",
        ),
        (
            "artifacts/rp4_v3_b3/receipt.json",
            "698cd3067258f95c2ca3573618cda88f9fa1d3fda339def0f1455337767ac635",
        ),
        (
            "artifacts/rp4_v4_a1/specification.json",
            "0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04",
        ),
        (
            "artifacts/rp4_v4_a2/evaluation_release_rv15.json",
            "7b5499579a66a468f040966d22824501ec1c65c29fefb848b40366bfd1f2351a",
        ),
        (
            "artifacts/rp4_v4_a2/evaluation_release_rv5.json",
            "efeb22b33d992d453a4d766c93b5434e4f3f73271f350b50268a8289c365b08d",
        ),
        (
            "artifacts/rp4_v4_b2_rv15/receipt.json",
            "d67cb9611e4630accba768b1a25bfbb04768702d4c2da8e78a17ab63cc5a8b93",
        ),
        (
            "artifacts/rp4_v4_b3_rv15/receipt.json",
            "b8b5571b8d251ffcb0a458f2404b363bb2fc519402c880c4ccad6e6fa3108ecb",
        ),
        (
            "artifacts/rp4_v4_b2_rv5/receipt.json",
            "737ca5daa6f9d06cc212dee2449944fae87aba8ca51e2940a313c22f2b612365",
        ),
        (
            "artifacts/rp4_v4_b3_rv5/receipt.json",
            "556ef30116e9756ac553116fdd3bd48b96f5b4543a39d0ec63f4a5cc0634a769",
        ),
        (
            "artifacts/rp4_v4_b4/timing.csv",
            "b23fcdcc6ffcabb088176e678a95829ea255b9db148d47fe448958112658e483",
        ),
        (
            "artifacts/rp4_closeout_audit/b2_coefficient_summary.csv",
            "150fdf4398072496ef64547df580053907a117921d2c214f9b3c82446254e9be",
        ),
        (
            "artifacts/rp4_closeout_audit/b2_presence_coefficient_summary.csv",
            "9d4fc01b00af2ea25ab34b44276c481cf963be83edcc8f4b31ad114e1e6ab5e7",
        ),
        (
            "uv.lock",
            "960c8a2638cdf39be44acb6d06b0e355eceab4e6658357f089f2b9aa159d61d0",
        ),
    ]
)
RECEIPTS = (
    ("rp4_v3_b2", "rp4_v3_a2/evaluation_release.json"),
    ("rp4_v3_b3", "rp4_v3_a2/evaluation_release.json"),
    ("rp4_v4_b2_rv15", "rp4_v4_a2/evaluation_release_rv15.json"),
    ("rp4_v4_b3_rv15", "rp4_v4_a2/evaluation_release_rv15.json"),
    ("rp4_v4_b2_rv5", "rp4_v4_a2/evaluation_release_rv5.json"),
    ("rp4_v4_b3_rv5", "rp4_v4_a2/evaluation_release_rv5.json"),
)


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git(
    args: list[str],
    records: list[dict[str, Any]],
    repository: Path | None = None,
    alias: str = "checkout_current",
) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repository or ROOT, capture_output=True, check=False
    )
    allowed = (0, 1) if args[0] == "merge-base" else (0,)
    records.append(
        {
            "command": "git " + " ".join(args),
            "working_directory_alias": alias,
            "exit_code": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        }
    )
    if result.returncode not in allowed:
        raise RuntimeError("READ_ONLY_GIT_CHECK_FAILED")
    if args[0] == "merge-base":
        return str(result.returncode)
    return result.stdout.decode("utf-8").strip()


def artifact_owner(relative: str) -> str | None:
    parts = Path(relative).parts
    if len(parts) > 1 and parts[0] == "artifacts" and parts[1].startswith("rp4_"):
        return parts[1]
    return None


def related_repository(path: Path, alias: str) -> dict[str, Any]:
    """Enumerate related Git metadata without changing any checkout."""
    result: dict[str, Any] = {
        "alias": alias,
        "path_sha256": digest_text(str(path.resolve())),
        "exists": path.is_dir(),
        "deletion_authorized": False,
    }
    if not path.is_dir():
        result["status"] = "NO VERIFICABLE: directory absent"
        return result
    commands: list[dict[str, Any]] = []

    def read(args: list[str]) -> str:
        return git(args, commands, path, alias)

    head = read(["rev-parse", "HEAD"])
    upstream = read(["rev-parse", "origin/main"])
    common = read(["rev-parse", "--git-common-dir"])
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = path / common_path
    worktrees: list[dict[str, Any]] = []
    for block in read(["worktree", "list", "--porcelain"]).split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        if "worktree" in fields:
            worktrees.append(
                {
                    "alias": f"{alias}_checkout_{len(worktrees) + 1:02d}",
                    "path_sha256": digest_text(str(Path(fields["worktree"]).resolve())),
                    "head": fields.get("HEAD"),
                    "rp4_branch": "rp4" in fields.get("branch", "").lower(),
                    "deletion_authorized": False,
                }
            )
    branches: list[dict[str, Any]] = []
    for row in read(["for-each-ref", "--format=%(refname)|%(objectname)"]).splitlines():
        ref, tip = row.split("|", 1)
        if "rp4" not in ref.lower():
            continue
        branches.append(
            {
                "alias": f"{alias}_branch_{len(branches) + 1:02d}",
                "ref_sha256": digest_text(ref),
                "kind": "local" if ref.startswith("refs/heads/") else "remote_tracking",
                "tip": tip,
                "merged_into_this_repository_head": read(["merge-base", "--is-ancestor", tip, head])
                == "0",
                "merged_into_this_local_origin_main": read(
                    ["merge-base", "--is-ancestor", tip, upstream]
                )
                == "0",
                "deletion_authorized": False,
            }
        )
    result.update(
        {
            "status": "METADATA_ENUMERATED",
            "head": head,
            "local_origin_main": upstream,
            "git_common_directory_sha256": digest_text(str(common_path.resolve())),
            "worktrees": worktrees,
            "rp4_branches": branches,
            "commands": commands,
            "content_scan_performed": False,
        }
    )
    return result


def scan_inventory(
    physical_root: Path | None = None,
    related_roots: list[Path] | None = None,
) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    head = git(["rev-parse", "HEAD"], commands)
    upstream = git(["rev-parse", "origin/main"], commands)
    worktrees_raw = git(["worktree", "list", "--porcelain"], commands)
    refs_raw = git(["for-each-ref", "--format=%(refname)|%(objectname)|%(upstream)"], commands)
    branches: list[dict[str, Any]] = []
    for raw in refs_raw.splitlines():
        ref, tip, _ = raw.split("|", 2)
        if "rp4" not in ref.lower():
            continue
        branches.append(
            {
                "alias": f"branch_{len(branches) + 1:02d}",
                "leaf": ref.rsplit("/", 1)[-1],
                "kind": "local" if ref.startswith("refs/heads/") else "remote_tracking",
                "tip": tip,
                "merged_into_snapshot_head": git(
                    ["merge-base", "--is-ancestor", tip, head], commands
                )
                == "0",
                "merged_into_local_origin_main": git(
                    ["merge-base", "--is-ancestor", tip, upstream], commands
                )
                == "0",
                "deletion_authorized": False,
            }
        )
    worktrees: list[dict[str, Any]] = []
    for block in worktrees_raw.split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        if "worktree" in fields:
            worktrees.append(
                {
                    "alias": f"checkout_{len(worktrees) + 1:02d}",
                    "path_sha256": digest_text(fields["worktree"]),
                    "head": fields.get("HEAD"),
                    "current": Path(fields["worktree"]).resolve() == ROOT,
                    "deletion_authorized": False,
                }
            )
    raw_files = git(["ls-files", "-z", "--cached", "--others", "--exclude-standard"], commands)
    files = sorted(set(raw_files.split("\0")) - {""})
    candidates = sorted(
        item.name
        for item in (ROOT / "artifacts").iterdir()
        if item.is_dir() and item.name.startswith("rp4_") and item.name != "rp4_cleanup_review"
    )
    inbound: dict[str, list[dict[str, Any]]] = {name: [] for name in candidates}
    metadata_counts = dict.fromkeys(candidates, 0)
    excluded: dict[str, int] = {}
    scanned: list[dict[str, Any]] = []
    literal_counts: dict[str, int] = {}
    # Source control lists filenames only. Content scope excludes secrets, raw inputs,
    # hidden directories, large generated records and this review's own references.
    extensions = {".json", ".md", ".py", ".toml", ".yaml", ".yml", ".ps1"}
    for relative in files:
        path = ROOT / relative
        parts = Path(relative).parts
        reason = None
        if relative.startswith("artifacts/rp4_cleanup_review/") or relative in {
            "docs/rp4/RUNBOOK.md",
            "docs/rp4/CLEANUP_REVIEW.md",
        }:
            reason = "review_self_reference"
        elif any(part.startswith(".") for part in parts):
            reason = "hidden_path"
        elif path.suffix.lower() not in extensions:
            reason = "non_text_metadata_extension"
        elif any(
            token in path.name.lower()
            for token in ("secret", "credential", "license", "licence", "token", "cookie")
        ):
            reason = "sensitive_filename"
        elif any(
            part.lower() in {"raw", "targets", "data", "sessions", "components"} for part in parts
        ):
            reason = "input_or_checkpoint_directory"
        elif not path.is_file():
            reason = "missing_or_nonfile"
        elif path.stat().st_size > 4 * 1024 * 1024:
            reason = "larger_than_4_mib"
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        payload = path.read_bytes()
        try:
            content = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            excluded["not_utf8"] = excluded.get("not_utf8", 0) + 1
            continue
        alias = f"reference_{len(scanned) + 1:05d}"
        source = {
            "alias": alias,
            "path_sha256": digest_text(relative),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "owner": artifact_owner(relative),
            "json_metadata": path.suffix.lower() == ".json",
        }
        scanned.append(source)
        owner = artifact_owner(relative)
        if owner in metadata_counts and source["json_metadata"]:
            metadata_counts[owner] += 1
        referenced = set(re.findall(r"\brp4_[A-Za-z0-9_]+\b", content))
        for name in referenced:
            literal_counts[name] = literal_counts.get(name, 0) + 1
        for name in referenced.intersection(inbound):
            if name != owner:
                inbound[name].append(source)
    directory_inventory = []
    for name in candidates:
        refs = inbound[name]
        directory_inventory.append(
            {
                "path": f"artifacts/{name}",
                "inbound_reference_files": len(refs),
                "inbound_json_reference_files": sum(r["json_metadata"] for r in refs),
                "own_scanned_json_files": metadata_counts[name],
                "reference_examples": refs[:5],
                "classification": (
                    "REFERENCED_KEEP"
                    if refs
                    else "NO_LITERAL_INBOUND_IN_SCANNED_SCOPE_REVIEW_REQUIRED"
                ),
                "orphan_confirmed": False,
                "deletion_authorized": False,
            }
        )
    scan_stream = "\n".join(f"{entry['path_sha256']} {entry['sha256']}" for entry in scanned)
    physical: list[dict[str, Any]] = []
    if physical_root is not None and physical_root.is_dir():
        for path in sorted(physical_root.iterdir()):
            if not path.is_dir() or not path.name.startswith("rp4_"):
                continue
            children = list(path.iterdir())
            physical.append(
                {
                    "alias": f"physical_artifact_{len(physical) + 1:02d}",
                    "path_sha256": digest_text(str(path.resolve())),
                    "name_sha256": digest_text(path.name),
                    "immediate_file_count": sum(p.is_file() for p in children),
                    "immediate_directory_count": sum(p.is_dir() for p in children),
                    "current_checkout_literal_reference_files": literal_counts.get(path.name, 0),
                    "reference_status": "NO VERIFICABLE: global reference scan incomplete",
                    "contents_read": False,
                    "orphan_confirmed": False,
                    "deletion_authorized": False,
                }
            )
    related = [
        related_repository(path, f"related_repository_{index + 1:02d}")
        for index, path in enumerate(related_roots or [])
    ]
    return {
        "schema": "rp4-cleanup-review-v1",
        "created_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "scope": "current text references; separate related Git and physical directory censuses",
        "head": head,
        "local_origin_main": upstream,
        "remote_ref_refresh_performed": False,
        "global_worktree_inventory_complete": False,
        "global_reference_graph_complete": False,
        "limitations": [
            "No separate clones, external private manifests or historical objects scanned.",
            "Dynamic path construction and content inside excluded files are not resolved.",
            "Zero literal references is not evidence of safe deletion.",
            "Ancestry is not authority to delete scientific records.",
        ],
        "worktrees": worktrees,
        "branches": branches,
        "related_repositories": related,
        "physical_artifact_census": {
            "root_alias": "physical_artifacts_root",
            "root_path_sha256": digest_text(str(physical_root.resolve()))
            if physical_root is not None
            else None,
            "root_exists": physical_root.is_dir() if physical_root is not None else False,
            "directories": physical,
            "status": "METADATA_ONLY_NO_DELETION_AUTHORITY",
        },
        "reference_scan": {
            "tracked_and_untracked_filenames": len(files),
            "scanned_text_files": len(scanned),
            "scanned_json_files": sum(r["json_metadata"] for r in scanned),
            "excluded_counts": excluded,
            "sorted_source_digest_sha256": digest_text(scan_stream),
            "matching": "exact literal directory token; external owner only; no self links",
        },
        "directories": directory_inventory,
        "pinned_sources_sha256": PINS,
        "commands": commands,
        "model_fits": 0,
        "inference_runs": 0,
        "files_deleted": 0,
        "git_mutations": 0,
        "maximum_threads": 1,
        "status": "REVIEW_ONLY_NOT_A_DELETION_AUTHORIZATION",
    }


def verify(licensed: bool) -> dict[str, Any]:
    checked: dict[str, dict[str, str]] = {}
    failures: list[str] = []
    skipped_private = 0

    def check(path: Path, expected: str, alias: str) -> None:
        nonlocal skipped_private
        path = path if path.is_absolute() else ROOT / path
        if not licensed and not path.is_relative_to(ROOT):
            skipped_private += 1
            return
        observed = sha(path) if path.is_file() else "MISSING"
        checked[alias] = {"expected": expected, "observed": observed}
        if observed != expected:
            failures.append(alias)

    for name, expected in PINS.items():
        check(ROOT / name, expected, name)
    for directory, release_name in RECEIPTS:
        receipt_name = f"artifacts/{directory}/receipt.json"
        if receipt_name in failures:
            continue
        receipt = json.loads((ROOT / receipt_name).read_text(encoding="utf-8"))
        if receipt.get("status") != "COMPLETE" or receipt.get("exit_code") != 0:
            failures.append(f"{directory}/NOT_COMPLETE")
            continue
        release_path = ROOT / "artifacts" / release_name
        check(release_path, receipt["release_sha256"], f"{directory}/release")
        for index, (name, expected) in enumerate(receipt["artifacts_sha256"].items()):
            check(Path(name), expected, f"{directory}/result_{index:02d}")
        for index, (name, expected) in enumerate(receipt["evaluation_code_sha256"].items()):
            check(ROOT / name, expected, f"{directory}/code_{index:02d}")
        for index, command in enumerate(receipt["commands"]):
            if command["exit_code"] != 0:
                failures.append(f"{directory}/command_{index:02d}")
            check(
                Path(command["log"]),
                command["log_sha256"],
                f"{directory}/log_{index:02d}",
            )
    timing = list(
        csv.DictReader(
            (ROOT / "artifacts/rp4_v4_b4/timing.csv").read_text(encoding="utf-8-sig").splitlines()
        )
    )
    return {
        "status": "PASS" if not failures else "FAIL",
        "mode": "licensed_byte_custody" if licensed else "public_byte_custody",
        "checked_files": len(checked),
        "checks": checked,
        "private_hash_checks_skipped": skipped_private,
        "failures": failures,
        "timing_rows": len(timing),
        "coverage": (
            "Pinned specifications, releases, receipts, result files, code and logs; "
            "no checkpoint graph, panel contents, runtime import or statistical recomputation."
        ),
        "model_fits": 0,
        "inference_runs": 0,
        "files_written": 0,
        "maximum_threads": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inventory", action="store_true")
    group.add_argument("--verify-public", action="store_true")
    group.add_argument("--verify-licensed", action="store_true")
    parser.add_argument("--physical-artifacts-root", type=Path)
    parser.add_argument("--related-repository", type=Path, action="append", default=[])
    args = parser.parse_args()
    result = (
        scan_inventory(args.physical_artifacts_root, args.related_repository)
        if args.inventory
        else verify(args.verify_licensed)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
