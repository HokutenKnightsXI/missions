import json
import re
from pathlib import Path

import pytest
import missions

from build_loot_tables import allowed_zone, parse_drops, parse_item_details, parse_spawns, th_rate
from missions import compact_market_snapshot, create_app, dynamis_catalog, market_snapshot


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


def test_shared_drop_block_is_applied_to_every_consecutive_mob_heading():
    sql = """-- ZoneID: 124 - Tonberry Jinxer
-- ZoneID: 160 - Tonberry Imprecator
INSERT INTO `mob_droplist` VALUES (2438,0,0,1000,1429,@UNCOMMON); -- Black Mages Testimony (Uncommon, 10%)
"""
    rows = parse_drops(sql, {124: "Yhoator_Jungle", 160: "Den_of_Rancor"})
    assert [row[:3] for row in rows] == [
        ["Den of Rancor", "Tonberry Imprecator", "Black Mages Testimony"],
        ["Yhoator Jungle", "Tonberry Jinxer", "Black Mages Testimony"],
    ]
    assert all(row[9] == 1429 for row in rows)


def test_general_loot_index_excludes_dynamis_currency():
    sql = """-- ZoneID: 134 - Vanguard Eye
INSERT INTO `mob_droplist` VALUES (1,0,0,1000,1452,@COMMON); -- One Byne Bill (Common, 15%)
INSERT INTO `mob_droplist` VALUES (2,0,0,1000,15102,@RARE); -- Warriors Mufflers (Rare, 5%)
"""
    rows = parse_drops(sql, {134: "Dynamis-Bastok"})
    assert [row[2] for row in rows] == ["Warriors Mufflers"]


def test_drop_item_details_include_icon_id_and_description():
    rows = [["Yhoator Jungle", "Tonberry Jinxer", "Black Mages Testimony",
             10, 12, 15, 16.5, 18, 1, 1429]]
    details = parse_item_details(
        '[1429] = {id=1429,en="A testimony from a black mage."},\n', rows
    )
    assert details["1429"]["name"] == "Black Mages Testimony"
    assert details["1429"]["description"] == "A testimony from a black mage."


def test_bhaflau_wivre_uses_renamed_locus_spawn_coordinates():
    sql = """-- Bhaflau Thickets (Zone 52)
INSERT INTO `mob_spawn_points` VALUES (17000001,1,'Locus_Wivre','Locus_Wivre',0,135,137,-560,-11,-66,0);
"""
    rows = [["Bhaflau Thickets", "Wivre", "Wivre Hide"]]
    spawns, _bounds = parse_spawns(sql, {52: "Bhaflau_Thickets"}, rows)
    assert spawns["Bhaflau Thickets\twivre"] == {
        "p": [[-560.0, -66.0, -11.0]],
        "l": [78, 83],
    }


def test_loot_table_page_and_generated_index(client):
    response = client.get("/loot-tables")
    assert response.status_code == 200
    assert b"HorizonXI Loot Tables" in response.data
    assert b"TH4" in response.data and b"Search monsters" in response.data
    payload = json.loads(Path("static/loot_tables.json").read_text(encoding="utf-8"))
    assert payload["th_max"] == 4 and len(payload["rows"]) > 10_000
    assert payload["items"] and all(len(row) == 10 for row in payload["rows"])
    zones = {row[0] for row in payload["rows"]}
    assert not any("Abyssea" in zone or "[S]" in zone for zone in zones)
    dark_stalker = payload["spawns"]["The Eldieme Necropolis\tdarkstalker"]
    assert len(dark_stalker["p"]) == 16
    assert dark_stalker["l"] == [57, 59]


def test_market_snapshot_is_compacted_for_price_cells():
    snapshot = compact_market_snapshot({
        "meta": {"generatedAt": "2026-08-11T18:00:00Z"},
        "data": [{
            "itemId": 15515, "itemName": "Peacock Amulet", "asOf": "2026-08-11T17:55:00Z",
            "ah": {"currentStock": 2, "currentStackStock": 0,
                   "single": {"lastSale": 900000, "median": 875000, "volume": 4},
                   "stack": {"lastSale": None, "median": None, "volume": 0}},
        }],
    })
    assert snapshot["generated_at"] == "2026-08-11T18:00:00Z"
    assert snapshot["prices"]["15515"]["single_last"] == 900000
    assert snapshot["prices"]["15515"]["stock"] == 2


def test_market_price_endpoint_returns_server_cached_values(client, monkeypatch):
    monkeypatch.setattr(missions, "market_snapshot", lambda _path, _token: {
        "generated_at": "2026-08-11T18:00:00Z",
        "prices": {"15515": {"single_last": 900000}},
    })
    response = client.get("/api/market-prices")
    assert response.status_code == 200
    assert response.get_json()["prices"]["15515"]["single_last"] == 900000
    assert response.headers["Cache-Control"] == "public, max-age=300"


def test_market_snapshot_fetches_only_once_inside_hour(tmp_path, monkeypatch):
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"meta": {"generatedAt": "now"}, "data": []}).encode()

    monkeypatch.setattr(missions, "urlopen", lambda *_args, **_kwargs: calls.append(1) or Response())
    cache = tmp_path / "market.json"
    assert market_snapshot(cache, now=1000)["generated_at"] == "now"
    assert market_snapshot(cache, now=1001)["generated_at"] == "now"
    assert len(calls) == 1


def test_loot_hub_offers_general_dynamis_and_limbus_modes(client):
    general = client.get("/loot-tables")
    assert b"General Loot Tables" in general.data
    assert b"AH Value" in general.data and b"MARKET_DATA_URL" in general.data
    assert b'id="market-value-header"' in general.data
    market_script = client.get("/static/loot_tables.js").data
    assert b"MARKET_NAME_ALIASES={peacockamulet:'peacockcharm'}" in market_script
    assert b"marketByName" in market_script
    assert b"marketSortDirection" in market_script
    assert b"aria-sort" in market_script
    assert b"zone-map-trigger" in market_script
    assert b"trigger.dataset.mob" in market_script
    assert b"Dynamis Loot" in general.data and b"Limbus Loot" in general.data
    dynamis = client.get("/loot-tables?mode=dynamis&member_id=1")
    assert b"By Dynamis Area" in dynamis.data
    assert b"Warrior&#39;s Calligae" in dynamis.data
    limbus = client.get("/loot-tables?mode=limbus&member_id=1")
    assert b"Proto-Omega" in limbus.data and b"Homam Corazza" in limbus.data
    assert b"Proto-Ultima" in limbus.data and b"Nashira Manteel" in limbus.data
    styling = client.get("/static/loot_tracker_layout.css")
    assert b"#ff9f1c" in styling.data


def test_dynamis_ownership_is_shared_between_area_and_job_views(client):
    response = client.post("/loot-tables/ownership", data={
        "catalog": "dynamis", "view": "job", "member_id": "1",
        "owned": ["dynamis:WAR:feet", "dynamis:RDM:head"],
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated Imaven&#39;s Dynamis loot tracker" in response.data
    area = client.get("/loot-tables?mode=dynamis&view=area&member_id=1")
    job = client.get("/loot-tables?mode=dynamis&view=job&member_id=1")
    for page in (area, job):
        assert b'value="dynamis:WAR:feet" checked' in page.data
        assert b'value="dynamis:RDM:head" checked' in page.data


def test_limbus_ownership_saves_separately_from_dynamis(client):
    client.post("/loot-tables/ownership", data={
        "catalog": "limbus", "member_id": "1",
        "owned": ["limbus:proto-omega:body", "limbus:proto-ultima:head"],
    })
    page = client.get("/loot-tables?mode=limbus&member_id=1")
    assert b'value="limbus:proto-omega:body" checked' in page.data
    assert b'value="limbus:proto-ultima:head" checked' in page.data
    assert b'value="limbus:proto-omega:feet" checked' not in page.data


def test_limbus_tracks_af1_materials_and_finished_pieces(client):
    page = client.get("/loot-tables?mode=limbus&member_id=1")
    assert b"AF+1 Materials &amp; Finished Pieces" in page.data
    assert b"Argyro Rivet" in page.data and b"NE F3" in page.data
    assert b"Ecarlate Cloth" in page.data and b"North F2/F4" in page.data
    assert b"Fighter&#39;s Mask +1" in page.data
    assert b"job-icons.svg#war" in page.data

    saved = client.post("/loot-tables/ownership", data={
        "catalog": "limbus", "member_id": "1",
        "owned": ["limbus:af1:WAR:apollyon", "limbus:af1:WAR:head"],
    }, follow_redirects=True)
    assert saved.status_code == 200
    assert b'value="limbus:af1:WAR:apollyon" checked' in saved.data
    assert b'value="limbus:af1:WAR:head" checked' in saved.data


def test_limbus_tooltips_include_jobs_and_af1_stats():
    tooltips = json.loads(Path("static/item_tooltips.json").read_text(encoding="utf-8"))
    assert tooltips["limbus:proto-omega:body"]["job"] == "BLU · DRG · DRK · PLD · THF"
    assert tooltips["limbus:proto-ultima:head"]["job"] == "BLU · BLM · BRD · RDM · SMN · WHM"
    assert tooltips["limbus:af1:WAR:apollyon"]["job"] == "WAR"
    assert "NE F3" in tooltips["limbus:af1:WAR:apollyon"]["stats"]
    finished = tooltips["limbus:af1:WAR:head"]
    assert finished["name"] == "Fighter's Mask +1"
    assert finished["level"] == 74
    assert finished["stats"] != "Equipment description unavailable."


def test_member_submitted_target_is_forced_to_signed_in_character(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "secured-loot.db"),
                      "SECRET_KEY": "test", "AUTH_DISABLED": False})
    secured = app.test_client()
    with secured.session_transaction() as session:
        session["is_editor"] = True
        session["member_id"] = 1
        session["csrf_token"] = "valid-token"
    response = secured.post("/loot-tables/ownership", data={
        "csrf_token": "valid-token", "catalog": "dynamis", "member_id": "2",
        "owned": ["dynamis:WAR:feet"],
    })
    assert response.status_code == 302
    import sqlite3
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute(
        "SELECT member_id,item_key FROM loot_ownership"
    ).fetchall() == [(1, "dynamis:WAR:feet")]
    database.close()


def test_dynamis_catalog_includes_sorted_dreamland_minus_ones_and_accessories(client):
    pieces = dynamis_catalog()
    by_area = {}
    for piece in pieces:
        by_area.setdefault(piece["area"], []).append(piece)
    assert {"Dynamis - Valkurm", "Dynamis - Buburimu", "Dynamis - Qufim",
            "Dynamis - Tavnazia"} <= set(by_area)
    assert any(piece["item"] == "Warrior's Mask -1" for piece in by_area["Dynamis - Valkurm"])
    assert any(piece["item"] == "Warrior's Mufflers -1" for piece in by_area["Dynamis - Buburimu"])
    assert any(piece["item"] == "Warrior's Calligae -1" for piece in by_area["Dynamis - Qufim"])
    assert any(piece["item"] == "Warrior's Lorica -1" for piece in by_area["Dynamis - Tavnazia"])
    page = client.get("/loot-tables?mode=dynamis&member_id=1")
    assert b"Dreamland Dynamis" in page.data
    assert b"Warrior&#39;s Stone" in page.data
    cards = re.findall(rb'<section class="loot-track-card"[^>]*>(.*?)</section>', page.data, re.S)
    assert cards
    for card in cards:
        jobs = re.findall(rb'<span class="job-token">([^<]+)', card)
        assert jobs == sorted(jobs)
    layout = client.get("/static/loot_tracker_layout.css")
    assert b"repeat(3" in layout.data


def test_job_view_pairs_main_and_minus_one_with_icons_and_cross_links(client):
    page = client.get("/loot-tables?mode=dynamis&view=job&member_id=1")
    assert b'id="job-WAR"' in page.data
    assert b'job-icons.svg#war' in page.data
    warrior_row = re.search(
        rb'<div class="paired-relic-row">.*?Warrior&#39;s Mask.*?Warrior&#39;s Mask -1.*?</div>',
        page.data, re.S,
    )
    assert warrior_row
    assert b'#area-windurst' in warrior_row.group(0)
    assert b'#area-valkurm' in warrior_row.group(0)
    area = client.get("/loot-tables?mode=dynamis&view=area&member_id=1")
    assert b'#job-WAR' in area.data
    layout = client.get("/static/loot_tracker_layout.css")
    assert b'grayscale(.8)' in layout.data
    assert b':has(input:checked)' in layout.data


def test_tracked_items_have_static_hover_stats_and_wider_layout(client):
    page = client.get("/loot-tables?mode=dynamis&view=job&member_id=1")
    assert b"item-stat-tooltip" in page.data
    assert b"item_tooltips.js" in page.data
    tooltips = json.loads(Path("static/item_tooltips.json").read_text(encoding="utf-8"))
    petasos = tooltips["dynamis:BLM:head"]
    assert petasos["item_id"] == 15075
    assert petasos["name"] == "Sorcerer's Petasos"
    assert petasos["level"] == 75
    assert "Elemental magic skill +10" in petasos["stats"]
    layout = Path("static/loot_tracker_layout.css").read_text(encoding="utf-8")
    assert "max-width:1580px" in layout
    assert ".paired-piece span>b{white-space:normal" in layout
    damaged = tooltips["dynamis:dream:BLM:head"]
    assert damaged["name"] == "Sorcerer's Petasos -1"
    assert damaged["level"] == 75
    assert "UPGRADE PREVIEW" in damaged["stats"]
    assert "Elemental magic skill" in damaged["stats"]
    assert "upgrade material" in damaged["note"]
    assert ".loot-table{font-size:14px}" in layout
