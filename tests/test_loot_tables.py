import json
from pathlib import Path

import pytest

from build_loot_tables import allowed_zone, th_rate
from missions import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "loot.db"),
                      "SECRET_KEY": "test", "AUTH_DISABLED": True})
    return app.test_client()


def test_th_rates_are_capped_at_th4_and_follow_supplied_brackets():
    assert [th_rate(240, th) for th in range(5)] == [24, 48, 56, 60, 64]
    assert [th_rate(50, th) for th in range(5)] == [5, 6, 7, 7.5, 8]
    assert th_rate(1000, 4) == 100


def test_zone_filter_excludes_later_expansions():
    assert allowed_zone(100, "West_Ronfaure")
    assert allowed_zone(79, "Caedarva_Mire")
    assert not allowed_zone(81, "East_Ronfaure_[S]")
    assert not allowed_zone(15, "Abyssea-Konschtat")
    assert not allowed_zone(256, "Western_Adoulin")


def test_loot_table_page_and_generated_index(client):
    response = client.get("/loot-tables")
    assert response.status_code == 200
    assert b"HorizonXI Loot Tables" in response.data
    assert b"TH4" in response.data and b"Search monsters" in response.data
    payload = json.loads(Path("static/loot_tables.json").read_text(encoding="utf-8"))
    assert payload["th_max"] == 4 and len(payload["rows"]) > 10_000
    zones = {row[0] for row in payload["rows"]}
    assert not any("Abyssea" in zone or "[S]" in zone for zone in zones)
    dark_stalker = payload["spawns"]["The Eldieme Necropolis\tdarkstalker"]
    assert len(dark_stalker["p"]) == 16
    assert dark_stalker["l"] == [57, 59]
