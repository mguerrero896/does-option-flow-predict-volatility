"""Pins for the three Supabase producer defects the 2026-08-25 audit named.

1. sync_supabase_catalog copied the artifact's GLOBAL note onto every campaign —
   the defect migration block14 had to clean server-side. The note must now come
   from the campaign itself, and p_wild_status must derive from the same field
   published as p_wild.
2. upload_gated_data sent x-upsert:true, able to silently replace a frozen object.
3. load_supabase_datasets wipes-then-reloads with row-count identity and no
   staging; until reworked it must refuse to run without an explicit override.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load(name: str):  # type: ignore[no-untyped-def]  # a script module has no stub
    path = REPO / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestSyncCatalogRows:
    def test_global_note_is_not_copied_onto_campaigns(self) -> None:
        sync = _load("sync_supabase_catalog")
        gate1 = {
            "note": "a GLOBAL caveat that belongs to the artifact, not to campaigns",
            "campaigns": {
                "C1": {"sessions": 3, "rows": 9, "input_sha256": "a" * 64, "blocks": {}},
                "C6": {
                    "sessions": 2,
                    "rows": 4,
                    "input_sha256": "b" * 64,
                    "note": "C6-specific caveat",
                    "blocks": {},
                },
            },
        }
        rows = sync.build_rows(gate1, {"campaigns": {}}, {"files": []})
        notes = {row["campaign_id"]: row["note"] for row in rows["campaigns"]}
        assert notes == {"C1": None, "C6": "C6-specific caveat"}

    def test_p_wild_status_matches_the_published_p_wild(self) -> None:
        sync = _load("sync_supabase_catalog")
        entry_with = {"cluster_t": {"estimate": 0.1, "statistic": 2.0, "p_value": 0.04},
                      "wild_bootstrap": {"p_value": 0.03}}
        entry_without = {"cluster_t": {"estimate": 0.2, "statistic": 1.0, "p_value": 0.30}}
        gate1 = {
            "campaigns": {
                "C1": {
                    "input_sha256": "a" * 64,
                    "blocks": {
                        "B": {"contrasts": {"b1:var": entry_with, "b2:var": entry_without}}
                    },
                }
            }
        }
        rows = sync.build_rows(gate1, {"campaigns": {}}, {"files": []})
        by_role = {row["model_role"]: row for row in rows["contrasts"]}
        assert by_role["b1"]["p_wild_status"] == "SYNCED"
        assert by_role["b1"]["p_wild"] == 0.03
        assert by_role["b2"]["p_wild_status"] == "AVAILABLE_IN_ARTIFACT_ONLY"
        assert by_role["b2"]["p_wild"] is None

    def test_verify_rejects_a_remote_row_that_dropped_a_sent_field(self) -> None:
        sync = _load("sync_supabase_catalog")

        class Response:
            status_code = 200

            @staticmethod
            def json():  # type: ignore[no-untyped-def]
                return [{"campaign_id": "C1"}]

        class Client:
            @staticmethod
            def get(*_args: object, **_kwargs: object) -> Response:
                return Response()

        with pytest.raises(SystemExit, match="VERIFY_FAILED campaigns: missing fields"):
            sync._verify(  # type: ignore[attr-defined]
                Client(),
                "campaigns",
                [{"campaign_id": "C1", "input_sha256": "a" * 64}],
                "campaign_id",
            )

    def test_catalog_sync_is_one_rpc_and_checks_every_returned_count(self) -> None:
        sync = _load("sync_supabase_catalog")

        class Response:
            status_code = 200

            @staticmethod
            def json():  # type: ignore[no-untyped-def]
                return {"campaigns": 1, "contrasts": 1, "cells": 1, "gated": 1}

        class Client:
            calls: list[tuple[str, dict]] = []

            def post(self, url: str, **kwargs: object) -> Response:
                self.calls.append((url, kwargs))
                return Response()

        client = Client()
        rows = {
            "campaigns": [{"campaign_id": "C1"}],
            "contrasts": [{"campaign_id": "C1"}],
            "cells": [{"campaign_id": "C1"}],
            "gated": [{"path": "a"}],
        }
        sync._sync(client, rows)  # type: ignore[attr-defined]
        assert len(client.calls) == 1
        assert client.calls[0][0].endswith("/rpc/reconcile_research_catalog")


class TestUploaderImmutability:
    def test_upsert_header_is_gone_from_the_uploader(self) -> None:
        # ponytail: the upload path needs a live bucket to run, so the pin is on the
        # request it would send — x-upsert must be false, or absent entirely.
        source = (REPO / "scripts" / "upload_gated_data.py").read_text(encoding="utf-8")
        assert '"x-upsert": "true"' not in source
        assert '"x-upsert": "false"' in source

    def test_bucket_privacy_is_checked_before_any_upload(self) -> None:
        source = (REPO / "scripts" / "upload_gated_data.py").read_text(encoding="utf-8")
        assert "BUCKET_PRIVACY_UNVERIFIED" in source
        assert source.index("BUCKET_PRIVACY_UNVERIFIED") < source.index("for entry in entries")


class TestLoaderSafety:
    """The loader was on an audit hold until 2026-08-26. The hold is gone because
    the five defects behind it are fixed, so these pin the fixes, not the gate."""

    def test_identity_is_the_source_digest_not_a_row_count(self) -> None:
        loader = _load("load_supabase_datasets")
        assert hasattr(loader, "file_digest"), "identity must come from the file's bytes"
        source = (REPO / "scripts" / "load_supabase_datasets.py").read_text(encoding="utf-8")
        assert "_recorded_load" in source, "the loader must compare against recorded provenance"
        assert '"source_sha256,row_count"' in source
        assert "_row_count(client, table)" in source, (
            "a matching registry digest must not hide live-table row drift"
        )
        assert "if existing == frame.height" not in source, (
            "the row-count identity check must be gone"
        )

    def test_it_loads_into_staging_and_never_deletes_the_live_table(self) -> None:
        source = (REPO / "scripts" / "load_supabase_datasets.py").read_text(encoding="utf-8")
        assert "__staging" in source, "rows must land in staging first"
        # The only DELETE may target staging; the live table is emptied server-side,
        # inside the promotion transaction.
        for line in source.splitlines():
            if "client.delete(" in line:
                assert "staging" in line, f"a delete targets a live table: {line.strip()}"

    def test_promotion_is_one_server_side_transaction(self) -> None:
        source = (REPO / "scripts" / "load_supabase_datasets.py").read_text(encoding="utf-8")
        assert "rpc/promote_dataset" in source, "promotion must be the transactional RPC"

    def test_a_staging_count_mismatch_stops_before_touching_the_live_table(self) -> None:
        source = (REPO / "scripts" / "load_supabase_datasets.py").read_text(encoding="utf-8")
        assert "STAGING_COUNT_MISMATCH" in source
        assert source.index("STAGING_COUNT_MISMATCH") < source.index("_promote(client, table")

    def test_the_audit_hold_is_gone(self) -> None:
        """A gate kept past its cause teaches people to route around gates."""
        source = (REPO / "scripts" / "load_supabase_datasets.py").read_text(encoding="utf-8")
        assert "SUPABASE_LOADER_ON_AUDIT_HOLD" not in source
        assert "MDS650_LOADER_ACK" not in source

    def test_missing_any_required_source_is_a_hard_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        loader = _load("load_supabase_datasets")
        monkeypatch.setattr(loader, "REPO", tmp_path)
        monkeypatch.setattr(loader, "DATASETS", {"only": "missing.parquet"})
        with pytest.raises(SystemExit, match="DATASET_SOURCES_MISSING: only"):
            loader.required_sources()  # type: ignore[attr-defined]

    def test_source_root_cannot_escape(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        loader = _load("load_supabase_datasets")
        monkeypatch.setattr(loader, "DATASETS", {"only": "../outside.parquet"})
        with pytest.raises(SystemExit, match="DATASET_PATH_ESCAPES_SOURCE_ROOT: only"):
            loader.required_sources(tmp_path)  # type: ignore[attr-defined]

    def test_explicit_source_root_finds_licensed_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        loader = _load("load_supabase_datasets")
        source = tmp_path / "artifacts" / "licensed.parquet"
        source.parent.mkdir()
        source.touch()
        monkeypatch.setattr(loader, "DATASETS", {"only": "artifacts/licensed.parquet"})
        assert loader.required_sources(tmp_path) == {"only": source.resolve()}  # type: ignore[attr-defined]

    def test_applied_loader_migration_is_run_scoped_and_explicitly_privileged(self) -> None:
        migration = (
            REPO
            / "supabase"
            / "migrations"
            / "20260826180409_loader_run_scoped_staging.sql"
        ).read_text(encoding="utf-8")
        assert "load_id uuid" in migration
        assert "where load_id = $1" in migration
        assert "enable row level security" in migration
        assert "grant execute on function public.promote_dataset_v2" in migration


class TestFetcherSafety:
    def test_download_lands_atomically_and_inside_the_repo(self) -> None:
        source = (REPO / "scripts" / "fetch_gated_data.py").read_text(encoding="utf-8")
        assert "PATH_ESCAPES_REPO" in source
        assert ".partial" in source and "partial.replace(destination)" in source
        assert "destination.write_bytes" not in source
