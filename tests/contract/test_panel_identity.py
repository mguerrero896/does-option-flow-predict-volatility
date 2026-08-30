"""Every declared RP2 panel must be the exact file recorded by its pointer."""

from __future__ import annotations

from tests.panel_guard import REPO, declared_panels, verified_panel_path


def test_all_declared_panel_identities() -> None:
    for relative in declared_panels():
        verified_panel_path(relative, REPO / relative)
