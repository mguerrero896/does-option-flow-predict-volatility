"""Extend the public allowlist with closed descriptive aggregate tables only."""

from __future__ import annotations

import json

from artifacts.rp4_closeout_audit_code.audit_closed import OUTPUT, load, new_file, sha

ADDED_AGGREGATES = (
    "descriptive_profiles.csv",
    "ridge_lambda_counts.csv",
    "ridge_bounds_pruning_summary.csv",
    "forecast_equality_summary.csv",
    "loss_tails_and_rounds_summary.csv",
    "training_end_clock_census.csv",
    "selected_target_endpoint_clock_census.csv",
    "metadata_findings.json",
    "findings.json",
)


def run() -> dict[str, str | int]:
    old = OUTPUT / "public_manifest.json"
    expected = "a5e969d43b2944f96856b9fa05616607a0e7f31e1343da137a3ba7996eefb7a7"
    manifest = load(old, expected)
    manifest["supersedes_public_manifest_sha256"] = expected
    for name in ADDED_AGGREGATES:
        assert "origins" not in name and "by_session" not in name
        path = OUTPUT / name
        content = path.read_text(encoding="utf-8")
        for forbidden in [
            "mguer",
            "private-input/d0023e7cb6a981751ef5",
            "private-input/8d10eace3eede3521e71",
            "private-input/8545a81f99f36eda523c",
            "private-input/77a21ec4f7934cdbc426",
            "public_checkout",
        ]:
            assert forbidden not in content
        manifest["outputs_sha256"][name] = sha(path)
    for name, digest in manifest["outputs_sha256"].items():
        assert sha(OUTPUT / name) == digest
    new_file("public_manifest_v2.json", (json.dumps(manifest, indent=2) + "\n").encode())
    return {
        "status": "PASS_AGGREGATE_ONLY_PUBLIC_PROJECTION_V2",
        "public_outputs": len(manifest["outputs_sha256"]),
        "prior_manifest_unchanged_sha256": sha(old),
        "public_manifest_v2_sha256": sha(OUTPUT / "public_manifest_v2.json"),
        "model_fits": 0,
        "new_p_values": 0,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
