import sqlite3

import pytest

from missions import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "alliances.db"),
                       "SECRET_KEY": "test", "AUTH_DISABLED": True})


def add_roster(app):
    with app.app_context():
        database = sqlite3.connect(app.config["DATABASE"])
        maven = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
        lion = database.execute("SELECT id FROM members WHERE name='Shiru'").fetchone()[0]
        database.executemany(
            "INSERT INTO member_jobs(member_id,job,level) VALUES(?,?,?)",
            [(maven, "PLD", 75), (maven, "WAR", 60), (lion, "WHM", 75)],
        )
        database.commit()
        database.close()
    return maven, lion


def test_alliance_builder_uses_job_roster_and_three_parties(app):
    add_roster(app)
    page = app.test_client().get("/alliance-builder")
    assert page.status_code == 200
    assert b"Alliance Party Maker" in page.data
    assert page.data.count(b'class="alliance-party"') == 3
    assert page.data.count(b'class="party-slot"') == 18
    assert b'"PLD": 75' in page.data and b'"WHM": 75' in page.data
    assert b"Alliance Builder" in page.data
    assert b"+ Load Saved Alliance" in page.data
    assert b'class="available-roster-table"' in page.data
    assert b'name="name" maxlength="80" required' in page.data
    assert b"Find Characters" not in page.data
    assert b"Character search" not in page.data
    assert b'class="roster-inline-filters"' in page.data
    assert b"Alliance name <i>Required</i>" in page.data
    assert b'id="pick-event-date"' in page.data
    assert b'class="native-date-input"' in page.data
    assert b"Minimum level" not in page.data
    assert b"Level 75 Jobs" in page.data
    script = app.test_client().get("/static/alliance_builder.js")
    assert b"dragstart" in script.data and b"drag-over" in script.data


def test_admin_can_save_and_reopen_alliance_layout(app):
    maven, lion = add_roster(app)
    client = app.test_client()
    response = client.post("/alliance-builder/save", data={
        "name": "Dynamis - Xarcabard", "event_at": "2026-08-08T20:00",
        "notes": "Gather in Ru'Lude Gardens",
        "member_1_1": str(maven), "job_1_1": "PLD",
        "member_2_1": str(lion), "job_2_1": "WHM",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Saved alliance layout for Dynamis - Xarcabard" in response.data
    assert f'data-member="{maven}" data-job="PLD"'.encode() in response.data
    assert f'data-member="{lion}" data-job="WHM"'.encode() in response.data
    with app.app_context():
        database = sqlite3.connect(app.config["DATABASE"])
        assert database.execute("SELECT COUNT(*) FROM alliance_events").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM alliance_slots").fetchone()[0] == 2
        database.close()


def test_alliance_save_rejects_duplicate_members_and_unrostered_jobs(app):
    maven, _lion = add_roster(app)
    client = app.test_client()
    duplicate = client.post("/alliance-builder/save", data={
        "name": "Duplicate Test",
        "member_1_1": str(maven), "job_1_1": "PLD",
        "member_2_1": str(maven), "job_2_1": "WAR",
    })
    assert duplicate.status_code == 400
    forged = client.post("/alliance-builder/save", data={
        "name": "Forged Job", "member_1_1": str(maven), "job_1_1": "WHM",
    })
    assert forged.status_code == 400


def test_alliance_builder_requires_administrator_password(tmp_path):
    secured_app = create_app({
        "TESTING": True, "DATABASE": str(tmp_path / "secured.db"),
        "SECRET_KEY": "test", "AUTH_DISABLED": False,
    })
    client = secured_app.test_client()
    assert client.get("/alliance-builder").status_code == 403
    with client.session_transaction() as session:
        session["is_editor"] = True
        session["member_id"] = 1
    assert client.get("/alliance-builder").status_code == 403
    with client.session_transaction() as session:
        session["is_admin"] = True
    assert client.get("/alliance-builder").status_code == 200
