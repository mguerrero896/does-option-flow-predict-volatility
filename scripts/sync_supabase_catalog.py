"""Sync the research catalog tables in Supabase from the repo's frozen artifacts.

Idempotent upserts (PostgREST, service-role key) of aggregates only — no licensed
provider values ever leave the repo through this script:

    campaigns          <- artifacts/gate1_inference/results.json
    contrast_results   <- artifacts/gate1_inference/results.json
    mcs_cells          <- artifacts/mcs_block_sensitivity/results.json
    gated_files        <- data/GATED_DATA_POINTERS.json

Run:  $env:SUPABASE_SERVICE_KEY set, then  uv run python scripts/sync_supabase_catalog.py
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import httpx

from mds650.sealed import guard_sealed_access

REPO = Path(__file__).resolve().parents[1]
PROJECT_REF = "eqpyjikcewqaegnbaemf"
REST = f"https://{PROJECT_REF}.supabase.co/rest/v1"


def _upsert(client: httpx.Client, table: str, rows: list[dict[str, Any]], conflict: str) -> None:
    if not rows:
        return
    response = client.post(
        f"{REST}/{table}",
        params={"on_conflict": conflict},
        json=rows,
        headers={"Prefer": "resolution=merge-duplicates"},
    )
    if response.status_code not in (200, 201):
        raise SystemExit(f"UPSERT_FAILED {table}: {response.status_code} {response.text[:300]}")
    print(f"[sync] {table}: {len(rows)} rows upserted")


def _verify(client: httpx.Client, table: str, rows: list[dict[str, Any]], conflict: str) -> None:
    """Read back every upserted row and require field-for-field agreement.

    An upsert that returns 201 can still have written something other than what was
    intended (a column silently dropped by PostgREST, a coercion). Fetching a sample
    row by its conflict keys and comparing every sent field closes that gap; a
    mismatch is a hard failure, not a warning.
    """
    if not rows:
        return
    for sent in rows:
        params = {key: f"eq.{sent[key]}" for key in conflict.split(",")}
        response = client.get(f"{REST}/{table}", params=params)
        if response.status_code != 200 or len(response.json()) != 1:
            raise SystemExit(f"VERIFY_FAILED {table}: row unreadable after upsert")
        remote = response.json()[0]
        missing = sorted(set(sent) - set(remote))
        if missing:
            raise SystemExit(f"VERIFY_FAILED {table}: missing fields: {missing}")
        mismatched = [field for field, value in sent.items() if remote[field] != value]
        if mismatched:
            raise SystemExit(f"VERIFY_FAILED {table}: fields differ after upsert: {mismatched}")
    print(f"[sync] {table}: {len(rows)} rows verified")


def _sync(client: httpx.Client, rows: dict[str, list[dict[str, Any]]]) -> None:
    """Atomically replace the catalog with the repository's complete aggregate payload."""
    response = client.post(f"{REST}/rpc/reconcile_research_catalog", json={"p_payload": rows})
    if response.status_code not in (200, 201):
        raise SystemExit(f"CATALOG_SYNC_FAILED: {response.status_code} {response.text[:300]}")
    expected = {name: len(payload) for name, payload in rows.items()}
    if response.json() != expected:
        raise SystemExit(f"CATALOG_SYNC_COUNT_MISMATCH: expected {expected}, got {response.json()}")
    print(f"[sync] atomic catalog reconciliation verified: {expected}")


def build_rows(
    gate1: dict[str, Any], mcs: dict[str, Any], pointers: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Pure artifact-to-rows mapping, split out so the note and p_wild_status
    derivations are unit-testable without a network."""

    campaigns: list[dict[str, Any]] = []
    contrasts: list[dict[str, Any]] = []
    for campaign_id, campaign in gate1["campaigns"].items():
        campaigns.append(
            {
                "campaign_id": campaign_id,
                "sessions": campaign.get("sessions"),
                "row_count": campaign.get("rows"),
                "input_sha256": campaign["input_sha256"],
                # Root cause of the repeated-note defect migration block14 had to
                # clean: the artifact's GLOBAL note was copied onto every campaign.
                # A note is published only if the campaign itself carries one.
                "note": campaign.get("note"),
            }
        )
        for block_id, block in campaign["blocks"].items():
            for contrast_key, entry in block["contrasts"].items():
                model_role, _, contrast = contrast_key.partition(":")
                contrasts.append(
                    {
                        "campaign_id": campaign_id,
                        "block_id": block_id,
                        "model_role": model_role,
                        # Derived from the SAME field published as p_wild below, so the
                        # status can never disagree with the value it describes.
                        "p_wild_status": (
                            "SYNCED"
                            if entry.get("wild_bootstrap", {}).get("p_value") is not None
                            else "AVAILABLE_IN_ARTIFACT_ONLY"
                        ),
                        "contrast": contrast,
                        "estimate": entry["cluster_t"]["estimate"],
                        "cluster_t": entry["cluster_t"]["statistic"],
                        "p_cluster": entry["cluster_t"]["p_value"],
                        "p_newey_west": entry.get("newey_west", {}).get("p_value"),
                        "p_wild": entry.get("wild_bootstrap", {}).get("p_value"),
                        "rho1": (entry.get("acf") or [None])[0],
                        "ljung_box_p": entry.get("ljung_box", {}).get("p_value"),
                    }
                )

    cells: list[dict[str, Any]] = []
    for campaign_id, campaign in mcs["campaigns"].items():
        for block_id, block in campaign["blocks"].items():
            for length_key, result in block["by_block_length"].items():
                length = int(length_key.removeprefix("L="))
                survivors = set(result["survivors"])
                for cell, p_value in result["mcs_p_values"].items():
                    cells.append(
                        {
                            "campaign_id": campaign_id,
                            "block_id": block_id,
                            "block_length": length,
                            "cell": cell,
                            "mcs_p": p_value,
                            "survivor": cell in survivors,
                        }
                    )

    gated = [
        {
            "path": entry["path"],
            "sha256": entry["sha256"],
            "bytes": entry["bytes"],
            "bucket_object": entry["bucket_object"],
        }
        for entry in pointers["files"]
    ]

    return {"campaigns": campaigns, "contrasts": contrasts, "cells": cells, "gated": gated}


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        raise SystemExit("SUPABASE_SERVICE_KEY missing (User env var; see DATA_ACCESS.md).")

    gate1 = json.loads((REPO / "artifacts" / "gate1_inference" / "results.json").read_text())
    mcs = json.loads((REPO / "artifacts" / "mcs_block_sensitivity" / "results.json").read_text())
    pointers = json.loads((REPO / "data" / "GATED_DATA_POINTERS.json").read_text())
    guard_sealed_access(
        ["campaigns", "contrast_results", "mcs_cells", "gated_files",
         *[entry["path"] for entry in pointers["files"]]],
        operation="catalog sync",
    )
    rows = build_rows(gate1, mcs, pointers)
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    with httpx.Client(timeout=120, headers=headers) as client:
        _sync(client, rows)
    print("[sync] done")


if __name__ == "__main__":
    main()
