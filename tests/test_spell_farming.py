import json
import sqlite3
from pathlib import Path

from build_blue_spell_farming import blue_magic_cap, build
from missions import create_app


def test_blue_magic_skill_threshold_uses_level_75_cap():
    assert blue_magic_cap(1) == 6
    assert blue_magic_cap(50) == 153
    assert blue_magic_cap(70) == 248
    assert blue_magic_cap(75) == 276


def test_catalog_excludes_post_toau_zones_and_derives_minimum_skill():
    payload = build([
        {"spell_level": 75, "name": "Vertical Cleave", "monster_name": "Euvhi",
         "zone": "Al'Taieu", "min_level": "74", "max_level": "76", "link": ""},
        {"spell_level": 61, "name": "Bad Breath", "monster_name": "Morbol",
         "zone": "Abyssea - La Theine", "min_level": "80", "max_level": "82", "link": ""},
    ])
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["minimum_skill"] == 247


def test_spell_farming_page_and_generated_catalog(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "spell.db"),
                      "SECRET_KEY": "test", "AUTH_DISABLED": True})
    client = app.test_client()
    with client.session_transaction() as session:
        session["member_id"] = 1
        session["is_editor"] = True
    page = client.get("/spell-farming")
    assert page.status_code == 200
    assert b"Spell Farming" in page.data
    assert b'id="spell-current-skill"' in page.data
    assert b"Spell Farming</a>" in page.data
    assert b"My Learned Spells" in page.data
    assert b"Changes automatically save to Imaven" in page.data

    payload = json.loads(Path("static/blue_spell_farming.json").read_text(encoding="utf-8"))
    assert len(payload["rows"]) > 500
    assert len({row["spell"] for row in payload["rows"]}) == 100
    assert all(row["spell_level"] <= 75 for row in payload["rows"])
    assert not any("Abyssea" in row["zone"] or " (S)" in row["zone"]
                   for row in payload["rows"])


def test_member_can_save_and_reopen_learned_spells(tmp_path):
    database_path = tmp_path / "learned.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path),
                      "SECRET_KEY": "test", "AUTH_DISABLED": True})
    client = app.test_client()
    with client.session_transaction() as session:
        session["member_id"] = 1
        session["is_editor"] = True
    response = client.post("/spell-farming/ownership", data={
        "spells": ["Pollen", "Head Butt"],
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Saved 2 learned Blue Magic spells" in response.data
    assert b'window.LEARNED_BLUE_SPELLS=["Head Butt", "Pollen"]' in response.data
    database = sqlite3.connect(database_path)
    assert database.execute(
        "SELECT spell FROM blue_spell_ownership ORDER BY spell"
    ).fetchall() == [("Head Butt",), ("Pollen",)]
    database.close()


def test_spell_ownership_rejects_unknown_spells(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "invalid.db"),
                      "SECRET_KEY": "test", "AUTH_DISABLED": True})
    client = app.test_client()
    with client.session_transaction() as session:
        session["member_id"] = 1
        session["is_editor"] = True
    assert client.post("/spell-farming/ownership", data={"spells": "Meteor II"}).status_code == 400


def test_learned_spells_are_isolated_to_signed_in_character(tmp_path):
    database_path = tmp_path / "per-member.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path),
                      "SECRET_KEY": "test", "AUTH_DISABLED": True})
    client = app.test_client()
    with client.session_transaction() as session:
        session["member_id"] = 1
        session["is_editor"] = True
    client.post("/spell-farming/ownership", data={"spells": ["Pollen", "Head Butt"]})

    with client.session_transaction() as session:
        session["member_id"] = 2
    second_member_page = client.get("/spell-farming")
    assert b"Changes automatically save to Sexualpotato" in second_member_page.data
    assert b"window.LEARNED_BLUE_SPELLS=[]" in second_member_page.data

    client.post("/spell-farming/ownership", data={"spells": "Cocoon"})
    database = sqlite3.connect(database_path)
    ownership = database.execute(
        "SELECT member_id,spell FROM blue_spell_ownership ORDER BY member_id,spell"
    ).fetchall()
    database.close()
    assert ownership == [(1, "Head Butt"), (1, "Pollen"), (2, "Cocoon")]
