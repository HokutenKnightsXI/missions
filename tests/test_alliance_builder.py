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


def identify(client, member_id):
    with client.session_transaction() as session:
        session["is_editor"] = True
        session["member_id"] = member_id


def test_alliance_builder_uses_job_roster_and_three_parties(app):
    maven, _lion = add_roster(app)
    client = app.test_client()
    identify(client, maven)
    page = client.get("/alliance-builder")
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
    assert b'id="alliance-character-search"' in page.data
    assert page.data.count(b'class="add-custom-slot"') == 18
    assert b'id="custom-alliance-dialog"' in page.data
    assert b"Alliance name <i>Required</i>" in page.data
    assert b'id="pick-event-date"' in page.data
    assert b'class="native-date-input"' in page.data
    assert b"Minimum level" not in page.data
    assert b"Level 75 Jobs" in page.data
    script = client.get("/static/alliance_builder.js")
    assert b"dragstart" in script.data and b"drag-over" in script.data


def test_member_can_save_and_reopen_own_alliance_layout(app):
    maven, lion = add_roster(app)
    client = app.test_client()
    identify(client, maven)
    response = client.post("/alliance-builder/save", data={
        "name": "Dynamis - Xarcabard", "event_at": "2026-08-08T20:00",
        "notes": "Gather in Ru'Lude Gardens",
        "member_1_1": str(maven), "job_1_1": "PLD",
        "member_2_1": str(lion), "job_2_1": "WHM",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Saved alliance layout for Dynamis - Xarcabard" in response.data
    assert f'data-member="{maven}"'.encode() in response.data and b'data-job="PLD"' in response.data
    assert f'data-member="{lion}"'.encode() in response.data and b'data-job="WHM"' in response.data
    with app.app_context():
        database = sqlite3.connect(app.config["DATABASE"])
        assert database.execute("SELECT COUNT(*) FROM alliance_events").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM alliance_slots").fetchone()[0] == 2
        database.close()


def test_custom_character_assignment_is_saved_and_reopened(app):
    maven, _lion = add_roster(app)
    client = app.test_client()
    identify(client, maven)
    response = client.post("/alliance-builder/save", data={
        "name": "Guest Layout", "custom_name_3_6": "Guestplayer", "job_3_6": "BRD",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'data-custom-name="Guestplayer"' in response.data
    assert b'data-job="BRD"' in response.data
    with app.app_context():
        database = sqlite3.connect(app.config["DATABASE"])
        slot = database.execute(
            "SELECT member_id,custom_name,job FROM alliance_slots"
        ).fetchone()
        assert slot == (None, "Guestplayer", "BRD")
        database.close()


def test_alliance_save_rejects_duplicate_members_and_unrostered_jobs(app):
    maven, _lion = add_roster(app)
    client = app.test_client()
    identify(client, maven)
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


def test_alliance_builder_requires_member_sign_in_not_administrator(tmp_path):
    secured_app = create_app({
        "TESTING": True, "DATABASE": str(tmp_path / "secured.db"),
        "SECRET_KEY": "test", "AUTH_DISABLED": False,
    })
    client = secured_app.test_client()
    assert client.get("/alliance-builder").status_code == 302
    with client.session_transaction() as session:
        session["is_editor"] = True
        session["member_id"] = 1
    assert client.get("/alliance-builder").status_code == 200
    with client.session_transaction() as session:
        session.pop("member_id", None)
        session["is_admin"] = True
    assert client.get("/alliance-builder").status_code == 403


def test_saved_alliances_are_private_and_deletable_from_loader(app):
    maven, lion = add_roster(app)
    client = app.test_client()
    identify(client, maven)
    created = client.post("/alliance-builder/save", data={
        "name": "Maven's Layout", "member_1_1": str(maven), "job_1_1": "PLD",
    }, follow_redirects=False)
    event_id = int(created.location.split("event=")[-1])
    owner_page = client.get("/alliance-builder")
    assert b"Maven&#39;s Layout" in owner_page.data
    assert f'/alliance-builder/{event_id}/delete'.encode() in owner_page.data

    identify(client, lion)
    assert b"Maven&#39;s Layout" not in client.get("/alliance-builder").data
    assert client.get(f"/alliance-builder?event={event_id}").status_code == 404
    assert client.post(f"/alliance-builder/{event_id}/delete").status_code == 404

    identify(client, maven)
    deleted = client.post(f"/alliance-builder/{event_id}/delete", follow_redirects=True)
    assert deleted.status_code == 200
    assert b"Deleted alliance layout" in deleted.data
    with app.app_context():
        database = sqlite3.connect(app.config["DATABASE"])
        assert database.execute("SELECT COUNT(*) FROM alliance_events").fetchone()[0] == 0
        database.close()
