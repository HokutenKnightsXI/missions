from missions import create_app


def make_app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "endgame.db"),
        "SECRET_KEY": "test",
        "AUTH_DISABLED": False,
    })


def sign_in(client, member_id=1, admin=False):
    with client.session_transaction() as session:
        session["is_editor"] = True
        session["is_admin"] = admin
        session["member_id"] = member_id
        session["csrf_token"] = "token"


def test_endgame_master_tab_requires_sign_in_and_renders_all_subtabs(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.get("/endgame")
    assert response.status_code == 302
    assert "/login" in response.location

    sign_in(client, admin=True)
    response = client.get("/endgame")
    assert response.status_code == 200
    for label in (
        b"Priority Calculator", b"Member Detail", b"Event Log",
        b"Linkshell Loot", b"Linkshell Pops",
    ):
        assert label in response.data
    assert b"Blood Saber" not in response.data
    assert b"Gem of the East" in response.data
    assert b"High-Quality Euvhi Organ" in response.data
    assert b"Jailer of Love" in response.data
    assert b"Byakko&#39;s Haidate" in response.data
    assert b"Novio Earring" in response.data
    assert b"Crimson Finger Gauntlets" in response.data
    assert b'"p3": ["THF", "WHM"]' in response.data
    for priority in (
        b'"name": "Seiryu\\u0027s Kote", "p1": ["RNG"], "p2": ["SAM", "NIN"]',
        b'"name": "Adaman Celata", "p1": ["WAR"], "p2": ["DRK", "BST"]',
        b'"name": "Adaman Sollerets", "p1": ["WAR"], "p2": ["DRK", "BST"], "p3": [], "source": "Byakko"',
        b'"name": "Crimson Greaves", "p1": ["PLD"], "p2": ["RDM", "RNG"]',
        b'"name": "Justice Torque", "p1": ["DRK", "SAM"], "p2": [], "p3": []',
        b'"name": "Temperance Torque", "p1": ["BST"], "p2": ["WAR"]',
        b'"name": "Love Torque", "p1": ["DRG", "THF"], "p2": ["COR"], "p3": ["BRD"]',
    ):
        assert priority in response.data
    assert b'<option value="">Select an item</option>' in response.data
    assert b"Byakko" in response.data
    assert b"Jailer of Faith" in response.data
    assert response.data.count(b"priority-source-heading") >= 10
    assert b'id="priority-source" value=""' in response.data
    assert b'id="priority-family" value=""' in response.data
    assert b">Loot class<" not in response.data
    assert b"Create new events from Event Calendar" in response.data
    assert b'data-endgame-view="job-selections"' not in response.data
    assert b'id="job-request-dialog"' in response.data
    assert b'data-open-server-event=' in response.data
    assert b"Attendance Roster" not in response.data
    assert b"Upcoming Events" in response.data
    assert b"Past Events" in response.data
    assert b"Loot Drops" in response.data
    assert b"Edit Loot" in response.data
    assert b"Edit Attendance" in response.data
    assert b"loot-column-filters" in response.data
    assert b"ENDGAME_MEMBER_DETAILS" in response.data
    assert b'data-name="alecy"' in response.data
    alecy_row = response.data.split(b'data-name="alecy"', 1)[1].split(b"</tr>", 1)[0]
    assert b'data-attendance="50"' in alecy_row
    assert b"Interactive prototype" not in response.data
    assert b'data-tier="2"' in alecy_row
    assert response.data.count(b"data-loot-sort=") == 7


def test_endgame_admin_sees_decision_inbox(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client, admin=True)
    response = client.get("/endgame#jobs")
    assert response.status_code == 200
    assert b"job-change requests need review" in response.data
    assert b"Record Event" not in response.data
    assert b"Record Loot" in response.data
    assert b"Review requests" in response.data
    assert b'id="record-loot-dialog"' in response.data
    assert b'id="open-priority-matrix"' in response.data
    assert b"Sky &amp; Sea Priority Matrix" in response.data
    assert b"ENDGAME_IS_ADMIN=true" in response.data
    assert b"roster-column-filters" in response.data
    assert response.data.count(b"data-roster-sort=") == 8
    assert b'Event date and time' in response.data
    assert b'Choose date and time' in response.data
    assert b'id="pick-guild-event-date"' in response.data
    assert b"quarter_hour_picker.js" in response.data
    assert b'type="hidden" name="start_at"' in response.data
    assert b'Gather Location' in response.data
    assert b'name="end_at"' not in response.data
    assert b"Admin Audit" in response.data
    assert b"admin-audit-body" in response.data


def test_only_designated_admins_can_create_guild_events(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    client = app.test_client()
    database = sqlite3.connect(app.config["DATABASE"])
    ordinary_id = database.execute("SELECT id FROM members WHERE name='Alecy'").fetchone()[0]
    database.close()
    sign_in(client, member_id=ordinary_id, admin=True)
    page = client.get("/endgame").data
    assert b"Create Guild Event" not in page
    assert b"Endgame Operations</button>" in page
    assert b"Priority Calculator" in page
    assert b"Linkshell Loot" in page
    assert b"Linkshell Pops" in page
    assert b"Admin Audit" not in page
    assert b"Record Loot" not in page
    response = client.post("/endgame/events/new", data={
        "csrf_token": "token", "name": "Unauthorized Event",
        "start_at": "2026-08-20T20:00", "location": "Ru'Aun Gardens",
    })
    assert response.status_code == 403


def test_linked_admin_character_does_not_depend_on_stale_session_flag(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    app.config.update(
        DISCORD_CLIENT_ID="client", DISCORD_CLIENT_SECRET="secret",
        DISCORD_GUILD_ID="guild", DISCORD_REDIRECT_URI="https://example.test/callback",
        DISCORD_ADMIN_USER_ID="verified-imaven",
    )
    client = app.test_client()
    database = sqlite3.connect(app.config["DATABASE"])
    database.execute(
        "UPDATE members SET discord_user_id='verified-imaven' WHERE name='Imaven'"
    )
    database.commit()
    member_id = database.execute(
        "SELECT id FROM members WHERE name='Imaven'"
    ).fetchone()[0]
    database.close()
    sign_in(client, member_id=member_id, admin=False)
    response = client.get("/endgame#jobs")
    assert b"Review requests" in response.data


def test_endgame_javascript_calculates_priority_and_pop_readiness(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client)
    script = client.get("/static/endgame_dashboard.js")
    assert script.status_code == 200
    assert b"jobStatus" in script.data
    assert b"rankMatrixPriority" in script.data
    assert b"priorityTier" in script.data
    assert b'item.family' in script.data
    assert b"hokuten-pop-prototype" in script.data
    assert b"pop-readiness" in script.data
    assert b"hokuten-job-change-log" in script.data
    assert b"dataset.jobHistory" in script.data
    assert b"data-roster-filter" in script.data
    assert b"event-detail-grid" in script.data
    assert b"hokuten-admin-audit" in script.data
    assert b"hokuten-event-overrides" in script.data
    assert b"data-loot-filter" in script.data
    styles = client.get("/static/endgame_dashboard.css")
    assert b"[data-endgame-view-panel][hidden]{display:none!important}" in styles.data
    assert b"#8d3540" in styles.data


def test_guild_event_creates_discord_event_syncs_signups_and_tracks_attendance(monkeypatch, tmp_path):
    import sqlite3
    import missions

    app = make_app(tmp_path)
    app.config.update(
        DISCORD_BOT_TOKEN="bot-token", DISCORD_GUILD_ID="guild-id",
        DISCORD_EVENT_CHANNEL_ID="endgame-channel-id",
    )
    calls = []

    def fake_discord(_token, method, path, payload=None):
        calls.append((method, path, payload))
        if method == "POST":
            return {"id": "discord-event-1"}
        return [{"user": {"id": "discord-member-1"}}]

    monkeypatch.setattr(missions, "discord_bot_request", fake_discord)
    database = sqlite3.connect(app.config["DATABASE"])
    database.execute(
        "UPDATE members SET discord_user_id='discord-member-1' WHERE name='Sexualpotato'"
    )
    database.commit()
    member_id = database.execute("SELECT id FROM members WHERE name='Sexualpotato'").fetchone()[0]
    database.close()

    client = app.test_client()
    sign_in(client, admin=True)
    response = client.post("/endgame/events/new", data={
        "csrf_token": "token", "name": "Sky Gods", "description": "Four gods and Kirin",
        "start_at": "2026-08-20T20:00", "end_at": "2026-08-20T23:00", "location": "Ru'Aun Gardens",
    })
    assert response.status_code == 302
    database = sqlite3.connect(app.config["DATABASE"])
    event_id, discord_id, message_id = database.execute(
        "SELECT id,discord_event_id,discord_message_id FROM guild_events WHERE name='Sky Gods'"
    ).fetchone()
    database.close()
    assert discord_id == "discord-event-1"
    assert message_id == "discord-event-1"
    assert calls[0][2]["entity_type"] == 3
    assert calls[1][0:2] == ("POST", "/channels/endgame-channel-id/messages")
    signup = calls[1][2]
    assert "Sky Gods" in signup["embeds"][0]["title"]
    assert any(field["name"] == "📊 Confirmed Alliance Setup" for field in signup["embeds"][0]["fields"])
    assert [button["custom_id"] for button in signup["components"][0]["components"]] == [
        "hokuten_event_going", "hokuten_event_maybe", "hokuten_event_cant",
        "hokuten_event_choose_job", "hokuten_event_edit",
    ]

    assert client.post(f"/endgame/events/{event_id}/sync", data={"csrf_token": "token"}).status_code == 302
    assert client.post(f"/endgame/events/{event_id}/attendance", data={
        "csrf_token": "token", "member_ids": [str(member_id)],
    }).status_code == 302
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT member_id FROM guild_event_signups").fetchall() == [(member_id,)]
    assert database.execute(
        "SELECT member_id FROM guild_event_attendance WHERE event_id=?", (event_id,)
    ).fetchall() == [(member_id,)]
    database.close()

    page = client.get("/endgame#event-calendar")
    assert b"Sky Gods" in page.data
    assert b"Sexualpotato" in page.data
    assert b"Currently scheduled" in page.data
    assert b"Create new events from Event Calendar" in page.data
    alliance = client.get("/alliance-builder")
    assert b'id="alliance-guild-event"' in alliance.data
    assert b"Sky Gods" in alliance.data


def test_event_bot_rsvps_include_status_and_job_in_alliance_builder(monkeypatch, tmp_path):
    import sqlite3
    import missions

    app = make_app(tmp_path)
    app.config.update(
        HOKUTEN_EVENT_BOT_API_URL="https://events.example.test",
        HOKUTEN_EVENT_BOT_API_TOKEN="shared-secret",
    )
    database = sqlite3.connect(app.config["DATABASE"])
    creator_id = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
    event_id = database.execute(
        """INSERT INTO guild_events
           (creator_member_id,name,start_at,end_at,discord_message_id)
           VALUES(?,?,?,?,?)""",
        (creator_id, "Sea Night", "2026-08-20T20:00", "2026-08-20T23:00", "message-1"),
    ).lastrowid
    database.commit()
    database.close()

    def fake_event_bot(_url, _token, method, path, payload=None):
        assert (method, path, payload) == ("GET", "/api/events/message-1", None)
        return {"success": True, "event": {"players": {
            "Imaven": {"status": "going", "job": "BLM"},
            "Sexualpotato": {"status": "maybe", "job": "RDM"},
            "Vlathgar": {"status": "cant", "job": "PLD"},
        }}}

    monkeypatch.setattr(missions, "hokuten_event_bot_request", fake_event_bot)
    client = app.test_client()
    sign_in(client, admin=True)
    response = client.post(f"/endgame/events/{event_id}/sync", data={"csrf_token": "token"})
    assert response.status_code == 302

    database = sqlite3.connect(app.config["DATABASE"])
    rows = database.execute(
        """SELECT m.name,s.rsvp_status,s.selected_job FROM guild_event_signups s
           JOIN members m ON m.id=s.member_id WHERE s.event_id=? ORDER BY m.name""", (event_id,),
    ).fetchall()
    database.close()
    assert rows == [
        ("Imaven", "going", "BLM"),
        ("Sexualpotato", "maybe", "RDM"),
        ("Vlathgar", "cant", "PLD"),
    ]

    calendar = client.get("/endgame#event-calendar")
    assert b"Discord Alliance Signups" in calendar.data
    assert b"Magic Damage" in calendar.data
    assert b"Healing" in calendar.data
    assert b"Can't Attend (1)" in calendar.data
    assert b"Sync Signups to Attendance" in calendar.data
    assert b"Mark absent players as Missing" in calendar.data

    database = sqlite3.connect(app.config["DATABASE"])
    imaven_id = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
    database.close()
    synced = client.post(
        f"/endgame/events/{event_id}/attendance/from-signups",
        data={"csrf_token": "token", "missing_ids": str(imaven_id)},
    )
    assert synced.status_code == 302
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute(
        "SELECT member_id FROM guild_event_attendance WHERE event_id=?", (event_id,),
    ).fetchall() == []
    audit = database.execute(
        "SELECT action,details FROM admin_change_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    database.close()
    assert audit[0] == "Attendance synced from Discord signups"
    assert "missing Imaven" in audit[1]

    alliance = client.get("/alliance-builder")
    assert b'"status": "going"' in alliance.data
    assert b'"job": "BLM"' in alliance.data
    assert b'"status": "maybe"' in alliance.data
    assert b'<optgroup label="Upcoming Events">' in alliance.data
    assert b'<optgroup label="Past Events">' in alliance.data
    script = client.get("/static/alliance_builder.js?v=5")
    assert b"discord-selected-job" in script.data
    assert b"Signed up as" in script.data


def test_designated_admin_can_edit_archived_attendance_and_loot(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    client = app.test_client()
    database = sqlite3.connect(app.config["DATABASE"])
    event_id = database.execute("SELECT id FROM guild_events ORDER BY start_at LIMIT 1").fetchone()[0]
    award_id = database.execute(
        "SELECT id FROM endgame_loot_awards WHERE event_id=? ORDER BY id LIMIT 1", (event_id,)
    ).fetchone()[0]
    member_id = database.execute("SELECT id FROM members WHERE name='Alecy'").fetchone()[0]
    database.close()

    sign_in(client, admin=True)
    response = client.post(f"/endgame/events/{event_id}/attendance", data={
        "csrf_token": "token", "member_ids": [str(member_id)],
    })
    assert response.status_code == 302
    response = client.post(f"/endgame/loot/{award_id}/update", data={
        "csrf_token": "token", "member_id": str(member_id), "item": "Byakko's Haidate",
        "job": "NIN", "family": "Legs", "distribution": "Secondary priority",
        "classification": "Major Loot",
    })
    assert response.status_code == 302
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute(
        "SELECT member_id FROM guild_event_attendance WHERE event_id=?", (event_id,)
    ).fetchall() == [(member_id,)]
    assert database.execute(
        "SELECT recipient_member_id,item,job,family,distribution,classification FROM endgame_loot_awards WHERE id=?",
        (award_id,),
    ).fetchone() == (member_id, "Byakko's Haidate", "NIN", "Legs", "Secondary priority", "Major Loot")
    database.close()

    assert client.post(f"/endgame/loot/{award_id}/delete", data={"csrf_token": "token"}).status_code == 302
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT 1 FROM endgame_loot_awards WHERE id=?", (award_id,)).fetchone() is None
    assert database.execute("SELECT COUNT(*) FROM admin_change_log").fetchone()[0] >= 3
    attendance_audit = database.execute(
        "SELECT details FROM admin_change_log WHERE area='Event Attendance' ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    assert "added none" in attendance_audit
    assert "removed Sexualpotato" in attendance_audit
    database.close()


def test_ordinary_member_cannot_edit_archived_loot(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    client = app.test_client()
    database = sqlite3.connect(app.config["DATABASE"])
    award_id = database.execute("SELECT id FROM endgame_loot_awards ORDER BY id LIMIT 1").fetchone()[0]
    ordinary_id = database.execute("SELECT id FROM members WHERE name='Alecy'").fetchone()[0]
    database.close()
    sign_in(client, member_id=ordinary_id, admin=True)
    assert client.post(f"/endgame/loot/{award_id}/delete", data={"csrf_token": "token"}).status_code == 403


def test_admin_event_delete_removes_discord_event_and_database_record(monkeypatch, tmp_path):
    import sqlite3
    import missions

    app = make_app(tmp_path)
    app.config.update(
        DISCORD_BOT_TOKEN="bot-token", DISCORD_GUILD_ID="guild-id",
        DISCORD_EVENT_CHANNEL_ID="channel-id",
    )
    calls = []
    monkeypatch.setattr(
        missions, "discord_bot_request",
        lambda token, method, path, payload=None: calls.append((method, path)) or None,
    )
    database = sqlite3.connect(app.config["DATABASE"])
    event_id = database.execute("SELECT id FROM guild_events ORDER BY id LIMIT 1").fetchone()[0]
    database.execute(
        "UPDATE guild_events SET discord_event_id='discord-event-1',discord_message_id='message-1' WHERE id=?",
        (event_id,),
    )
    database.commit()
    database.close()
    client = app.test_client()
    sign_in(client, admin=True)
    assert client.post(f"/endgame/events/{event_id}/delete", data={"csrf_token": "token"}).status_code == 302
    assert calls == [
        ("DELETE", "/channels/channel-id/messages/message-1"),
        ("DELETE", "/guilds/guild-id/scheduled-events/discord-event-1"),
    ]
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT 1 FROM guild_events WHERE id=?", (event_id,)).fetchone() is None
    database.close()


def test_event_delete_continues_when_discord_message_is_already_missing(monkeypatch, tmp_path):
    import sqlite3
    from urllib.error import HTTPError
    import missions

    app = make_app(tmp_path)
    app.config.update(
        DISCORD_BOT_TOKEN="bot-token", DISCORD_GUILD_ID="guild-id",
        DISCORD_EVENT_CHANNEL_ID="channel-id",
    )
    calls = []

    def fake_discord(_token, method, path, payload=None):
        calls.append((method, path))
        if "/messages/" in path:
            raise HTTPError(path, 404, "Unknown Message", {}, None)
        return None

    monkeypatch.setattr(missions, "discord_bot_request", fake_discord)
    database = sqlite3.connect(app.config["DATABASE"])
    event_id = database.execute("SELECT id FROM guild_events ORDER BY id LIMIT 1").fetchone()[0]
    database.execute(
        "UPDATE guild_events SET discord_event_id='discord-event-1',discord_message_id='message-1' WHERE id=?",
        (event_id,),
    )
    database.commit()
    database.close()

    client = app.test_client()
    sign_in(client, admin=True)
    response = client.post(f"/endgame/events/{event_id}/delete", data={"csrf_token": "token"})
    assert response.status_code == 302
    assert calls[-1] == (
        "DELETE", "/guilds/guild-id/scheduled-events/discord-event-1",
    )
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT 1 FROM guild_events WHERE id=?", (event_id,)).fetchone() is None
    database.close()


def test_event_creation_prefers_private_event_bot_api(monkeypatch, tmp_path):
    import sqlite3
    import missions

    app = make_app(tmp_path)
    app.config.update(
        HOKUTEN_EVENT_BOT_API_URL="https://events.example.test",
        HOKUTEN_EVENT_BOT_API_TOKEN="shared-secret",
        DISCORD_EVENT_CHANNEL_ID="channel-id",
        DISCORD_BOT_TOKEN="discord-token",
    )
    calls = []

    def fake_event_api(base_url, token, method, path, payload=None):
        calls.append((base_url, token, method, path, payload))
        return {"success": True, "event": {
            "scheduled_event_id": "scheduled-1", "message_id": "message-1",
        }}

    monkeypatch.setattr(missions, "hokuten_event_bot_request", fake_event_api)
    monkeypatch.setattr(
        missions, "discord_bot_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("direct Discord fallback used")),
    )
    client = app.test_client()
    sign_in(client, admin=True)
    response = client.post("/endgame/events/new", data={
        "csrf_token": "token", "name": "API Sky", "description": "Test",
        "start_at": "2026-08-20T20:00", "location": "Ru'Aun Gardens",
    })
    assert response.status_code == 302
    assert calls[0][0:4] == (
        "https://events.example.test", "shared-secret", "POST", "/api/events",
    )
    assert calls[0][4]["duration"] == "3"
    assert calls[0][4]["date"] == "Thursday August 20 2026"
    assert calls[0][4]["time"] == "8:00 PM"
    assert calls[0][4]["channel"] == "endgame-events-only"
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute(
        "SELECT discord_event_id,discord_message_id FROM guild_events WHERE name='API Sky'"
    ).fetchone() == ("scheduled-1", "message-1")
    database.close()


def test_event_creation_rejects_past_time_before_calling_discord(monkeypatch, tmp_path):
    import missions

    app = make_app(tmp_path)
    app.config.update(
        HOKUTEN_EVENT_BOT_API_URL="https://events.example.test",
        HOKUTEN_EVENT_BOT_API_TOKEN="shared-secret",
    )
    monkeypatch.setattr(
        missions, "hokuten_event_bot_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("event API called")),
    )
    client = app.test_client()
    sign_in(client, admin=True)
    response = client.post("/endgame/events/new", data={
        "csrf_token": "token", "name": "Past Event",
        "start_at": "2020-01-01T20:00", "location": "Hokuten Knights",
    })
    assert response.status_code == 400
    assert b"Choose an event date and time in the future" in response.data
