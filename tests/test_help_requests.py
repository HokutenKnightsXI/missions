from datetime import date, datetime, timedelta

import pytest

from missions import create_app, eastern_today, request_occurs_on


@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "help.db"), "SECRET_KEY": "test", "AUTH_DISABLED": True})


def add_member(client, name, **jobs):
    data = {"name": name, "COP_status": "Not started", "ZILART_status": "Not started"}
    data.update({f"job_{job}": str(level) for job, level in jobs.items()})
    client.post("/members/new", data=data)
    with client.application.app_context():
        import sqlite3
        db = sqlite3.connect(client.application.config["DATABASE"])
        return db.execute("SELECT id FROM members WHERE name=?", (name,)).fetchone()[0]


def identify(client, member_id):
    with client.session_transaction() as session:
        session["member_id"] = member_id
        session["is_editor"] = True


def valid_request(member_id, **overrides):
    future = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    data = {"requester_id": member_id, "title": "Under Observation", "category": "BCNM",
            "zone": "Horlais Peak", "level_cap": "40", "helpers_needed": "2",
            "availability_mode": "now", "expires_at": future, "requester_jobs": ["RDM"]}
    data.update(overrides)
    return data


def test_create_request_and_level_cap_eligibility(app):
    client = app.test_client(); member = add_member(client, "Maven", RDM=75, WAR=37); identify(client, member)
    response = client.post("/help-requests/new", data=valid_request(member), follow_redirects=True)
    assert response.status_code == 200 and b"Under Observation" in response.data
    board = client.get("/help-requests")
    assert b'job-chip eligible">RDM 75' in board.data
    assert b'job-chip ineligible">WAR 37' not in board.data


def test_battlefield_activities_use_validated_zone_dropdown(app):
    client = app.test_client(); member = add_member(client, "Maven", RDM=75); identify(client, member)
    form = client.get("/help-requests/new")
    assert b'id="zone-select"' in form.data and b"Balga" in form.data and b"Dais" in form.data
    assert b">KSNM</option>" in form.data
    invalid = client.post("/help-requests/new", data=valid_request(member, zone="Somewhere Else"))
    assert b"Choose a valid region and zone" in invalid.data


def test_non_battlefield_activities_include_grouped_region_zones(app):
    client = app.test_client(); member = add_member(client, "Maven", RDM=75); identify(client, member)
    form = client.get("/help-requests/new")
    assert b"Ronfaure" in form.data and b"West Ronfaure" in form.data
    assert b"Lumoria (Sea)" in form.data and b"The Garden of Ru" in form.data


def test_activity_filter_supports_parent_sections(app):
    client = app.test_client(); member = add_member(client, "Maven", RDM=75); identify(client, member)
    client.post("/help-requests/new", data=valid_request(member, title="BCNM run", category="BCNM"))
    nm_data = valid_request(member, title="Lottery camp", category="Lottery NM", zone="West Ronfaure")
    client.post("/help-requests/new", data=nm_data)
    parent = client.get("/help-requests?category=section:%F0%9F%91%B9+Notorious+Monsters")
    assert b"Lottery camp" in parent.data and b"BCNM run" not in parent.data
    assert b"All \xf0\x9f\x91\xb9 Notorious Monsters" in parent.data


def test_request_form_offers_all_cop_era_jobs(app):
    client = app.test_client(); member = add_member(client, "Maven", RDM=75); identify(client, member)
    form = client.get("/help-requests/new")
    for job in ("WAR", "MNK", "WHM", "BLM", "RDM", "THF", "PLD", "DRK",
                "BST", "BRD", "RNG", "SAM", "NIN", "DRG", "SMN"):
        assert f'name="requested_jobs" value="{job}"'.encode() in form.data
    for role in ("Tank", "DD", "Healer", "Support"):
        assert f'name="requested_party_roles" value="{role}"'.encode() in form.data


def test_requested_jobs_and_roles_store_optional_counts(app):
    client = app.test_client(); member = add_member(client, "Maven", RDM=75); identify(client, member)
    data = valid_request(member)
    data.update({"requested_jobs": ["WAR", "WHM"], "requested_count_job_WAR": "2",
                 "requested_count_job_WHM": "", "requested_party_roles": ["Tank", "Support"],
                 "requested_count_role_Tank": "1", "requested_count_role_Support": "3"})
    response = client.post("/help-requests/new", data=data, follow_redirects=True)
    assert b"WAR" in response.data and b"2" in response.data and b"Any count" in response.data
    with app.app_context():
        import sqlite3
        db = sqlite3.connect(app.config["DATABASE"])
        specs = db.execute("SELECT role,kind,quantity FROM help_request_roles ORDER BY role").fetchall()
        assert ("WAR", "job", 2) in specs and ("WHM", "job", None) in specs
        assert ("Tank", "role", 1) in specs and ("Support", "role", 3) in specs
    board = client.get("/help-requests")
    assert b"Requested party" in board.data
    assert "WAR · 2".encode() in board.data
    assert "WHM · Any".encode() in board.data


def test_rolling_and_fixed_calendar_rules():
    today = eastern_today(); expiry = datetime.combine(today + timedelta(days=2), datetime.min.time()).isoformat()
    rolling = {"status": "Open", "availability_mode": "now", "start_at": None, "end_at": None, "expires_at": expiry}
    assert request_occurs_on(rolling, today)
    assert not request_occurs_on(rolling, today + timedelta(days=1))
    assert not request_occurs_on(rolling, today + timedelta(days=3))
    fixed_at = datetime.combine(today + timedelta(days=1), datetime.min.time()).isoformat()
    fixed = {**rolling, "availability_mode": "fixed", "start_at": fixed_at}
    assert request_occurs_on(fixed, today + timedelta(days=1)) and not request_occurs_on(fixed, today)
    fixed["status"] = "Completed"
    assert not request_occurs_on(fixed, today + timedelta(days=1))

    after = {**rolling, "availability_mode": "after", "expires_at": None}
    assert request_occurs_on(after, today + timedelta(days=6))
    assert not request_occurs_on(after, today + timedelta(days=7))


def test_rolling_request_does_not_require_expiration(app):
    client = app.test_client(); member = add_member(client, "Prishe", RDM=75); identify(client, member)
    response = client.post("/help-requests/new", data=valid_request(member, expires_at=""))
    assert response.status_code == 302


def test_volunteer_update_prevents_duplicates_and_withdraws(app):
    client = app.test_client(); owner = add_member(client, "Maven", RDM=75); helper = add_member(client, "Lion", WHM=75)
    identify(client, owner); created = client.post("/help-requests/new", data=valid_request(owner), follow_redirects=False)
    request_id = int(created.location.rstrip("/").split("/")[-1]); identify(client, helper)
    client.post(f"/help-requests/{request_id}/volunteer", data={"jobs": ["WHM"], "note": "Ready"})
    client.post(f"/help-requests/{request_id}/volunteer", data={"jobs": ["WHM"], "note": "Updated"})
    with app.app_context():
        import sqlite3
        db = sqlite3.connect(app.config["DATABASE"])
        assert db.execute("SELECT COUNT(*) FROM help_volunteers WHERE request_id=?", (request_id,)).fetchone()[0] == 1
        assert db.execute("SELECT note FROM help_volunteers WHERE request_id=?", (request_id,)).fetchone()[0] == "Updated"
    client.post(f"/help-requests/{request_id}/withdraw")
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        assert db.execute("SELECT COUNT(*) FROM help_volunteers WHERE request_id=?", (request_id,)).fetchone()[0] == 0


def test_request_ownership_and_status_transitions(app):
    client = app.test_client(); owner = add_member(client, "Maven", RDM=75); stranger = add_member(client, "Lion", WHM=75)
    identify(client, owner); created = client.post("/help-requests/new", data=valid_request(owner))
    request_id = int(created.location.rstrip("/").split("/")[-1])
    identify(client, stranger)
    assert client.post(f"/help-requests/{request_id}/status", data={"status": "Cancelled"}).status_code == 403
    identify(client, owner)
    assert client.post(f"/help-requests/{request_id}/status", data={"status": "Forming"}).status_code == 302
    assert client.post(f"/help-requests/{request_id}/status", data={"status": "Expired"}).status_code == 400

    with client.session_transaction() as session:
        session.pop("member_id", None)  # Existing shared editor role acts as administrator.
        session["is_editor"] = True
    assert client.post(f"/help-requests/{request_id}/status", data={"status": "Cancelled"}).status_code == 302


def test_cancelled_request_can_be_edited_and_reactivated(app):
    client = app.test_client(); owner = add_member(client, "Maven", RDM=75); identify(client, owner)
    created = client.post("/help-requests/new", data=valid_request(owner))
    request_id = int(created.location.rstrip("/").split("/")[-1])
    client.post(f"/help-requests/{request_id}/status", data={"status": "Cancelled"})
    edit_page = client.get(f"/help-requests/{request_id}/edit")
    assert b"Save &amp; Reactivate" in edit_page.data
    updated = valid_request(owner, title="Under Observation Again", reactivate="1")
    response = client.post(f"/help-requests/{request_id}/edit", data=updated, follow_redirects=True)
    assert b"reactivated and is open again" in response.data
    assert b'help-badge open">Open' in response.data


def test_my_requests_view_includes_created_requests(app):
    client = app.test_client(); owner = add_member(client, "Maven", RDM=75); identify(client, owner)
    client.post("/help-requests/new", data=valid_request(owner))
    response = client.get("/my-help-requests")
    assert response.status_code == 200 and b"Under Observation" in response.data


def test_expired_requests_are_expired_and_hidden_from_active_board(app):
    client = app.test_client(); owner = add_member(client, "Maven", RDM=75); identify(client, owner)
    old = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    with app.app_context():
        import sqlite3
        db = sqlite3.connect(app.config["DATABASE"])
        db.execute("""INSERT INTO help_requests(requester_id,title,category,availability_mode,expires_at)
                      VALUES(?,?,?,?,?)""", (owner, "Stale run", "Mission", "now", old)); db.commit()
    board = client.get("/help-requests")
    assert b"Stale run" not in board.data


def test_member_and_administrator_permissions_are_separate(tmp_path):
    secured = create_app({"TESTING": True, "DATABASE": str(tmp_path / "roles.db"),
                          "SECRET_KEY": "test", "EDIT_PASSWORD": "hokuten",
                          "ADMIN_PASSWORD": "Idonthave1"})
    client = secured.test_client()
    with secured.app_context():
        import sqlite3
        db = sqlite3.connect(secured.config["DATABASE"])
        first, second = [row[0] for row in db.execute("SELECT id FROM members ORDER BY id LIMIT 2")]

    with client.session_transaction() as session:
        session["is_editor"] = True
        session["member_id"] = first
        session["csrf_token"] = "token"
    assert client.get(f"/members/{first}/edit").status_code == 200
    assert client.get(f"/members/{second}/edit").status_code == 403
    assert client.post(f"/members/{second}/delete", data={"csrf_token": "token"}).status_code == 403

    with client.session_transaction() as session:
        session.clear()
        session["is_admin"] = True
        session["csrf_token"] = "token"
    assert client.get(f"/members/{second}/edit").status_code == 200
    assert client.post(f"/members/{second}/delete", data={"csrf_token": "token"}).status_code == 302


def test_regular_progress_form_uses_signed_in_character(app):
    client = app.test_client(); own = add_member(client, "Maven", RDM=75); identify(client, own)
    response = client.get("/members/new")
    assert response.status_code == 200
    assert b'type="hidden" name="name" value="Maven"' in response.data
    assert b'value="Maven" disabled' in response.data


def test_administrator_password_sets_only_admin_role(tmp_path):
    secured = create_app({"TESTING": True, "DATABASE": str(tmp_path / "admin-login.db"),
                          "SECRET_KEY": "test", "EDIT_PASSWORD": "hokuten",
                          "ADMIN_PASSWORD": "Idonthave1"})
    client = secured.test_client(); client.get("/login")
    with client.session_transaction() as session: token = session["csrf_token"]
    assert client.post("/login", data={"csrf_token": token, "password": "Idonthave1"}).status_code == 302
    with client.session_transaction() as session:
        assert session["is_admin"] is True
        assert session["is_editor"] is False
        assert "member_id" not in session


def test_hokuten_password_adds_and_signs_in_new_player(tmp_path):
    secured = create_app({"TESTING": True, "DATABASE": str(tmp_path / "add-login.db"),
                          "SECRET_KEY": "test", "EDIT_PASSWORD": "different-environment-value",
                          "ADMIN_PASSWORD": "Idonthave1"})
    client = secured.test_client(); client.get("/login")
    with client.session_transaction() as session: token = session["csrf_token"]
    response = client.post("/login", data={"csrf_token": token, "password": "Hokuten",
        "action": "add_player", "new_member_name": "Newplayer", "next": "/help-requests"})
    assert response.status_code == 302 and response.location == "/help-requests"
    with client.session_transaction() as session:
        assert session["is_editor"] is True and session.get("member_id")
    client.get("/logout")
    assert b"Newplayer" in client.get("/login").data


def test_members_panel_is_administrator_only(tmp_path):
    secured = create_app({"TESTING": True, "DATABASE": str(tmp_path / "members-panel.db"),
                          "SECRET_KEY": "test", "EDIT_PASSWORD": "Hokuten",
                          "ADMIN_PASSWORD": "Idonthave1"})
    client = secured.test_client()
    with client.session_transaction() as session:
        session["is_editor"] = True
        session["member_id"] = 1
    assert client.get("/members").status_code == 403
    with client.session_transaction() as session:
        session.clear(); session["is_admin"] = True
    response = client.get("/members")
    assert response.status_code == 200
    assert b"Administrator panel" in response.data
    assert b">Edit</a>" in response.data and b">Delete</button>" in response.data


def test_public_job_roster_shows_job_matrix_and_horizon_profile(app):
    client = app.test_client(); add_member(client, "Maven", WAR=37, RDM=75, SMN=43)
    response = client.get("/job-roster")
    assert response.status_code == 200
    assert b"Job Level Roster" in response.data
    for job in ("WAR", "MNK", "WHM", "BLM", "RDM", "THF", "PLD", "DRK",
                "BST", "BRD", "RNG", "SAM", "NIN", "DRG", "SMN"):
        assert f"<b>{job}</b>".encode() in response.data
    assert b"https://horizonxi.com/players/Maven" in response.data
    assert b'max-level">75' in response.data
    assert b'subjob-level">37' in response.data
    assert b'/static/job-icons.svg#war' in response.data
    assert response.data.count(b'class="level-75-count"') == 15


def test_job_roster_filters_by_level_and_sorts_job_columns(app):
    client = app.test_client()
    add_member(client, "Maven", WAR=37, RDM=75)
    add_member(client, "Lion", WAR=50, RDM=40)
    filtered = client.get("/job-roster?job=RDM&min_level=75")
    assert b"1 character with RDM level 75+" in filtered.data
    assert b"players/Maven" in filtered.data and b"players/Lion" not in filtered.data
    sorted_page = client.get("/job-roster?sort=WAR&direction=desc")
    assert sorted_page.data.index(b"players/Lion") < sorted_page.data.index(b"players/Maven")
    assert b"sort-arrow" in sorted_page.data
