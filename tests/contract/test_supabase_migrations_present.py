"""Tripwire: every applied Supabase migration is IN GIT, verbatim.

On 2026-08-23 PR #43 was titled "Reconstruct the full applied Supabase migration
history" and merged with an EMPTY tree: the eleven .sql files had been written to
a worktree's disk but never `git add`ed, the branch carried unrelated commits, CI
was green (nothing to test), and the repository kept claiming reproducibility it
did not have until an external audit caught it two days later.

This test makes that failure impossible to repeat silently. It pins, offline:
  1. exactly the registered versioned files exist under supabase/migrations/;
  2. each file's body (after the header marker) hashes to the md5 Supabase itself
     reports for the applied SQL (md5(array_to_string(statements, E'\\n'))).
A future migration applied remotely must be added HERE with its remote md5 —
which is precisely the discipline the register exists to enforce.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "supabase" / "migrations"
MARKER = "-- ---- verbatim applied SQL follows ----\n"

#: version_name -> md5 reported by supabase_migrations.schema_migrations (2026-08-28).
APPLIED = {
    "20260818095451_research_catalog_v1": "0cbd13c385c331cebb9fa4b830ff69f2",
    "20260818100555_research_datasets_v1": "49dae2ea54d1163d93bd887781f4d348",
    "20260818182133_rp2_block14_evidence_hygiene": "bc31689dbc591531c1d22afdc5a00afb",
    "20260818205058_rp2_research_program_v2_catalog": "b3fd09e3a58f08c8d01dab7d685ed8ee",
    "20260818210128_rp2_extensions_catalog": "e66ce4326bf3d5d7dea8b77cc3392809",
    "20260818232434_rp2v2_ingestion_provenance_and_constraints": "cc074de11eaee27f50699aa1e92de368",
    "20260818232500_rp2v2_private_base_public_views_rls": "0257db586c6251e43b8c4f12eb157568",
    "20260821034446_rp2_v3_versioned_results": "df425bdbdaf99c26bd3f49b1e9375ffa",
    "20260821034552_rp2_v3_publication_functions": "a98c7a8aeb03f0de3a0e43d2758f475a",
    "20260823075803_expose_api_schema_for_public_aggregate_reads":
        "a8dfc1a5be41d5bbc677c9714c564398",
    "20260823080126_revert_ineffective_api_schema_exposure": "cc9aa3b50821432214fc80c6df278bf5",
    "20260825192000_fk_covering_indexes": "94814c3de32811418b5b1b15bdffda08",
    "20260826020000_least_privilege_and_invoker_views":
        "ba251c69f86d5bed254e26f2ad6eee0d",
    "20260826030000_loader_staging_and_atomic_promotion":
        "910b547d532b3308a0e45f5e089dbb17",
    "20260826180409_loader_run_scoped_staging":
        "066ad7db1e62b20cec39347e8ef24cbb",
    "20260826194803_safeupdate_compatible_reconciliation":
        "b4bd1196d32c1e5b0065f6d16d8421e4",
    "20260826210228_close_versioned_result_base_tables":
        "1e65e1e1eaf9f73624a3ae8afe6d7ad8",
    "20260827073145_retire_ineligible_current_rp2_results":
        "50620b2b0317b0de71e50ee2809c44ec",
    "20260828020327_close_service_role_sensitive_mutation_paths":
        "fb99bfba6d48f7e003483438e84e05f5",
}


def test_exactly_the_applied_migrations_are_versioned() -> None:
    on_disk = sorted(path.stem for path in MIGRATIONS.glob("*.sql"))
    assert on_disk == sorted(APPLIED), (
        "supabase/migrations/ must hold exactly the migrations Supabase records as "
        "applied — a missing file means the schema is not reproducible from Git "
        "(the PR #43 failure), an extra one means an unapplied file is posing as "
        "history. Register remote-applied migrations in APPLIED above."
    )


def test_every_migration_body_matches_the_remote_md5() -> None:
    mismatches = []
    for stem, expected in APPLIED.items():
        text = (MIGRATIONS / f"{stem}.sql").read_bytes().decode("utf-8")
        assert MARKER in text, f"{stem}.sql lost its header marker"
        # The remote md5 is over the submitted text. A Windows checkout may hand us
        # CRLF, and the MCP transport can append CRLF after the file's existing LF.
        body = text.split(MARKER, 1)[1].replace("\r\n", "\n")
        candidates = {
            body,
            body.rstrip("\n"),
            body.rstrip("\n") + "\n",
            body.rstrip("\n") + "\n\r\n",
        }
        digests = {hashlib.md5(c.encode("utf-8")).hexdigest() for c in candidates}
        if expected not in digests:
            mismatches.append(f"{stem}: {sorted(digests)} != {expected}")
    assert not mismatches, (
        "migration bodies no longer match what Supabase recorded as applied "
        "(edited in place? corrections must be NEW migrations):\n  "
        + "\n  ".join(mismatches)
    )


def test_the_never_applied_drafts_stay_out_of_the_migrations_directory() -> None:
    draft = REPO / "supabase" / "drafts" / "20260820170000_rp2_v3_versioned_results_DRAFT.sql"
    assert draft.is_file(), "the never-applied 36.9KB draft must stay preserved in drafts/"
    assert draft.read_text(encoding="utf-8").startswith("-- DRAFT - NEVER APPLIED AS WRITTEN")
    pending = REPO / "supabase" / "migrations_pending" / "rp2_block14_pending.sql"
    assert "DO NOT RUN AS WRITTEN" in pending.read_text(encoding="utf-8")
