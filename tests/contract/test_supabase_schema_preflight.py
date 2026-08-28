"""The loader migrations must agree with the measured and observed live states."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = ROOT / "artifacts" / "supabase_schema_preflight_20260826.json"
APPLIED = ROOT / "supabase" / "migrations" / (
    "20260826180409_loader_run_scoped_staging.sql"
)
CORRECTION = ROOT / "supabase" / "migrations" / (
    "20260826194803_safeupdate_compatible_reconciliation.sql"
)
MUTATION_BOUNDARY = ROOT / "supabase" / "migrations" / (
    "20260828020327_close_service_role_sensitive_mutation_paths.sql"
)


def test_applied_migration_matches_its_live_schema_preflight() -> None:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    migration = APPLIED.read_text(encoding="utf-8")

    assert preflight["mode"] == "READ_ONLY_POSTGREST_OPENAPI"
    assert preflight["sealed_cohorts_read"] == 0
    assert preflight["writes"] == 0
    assert preflight["verdict"] == "PENDING_MIGRATION_NOT_APPLIED"
    assert preflight["rpc"] == {
        "promote_dataset": True,
        "promote_dataset_v2": False,
        "reconcile_research_catalog": False,
    }
    assert all(not table["load_id"] for table in preflight["staging_tables"].values())
    for table in preflight["staging_tables"]:
        assert f"alter table public.{table} add column if not exists load_id uuid" in migration
    assert "create or replace function public.promote_dataset_v2(" in migration
    assert "create or replace function public.reconcile_research_catalog(" in migration


def test_applied_correction_is_safeupdate_compatible() -> None:
    migration = CORRECTION.read_text(encoding="utf-8")

    assert "delete from public.contrast_results where true" in migration
    assert "delete from public.mcs_cells where true" in migration
    assert "execute format('delete from %I where true', p_table)" in migration
    assert "delete from public.contrast_results;" not in migration
    assert "delete from public.mcs_cells;" not in migration
    assert "revoke execute on function public.promote_dataset(text, text, text)" in migration


def test_applied_default_privilege_hardening_is_owner_scoped() -> None:
    migration = MUTATION_BOUNDARY.read_text(encoding="utf-8")

    for kind in ("tables", "sequences", "functions"):
        assert (
            "alter default privileges for role postgres in schema public "
            f"revoke all on {kind} from public, anon, authenticated, service_role;"
        ) in migration
    assert "for role supabase_admin" not in migration
    assert "revoke insert, update, delete, truncate, references, trigger" in migration
    for table in (
        "rp2_block_results",
        "rp2_contrast_results",
        "rp2_extension_results",
        "rp2_power_results",
    ):
        assert f"public.{table}" in migration
    assert "public.dataset_loads" not in migration
    assert "public.dev_training_all_origins" not in migration
