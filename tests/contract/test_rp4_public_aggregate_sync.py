"""A public sync preserves cells, detects drift and touches only its three tables."""

import json
import shutil

import httpx
import pytest
from scripts import sync_supabase_catalog as sync


def test_public_v4_sync_round_trip_and_source_guards(tmp_path):
    payload = sync.rp4_rows()
    stored = {}

    def endpoint(request):
        table = request.url.path.rsplit("/", 1)[-1]
        assert table in sync.RP4_SOURCES
        if request.method == "POST":
            assert request.url.params["on_conflict"] == "source_sha256,row_number"
            stored[table] = json.loads(request.content)
            return httpx.Response(201)
        assert request.method == "GET"
        return httpx.Response(200, json=stored[table])

    with httpx.Client(transport=httpx.MockTransport(endpoint)) as client:
        receipt = sync.sync_rp4(client, payload)
        assert sync.sync_rp4(client, payload) == receipt
        assert stored == payload
        with pytest.raises(ValueError, match="TABLE_SCOPE"):
            sync.sync_rp4(client, {"other": []})
    first = next(iter(sync.RP4_SOURCES.values()))[0]
    target = tmp_path / first
    target.parent.mkdir(parents=True)
    shutil.copyfile(sync.REPO / first, target)
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SOURCE_HASH_MISMATCH"):
        sync.rp4_rows(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(201) if request.method == "POST"
        else httpx.Response(200, json=[])
    )) as client, pytest.raises(RuntimeError, match="CONTENT_MISMATCH"):
        sync.sync_rp4(client, payload)
