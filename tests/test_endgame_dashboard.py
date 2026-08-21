import json

from missions import ENDGAME_PRIORITY_ITEMS, create_app


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


def test_dragoon_has_tier_one_priority_on_all_hecatomb_gear():
    hecatomb_items = [item for item in ENDGAME_PRIORITY_ITEMS if item["name"].startswith("Hecatomb ")]

    assert {item["name"] for item in hecatomb_items} == {
        "Hecatomb Mittens", "Hecatomb Leggings", "Hecatomb Harness",
    }
    assert all("DRG" in item["p1"] for item in hecatomb_items)


def test_endgame_master_tab_requires_sign_in_and_renders_all_subtabs(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.get("/endgame")
    assert response.status_code == 302
    assert "/login" in response.location

    sign_in(client, admin=True)
    response = client.get("/endgame")
    assert response.status_code == 200
    assert response.data.count(b"data-endgame-view=") == 3
    for view in (b">Calendar</button>", b">DKP/Loot</button>", b">Operations</button>"):
        assert view in response.data
    assert b">Event Calendar</button>" not in response.data
    assert b">Endgame Operations</button>" not in response.data
    for label in (
        b"Item Eligibility", b"Member Detail", b"Event Log",
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
        b'"name": "Adaman Sollerets", "p1": ["WAR"], "p2": ["DRK", "BST"], "p3": []',
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
    assert b'id="priority-family"' not in response.data
    assert b">Loot class<" not in response.data
    assert b"Create new events from Event Calendar" in response.data
    assert b'data-endgame-view="job-selections"' not in response.data
    assert b'id="job-request-dialog"' not in response.data
    assert b'id="request-job-change"' not in response.data
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
    assert b'data-dkp="3"' in alecy_row
    assert b'data-spent="0"' in alecy_row
    assert b'data-earned="3"' in alecy_row
    assert b"DKP balance" in response.data
    assert b"Total spent" in response.data
    assert b"Lifetime earned" in response.data
    assert b"Last event" in response.data
    assert b"Interactive prototype" not in response.data
    assert b"Current bid cap" not in response.data
    assert b"Highest DKP" in response.data
    assert b"Average balance" in response.data
    assert b"Bid Cap" in response.data
    assert b"6 DKP" in response.data
    assert b'"name": "Zenith Mitts"' in response.data
    assert b'"required_level": 73' in response.data
    assert b"P1 may bid" in response.data
    assert b">Cooldown</th>" not in response.data
    assert response.data.count(b"data-loot-sort=") == 6


def test_past_endgame_events_show_most_recent_first(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client, admin=True)

    page = client.get("/endgame").data
    past_endgame = page.split(b"Past Endgame Events", 1)[1].split(b"Past User Events", 1)[0]
    assert past_endgame.index(b"2026-08-13 at 20:00") < past_endgame.index(b"2026-08-06 at 20:00")

    event_log = page.split(b">Past Events</h3>", 1)[1]
    assert event_log.index(b"2026-08-13") < event_log.index(b"2026-08-06")


def test_endgame_admin_controls_render_without_job_change_inbox(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client, admin=True)
    response = client.get("/endgame#jobs")
    assert response.status_code == 200
    assert b"job-change requests need review" not in response.data
    assert b"Record Event" not in response.data
    assert b"Record Loot" in response.data
    assert b"Review requests" not in response.data
    assert b'id="record-loot-dialog"' in response.data
    assert b'id="open-priority-matrix"' in response.data
    assert b"Sky &amp; Sea Priority Matrix" in response.data
    assert b"ENDGAME_IS_ADMIN=true" in response.data
    assert b"roster-column-filters" in response.data
    assert response.data.count(b"data-roster-sort=") == 5
    assert b'Event date and time' in response.data
    assert b'Choose date and time' in response.data
    assert b'id="pick-guild-event-date"' in response.data
    assert b"quarter_hour_picker.js" in response.data
    assert b'type="hidden" name="start_at"' in response.data
    assert b'Gather Location' in response.data
    assert b'name="end_at"' not in response.data
    assert b"Admin Audit" in response.data
    assert b"admin-audit-body" in response.data
    assert response.data.count(b"data-audit-sort=") == 5
    assert response.data.count(b"data-audit-filter=") == 5
    assert b"clear-audit-filters" in response.data
    assert response.data.index(b">Member Detail</button>") < response.data.index(b">Item Eligibility</button>")
    assert b'class="active" type="button" data-endgame-tab="bidding-live"' in response.data
    assert b"Active Bidding" in response.data
    assert b"Auction timer" in response.data
    assert b"Start Auction" in response.data
    roster_html = response.data.split(b'id="endgame-roster-body"', 1)[1]
    assert roster_html.index(b'data-name="alecy"') < roster_html.index(b'data-name="anonym"')


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
    assert b">Operations</button>" in page
    assert b"Item Eligibility" in page
    assert b"Linkshell Loot" in page
    assert b"Linkshell Pops" in page
    assert b"Admin Audit" not in page
    assert b"Record Loot" not in page
    response = client.post("/endgame/events/new", data={
        "csrf_token": "token", "name": "Unauthorized Event",
        "start_at": "2099-08-20T20:00", "location": "Ru'Aun Gardens",
    })
    assert response.status_code == 403


def test_cartuja_is_a_designated_event_admin(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    member_id = database.execute("SELECT id FROM members WHERE name='Cartuja'").fetchone()[0]
    database.close()
    client = app.test_client()
    sign_in(client, member_id=member_id, admin=True)
    assert b"Create Guild Event" in client.get("/endgame").data


def test_past_test_events_are_removed_and_only_archived_sky_is_endgame(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    creator_id = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
    database.executemany(
        """INSERT INTO guild_events
           (creator_member_id,name,start_at,end_at,status,discord_channel)
           VALUES(?,?,?,?,?,?)""",
        [
            (creator_id, "Test Loot Run", "2026-07-01T20:00", "2026-07-01T23:00", "Completed", "endgame-events-only"),
            (creator_id, "Past Dynamis", "2026-07-02T20:00", "2026-07-02T23:00", "Completed", "endgame-events-only"),
            (creator_id, "Chains of Promathia 4-3", "2026-08-20T18:00", "2026-08-20T21:00", "Scheduled", "endgame-events-only"),
            (creator_id, "Community ENM", "2026-08-20T19:00", "2026-08-20T22:00", "Scheduled", "events-posting-and-signup-only"),
            (creator_id, "Sky Gods", "2099-08-20T20:00", "2099-08-20T23:00", "Scheduled", "endgame-events-only"),
        ],
    )
    database.commit()
    database.close()

    # A normal application restart applies the one-time cleanup to an existing DB.
    app = make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute(
        "SELECT 1 FROM guild_events WHERE name='Test Loot Run'"
    ).fetchone() is None
    community_id = database.execute(
        "SELECT id FROM guild_events WHERE name='Community ENM'"
    ).fetchone()[0]
    database.close()
    client = app.test_client()
    sign_in(client, member_id=creator_id, admin=True)
    assert client.post(f"/endgame/events/{community_id}/dkp", data={
        "csrf_token": "token", "dkp_value": "3",
    }).status_code == 400
    page = client.get("/endgame").data
    dynamis = page.split(b'"name": "Past Dynamis"', 1)[0][-500:]
    assert b'"event_kind": "User"' in dynamis
    for name, kind in (
        (b"Chains of Promathia 4-3", b"User"),
        (b"Community ENM", b"User"),
        (b"Sky Gods", b"Endgame"),
    ):
        event = page.split(b'"name": "' + name + b'"', 1)[0][-500:]
        assert b'"event_kind": "' + kind + b'"' in event
    page_text = page.decode("utf-8")
    member_payload = page_text.split("window.ENDGAME_MEMBER_DETAILS=", 1)[1].split(";</script>", 1)[0]
    member_details = json.loads(member_payload)
    history_names = {
        event["name"] for member in member_details.values() for event in member["events"]
    }
    assert "Community ENM" not in history_names
    assert "Chains of Promathia 4-3" not in history_names
    assert "Sky Operations" in history_names
    for date in (b'2026-08-06', b'2026-08-13'):
        sky = page.split(date, 1)[1][:1500]
        assert b"Sky Operations" in sky
    assert b"<b>16</b> going" in page
    assert b"<b>19</b> going" in page


def test_admin_can_edit_event_dkp_and_balance_uses_event_value(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    creator_id = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
    alecy_id = database.execute("SELECT id FROM members WHERE name='Alecy'").fetchone()[0]
    event_id = database.execute(
        """INSERT INTO guild_events
           (creator_member_id,name,start_at,end_at,status)
           VALUES(?,?,?,?, 'Completed')""",
        (creator_id, "Long Sky Run", "2026-08-14T20:00", "2026-08-15T00:30"),
    ).lastrowid
    database.execute(
        "INSERT INTO guild_event_attendance(event_id,member_id,attended) VALUES(?,?,1)",
        (event_id, alecy_id),
    )
    database.commit()
    database.close()

    client = app.test_client()
    sign_in(client, member_id=creator_id, admin=True)
    response = client.post(f"/endgame/events/{event_id}/dkp", data={
        "csrf_token": "token", "dkp_value": "4",
    })
    assert response.status_code == 302
    page = client.get("/endgame").data
    alecy_row = page.split(b'data-name="alecy"', 1)[1].split(b"</tr>", 1)[0]
    assert b'data-dkp="7"' in alecy_row
    assert b'value="4"' in page
    assert client.post(f"/endgame/events/{event_id}/dkp", data={
        "csrf_token": "token", "dkp_value": "4.5",
    }).status_code == 400


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
    assert b"Review requests" not in response.data
    assert b"Admin Audit" in response.data


def test_endgame_javascript_calculates_priority_and_pop_readiness(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client)
    script = client.get("/static/endgame_dashboard.js")
    assert script.status_code == 200
    assert b"jobStatus" in script.data
    assert b"rankMatrixPriority" in script.data
    assert b"priorityTier" in script.data
    assert b"jobRequestDialog" not in script.data
    assert b"b.dkp - a.dkp" in script.data
    assert b"Only P1 candidates may bid" in script.data
    assert b"member.job_levels" in script.data
    assert b">= Number(item.required_level" in script.data
    assert b"endgame:open-live-auction" in script.data
    assert b"scrollIntoView" in script.data
    assert b"rankKey" in script.data
    assert b"displayedRank" in script.data
    assert b'"/api/endgame/pops"' in script.data
    assert b"pop-readiness" in script.data
    assert b"hokuten-job-change-log" in script.data
    assert b"dataset.jobHistory" in script.data
    assert b"data-roster-filter" in script.data
    assert b"event-detail-grid" in script.data
    assert b"hokuten-admin-audit" in script.data
    assert b"hokuten-event-overrides" in script.data
    assert b"data-loot-filter" in script.data
    assert b"refreshJobCooldowns" in script.data
    styles = client.get("/static/endgame_dashboard.css")
    assert b"[data-endgame-view-panel][hidden]{display:none!important}" in styles.data
    assert b"#8d3540" in styles.data


def test_recent_approved_job_change_shows_thirty_day_countdown(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    member_id = database.execute("SELECT id FROM members WHERE name='Alecy'").fetchone()[0]
    database.execute(
        """INSERT INTO endgame_job_change_requests
           (member_id,requested_main,requested_secondary,status,reviewed_at)
           VALUES(?,?,?,'Approved',CURRENT_TIMESTAMP)""",
        (member_id, "RDM", "BLM"),
    )
    database.commit()
    database.close()
    client = app.test_client()
    sign_in(client, admin=True)
    page = client.get("/endgame")
    assert b"Job change: 29d" in page.data


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
        "start_at": "2099-08-20T20:00", "end_at": "2099-08-20T23:00", "location": "Ru'Aun Gardens",
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
        (creator_id, "Sea Night", "2099-08-20T20:00", "2099-08-20T23:00", "message-1"),
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


def test_event_bot_resolves_retired_and_html_encoded_character_names(monkeypatch, tmp_path):
    import sqlite3
    import missions

    app = make_app(tmp_path)
    app.config.update(
        HOKUTEN_EVENT_BOT_API_URL="https://events.example.test",
        HOKUTEN_EVENT_BOT_API_TOKEN="shared-secret",
    )
    database = sqlite3.connect(app.config["DATABASE"])
    creator_id = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
    killboi_id = database.execute("INSERT INTO members(name) VALUES('Killboi')").lastrowid
    event_id = database.execute(
        """INSERT INTO guild_events
           (creator_member_id,name,start_at,end_at,discord_message_id)
           VALUES(?,?,?,?,?)""",
        (creator_id, "Alias Night", "2099-08-20T20:00", "2099-08-20T23:00", "alias-message"),
    ).lastrowid
    database.commit()
    database.close()

    monkeypatch.setattr(missions, "hokuten_event_bot_request", lambda *_args, **_kwargs: {
        "event": {"players": {
            "KB&#x20;": {"status": "going", "job": "DRG"},
            "Soya": {"status": "maybe", "job": "BST"},
        }}
    })
    client = app.test_client()
    sign_in(client, admin=True)
    assert client.post(f"/endgame/events/{event_id}/sync", data={"csrf_token": "token"}).status_code == 302

    database = sqlite3.connect(app.config["DATABASE"])
    rows = database.execute(
        """SELECT m.name,s.rsvp_status,s.selected_job FROM guild_event_signups s
           JOIN members m ON m.id=s.member_id WHERE s.event_id=? ORDER BY m.name""", (event_id,),
    ).fetchall()
    database.close()
    assert rows == [("Killboi", "going", "DRG"), ("Soyabean", "maybe", "BST")]
    assert killboi_id


def test_startup_removes_soya_duplicate_and_preserves_signup(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    creator_id = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
    soya_id = database.execute(
        "INSERT INTO members(name,discord_name,discord_user_id) VALUES(?,?,?)",
        ("Soya", "SoyaDiscord", "discord-soya"),
    ).lastrowid
    event_id = database.execute(
        """INSERT INTO guild_events(creator_member_id,name,start_at,end_at)
           VALUES(?,?,?,?)""",
        (creator_id, "Old Name Night", "2099-09-01T20:00", "2099-09-01T23:00"),
    ).lastrowid
    database.execute(
        """INSERT INTO guild_event_signups
           (event_id,member_id,rsvp_status,selected_job,discord_name)
           VALUES(?,?,?,?,?)""",
        (event_id, soya_id, "going", "BST", "Soya"),
    )
    database.commit()
    database.close()

    make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT 1 FROM members WHERE name='Soya'").fetchone() is None
    assert database.execute(
        "SELECT discord_user_id,discord_name FROM members WHERE name='Soyabean'"
    ).fetchone() == ("discord-soya", "SoyaDiscord")
    signup = database.execute(
        """SELECT m.name,s.rsvp_status,s.selected_job FROM guild_event_signups s
           JOIN members m ON m.id=s.member_id WHERE s.event_id=?""", (event_id,),
    ).fetchone()
    database.close()
    assert signup == ("Soyabean", "going", "BST")


def test_startup_removes_encoded_kb_duplicate_and_preserves_signup(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    creator_id = database.execute("SELECT id FROM members WHERE name='Imaven'").fetchone()[0]
    killboi_id = database.execute("INSERT INTO members(name) VALUES('Killboi')").lastrowid
    kb_id = database.execute("INSERT INTO members(name) VALUES('KB&#x20;')").lastrowid
    event_id = database.execute(
        "INSERT INTO guild_events(creator_member_id,name,start_at,end_at) VALUES(?,?,?,?)",
        (creator_id, "Encoded Name Night", "2099-09-02T20:00", "2099-09-02T23:00"),
    ).lastrowid
    database.execute(
        "INSERT INTO guild_event_signups(event_id,member_id,discord_name) VALUES(?,?,?)",
        (event_id, kb_id, "KB&#x20;"),
    )
    database.commit()
    database.close()

    make_app(tmp_path)
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT 1 FROM members WHERE name='KB&#x20;'").fetchone() is None
    assert database.execute(
        "SELECT member_id FROM guild_event_signups WHERE event_id=?", (event_id,),
    ).fetchone() == (killboi_id,)
    database.close()


def test_admin_can_import_discord_created_events_without_duplicates(monkeypatch, tmp_path):
    import sqlite3
    import missions

    app = make_app(tmp_path)
    app.config.update(
        HOKUTEN_EVENT_BOT_API_URL="https://events.example.test",
        HOKUTEN_EVENT_BOT_API_TOKEN="shared-secret",
    )
    calls = []

    def fake_event_bot(_url, _token, method, path, payload=None):
        calls.append((method, path, payload))
        if path in {"/api/events/discord-message-manual-1", "/api/events/discord-message-user-1"}:
            return {"success": True, "event": {"players": {
                "Imaven": {"status": "going", "job": "BLM"},
                "Sexualpotato": {"status": "maybe", "job": "RDM"},
            }}}
        return {"success": True, "events": [{
            "message_id": "discord-message-manual-1",
            "scheduled_event_id": "discord-event-manual-1",
            "title": "⚔️ **Hokuten Knights — First LS Dynamis Run 8:00 PM EST**",
            "date": "Wednesday August 19 2026", "time": "8:00 PM",
            "description": "First linkshell Dynamis run", "location": "Ru'Lude Gardens",
            "channel": "endgame-events-only",
        }, {
            "message_id": "discord-message-user-1", "scheduled_event_id": "discord-event-user-1",
            "name": "Member Assault Night", "date": "Thursday August 20 2026", "time": "9:00 PM",
            "location": "Aht Urhgan Whitegate", "channel_name": "linkshell-events",
        }]}

    monkeypatch.setattr(missions, "hokuten_event_bot_request", fake_event_bot)
    client = app.test_client()
    sign_in(client, admin=True)
    page = client.get("/endgame")
    assert b"Sync Events &amp; Signups" in page.data

    first = client.post("/endgame/events/sync-discord", data={"csrf_token": "token"})
    second = client.post("/endgame/events/sync-discord", data={"csrf_token": "token"})
    assert first.status_code == 302 and second.status_code == 302
    assert [call[1] for call in calls].count("/api/events") == 2
    assert [call[1] for call in calls].count("/api/events/discord-message-manual-1") == 2
    assert [call[1] for call in calls].count("/api/events/discord-message-user-1") == 2

    database = sqlite3.connect(app.config["DATABASE"])
    rows = database.execute(
        """SELECT name,start_at,location,discord_event_id,discord_message_id
           FROM guild_events WHERE discord_message_id='discord-message-manual-1'"""
    ).fetchall()
    audit = database.execute(
        "SELECT action,details FROM admin_change_log WHERE action='Discord events synchronized' ORDER BY id"
    ).fetchall()
    signups = database.execute(
        """SELECT m.name,s.rsvp_status,s.selected_job FROM guild_event_signups s
           JOIN members m ON m.id=s.member_id
           WHERE s.event_id=(SELECT id FROM guild_events WHERE discord_message_id='discord-message-manual-1')
           ORDER BY m.name"""
    ).fetchall()
    channels = database.execute(
        "SELECT name,discord_channel FROM guild_events WHERE discord_message_id<>'' ORDER BY name"
    ).fetchall()
    database.close()
    assert rows == [(
        "First LS Dynamis Run", "2026-08-19T20:00", "Ru'Lude Gardens",
        "discord-event-manual-1", "discord-message-manual-1",
    )]
    assert audit[-1][1] == "0 imported / 0 linked / 0 skipped"
    assert signups == [("Imaven", "going", "BLM"), ("Sexualpotato", "maybe", "RDM")]
    assert channels == [
        ("First LS Dynamis Run", "endgame-events-only"),
        ("Member Assault Night", "linkshell-events"),
    ]
    calendar = client.get("/endgame")
    assert b"Upcoming Endgame Events" in calendar.data
    assert b"Upcoming User Events" in calendar.data
    assert b"Endgame Event" in calendar.data and b"User Event" in calendar.data


def test_discord_event_import_is_admin_only_and_requires_api_config(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client, member_id=2, admin=False)
    response = client.post("/endgame/events/sync-discord", data={"csrf_token": "token"})
    assert response.status_code == 403
    sign_in(client, admin=True)
    assert client.post(
        "/endgame/events/sync-discord", data={"csrf_token": "token"}
    ).status_code == 400


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
            "job": "NIN", "family": "Legs", "distribution": "P2",
        "classification": "Major Loot", "dkp_cost": "2",
    })
    assert response.status_code == 302
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute(
        "SELECT member_id FROM guild_event_attendance WHERE event_id=?", (event_id,)
    ).fetchall() == [(member_id,)]
    assert database.execute(
        "SELECT recipient_member_id,item,job,family,distribution,classification,dkp_cost FROM endgame_loot_awards WHERE id=?",
        (award_id,),
    ).fetchone() == (member_id, "Byakko's Haidate", "NIN", "Legs", "P2", "Major Loot", 2.0)
    database.close()
    alecy_row = client.get("/endgame").data.split(b'data-name="alecy"', 1)[1].split(b"</tr>", 1)[0]
    assert b'data-dkp="1"' in alecy_row
    assert b'data-spent="2"' in alecy_row

    sexualpotato_row = client.get("/endgame").data.split(
        b'data-name="sexualpotato"', 1
    )[1].split(b"</tr>", 1)[0]
    assert b'data-dkp="3"' in sexualpotato_row

    member_payload = client.get("/endgame").data.split(
        b"window.ENDGAME_MEMBER_DETAILS=", 1
    )[1].split(b";</script>", 1)[0]
    member_details = json.loads(member_payload)
    sexualpotato = next(member for member in member_details.values() if member["name"] == "Sexualpotato")
    assert sexualpotato["lifetime_earned"] == 3
    assert sexualpotato["dkp"] == 3

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


def test_archived_attendance_edits_add_and_subtract_member_dkp(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client, admin=True)
    database = sqlite3.connect(app.config["DATABASE"])
    event_id = database.execute("SELECT id FROM guild_events ORDER BY start_at LIMIT 1").fetchone()[0]
    bodom_id = database.execute("SELECT id FROM members WHERE name='Bodom'").fetchone()[0]
    database.close()

    assert client.post(f"/endgame/events/{event_id}/attendance", data={
        "csrf_token": "token", "member_ids": [str(bodom_id)],
    }).status_code == 302
    bodom_row = client.get("/endgame").data.split(b'data-name="bodom"', 1)[1].split(b"</tr>", 1)[0]
    assert b'data-earned="9"' in bodom_row
    assert b'data-dkp="9"' in bodom_row

    assert client.post(f"/endgame/events/{event_id}/attendance", data={
        "csrf_token": "token", "member_ids": [],
    }).status_code == 302
    page = client.get("/endgame").data
    bodom_row = page.split(b'data-name="bodom"', 1)[1].split(b"</tr>", 1)[0]
    assert b'data-earned="6"' in bodom_row
    assert b'data-dkp="6"' in bodom_row
    member_details = json.loads(
        page.split(b"window.ENDGAME_MEMBER_DETAILS=", 1)[1].split(b";</script>", 1)[0]
    )
    bodom = next(member for member in member_details.values() if member["name"] == "Bodom")
    assert bodom["lifetime_earned"] == 6
    assert bodom["dkp"] == 6


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
        "start_at": "2099-08-20T20:00", "location": "Ru'Aun Gardens",
    })
    assert response.status_code == 302
    assert calls[0][0:4] == (
        "https://events.example.test", "shared-secret", "POST", "/api/events",
    )
    assert calls[0][4]["duration"] == "3"
    assert calls[0][4]["date"] == "Thursday August 20 2099"
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
def test_sky_auction_includes_complete_seiryu_pool(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client, member_id=1, admin=True)

    import sqlite3
    database = sqlite3.connect(app.config["DATABASE"])
    event_id = database.execute(
        "SELECT id FROM guild_events WHERE name='Sky Operations' ORDER BY id LIMIT 1"
    ).fetchone()[0]
    database.close()

    started = client.post("/endgame/auctions", data={
        "csrf_token": "token", "event_id": str(event_id), "boss": "Seiryu", "duration_minutes": "3",
    })
    assert started.status_code == 302
    auction = client.get("/api/endgame/auctions").get_json()["auctions"][0]
    assert {item["item"] for item in auction["items"]} == {
        "Seiryu's Kote", "Seiryu's Sword", "Aquarian Abjuration: Legs",
        "Dryadic Abjuration: Head", "Martial Abjuration: Head", "Wyrmal Abjuration: Hands",
    }
    deleted = client.post(f"/endgame/auctions/{auction['id']}/delete", data={"csrf_token": "token"})
    assert deleted.status_code == 302
    assert client.get("/api/endgame/auctions").get_json()["auctions"] == []

    assert client.post("/endgame/auctions", data={
        "csrf_token": "token", "event_id": str(event_id), "boss": "Suzaku", "duration_minutes": "3",
    }).status_code == 302
    auction = client.get("/api/endgame/auctions").get_json()["auctions"][0]
    leggings = next(item for item in auction["items"] if item["item"] == "Neptunal Abjuration: Feet")
    assert leggings["target_item"] == "Hecatomb Leggings"
    assert leggings["tooltip"]["item_id"] == 14180
    assert leggings["tooltip"]["name"] == "Hecatomb Leggings"
    assert leggings["tooltip"]["slots"] == ["Feet"]
    assert "STR+6" in leggings["tooltip"]["description"]


def test_live_dkp_auction_records_winner_and_deducts_balance(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    client = app.test_client()
    sign_in(client, member_id=1, admin=True)
    database = sqlite3.connect(app.config["DATABASE"])
    event_id = database.execute(
        "SELECT id FROM guild_events WHERE name='Sky Operations' ORDER BY id LIMIT 1"
    ).fetchone()[0]
    second_event_id = database.execute(
        "SELECT id FROM guild_events WHERE name='Sky Operations' ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    database.execute(
        "INSERT OR REPLACE INTO member_jobs(member_id,custom_name,job,level) VALUES(1,'','BLM',75)"
    )
    database.execute(
        "INSERT OR REPLACE INTO member_jobs(member_id,custom_name,job,level) VALUES(1,'','RDM',75)"
    )
    database.execute(
        "INSERT OR REPLACE INTO member_jobs(member_id,custom_name,job,level) VALUES(1,'','DRG',75)"
    )
    database.execute(
        "INSERT OR REPLACE INTO guild_event_attendance(event_id,member_id,attended) VALUES(?,1,1)",
        (event_id,),
    )
    database.execute(
        "INSERT OR REPLACE INTO guild_event_attendance(event_id,member_id,attended) VALUES(?,1,1)",
        (second_event_id,),
    )
    database.execute(
        "INSERT OR REPLACE INTO member_jobs(member_id,custom_name,job,level) VALUES(2,'','BLM',75)"
    )
    database.execute(
        "INSERT OR REPLACE INTO guild_event_attendance(event_id,member_id,attended) VALUES(?,2,1)",
        (event_id,),
    )
    database.execute(
        """INSERT INTO endgame_loot_awards
           (event_id,recipient_member_id,item,job,family,distribution,classification,dkp_cost,recorded_by)
           VALUES(?,2,'Prior Award','BLM','Accessories','Freelot','Standard',2,1)""",
        (event_id,),
    )
    database.commit()
    database.close()

    started = client.post("/endgame/auctions", data={
        "csrf_token": "token", "event_id": str(event_id), "boss": "Jailer of Love", "duration_minutes": "5",
    })
    assert started.status_code == 302
    payload = client.get("/api/endgame/auctions").get_json()
    assert payload["my_balance"] == 6
    assert payload["auctions"][0]["boss"] == "Jailer of Love"
    assert payload["auctions"][0]["ends_at"] > payload["auctions"][0]["starts_at"]
    novio = next(item for item in payload["auctions"][0]["items"] if item["item"] == "Novio Earring")
    novia = next(item for item in payload["auctions"][0]["items"] if item["item"] == "Novia Earring")
    love = next(item for item in payload["auctions"][0]["items"] if item["item"] == "Love Torque")
    assert novio["eligible_jobs"][0]["job"] == "BLM"
    assert novio["tooltip"]["name"] == "Novio Earring"
    assert novio["tooltip"]["description"]
    denied = client.post(f"/api/endgame/auction-items/{novia['id']}/bid", json={
        "job": "BLM", "amount": 1,
    }, headers={"X-CSRF-Token": "token"})
    assert denied.status_code == 403

    bid = client.post(f"/api/endgame/auction-items/{novio['id']}/bid", json={
        "job": "BLM", "amount": 2,
    }, headers={"X-CSRF-Token": "token"})
    assert bid.status_code == 200
    assert bid.get_json()["auction"]["auctions"][0]["items"][1]["bids"] or bid.get_json()["auction"]["recent_bids"]
    second_bid = client.post(f"/api/endgame/auction-items/{novia['id']}/bid", json={
        "job": "RDM", "amount": 2,
    }, headers={"X-CSRF-Token": "token"})
    assert second_bid.status_code == 200
    database = sqlite3.connect(app.config["DATABASE"])
    database.execute(
        """INSERT INTO endgame_loot_awards
           (event_id,recipient_member_id,item,job,family,distribution,classification,dkp_cost,recorded_by)
           VALUES(?,1,'Balance Adjustment','BLM','Other','Standard','Standard',1,1)""",
        (event_id,),
    )
    database.commit()
    database.close()
    rebalanced = client.post(f"/api/endgame/auction-items/{love['id']}/bid", json={
        "job": "DRG", "amount": 2,
    }, headers={"X-CSRF-Token": "token"})
    assert rebalanced.status_code == 200
    assert rebalanced.get_json()["adjusted"] == [{
        "item": "Novia Earring", "from": 2, "to": 1,
    }]
    committed = client.get("/api/endgame/auctions").get_json()
    assert committed["my_reserved"] == 5
    assert committed["my_available"] == 0

    database = sqlite3.connect(app.config["DATABASE"])
    database.execute(
        "INSERT INTO endgame_auction_bids(auction_item_id,member_id,job,amount) VALUES(?,2,'BLM',2)",
        (novio["id"],),
    )
    database.commit()
    database.close()
    tied = client.get("/api/endgame/auctions").get_json()["auctions"][0]
    tied_novio = next(item for item in tied["items"] if item["id"] == novio["id"])
    assert tied_novio["suggested_winner_id"] == 1

    paused = client.post(f"/endgame/auctions/{tied['id']}/pause", data={"csrf_token": "token"})
    assert paused.status_code == 302
    assert client.get("/api/endgame/auctions").get_json()["auctions"][0]["paused"] is True
    blocked_while_paused = client.post(f"/api/endgame/auction-items/{novio['id']}/bid", json={
        "job": "BLM", "amount": 3,
    }, headers={"X-CSRF-Token": "token"})
    assert blocked_while_paused.status_code == 400
    resumed = client.post(f"/endgame/auctions/{tied['id']}/pause", data={"csrf_token": "token"})
    assert resumed.status_code == 302
    assert client.get("/api/endgame/auctions").get_json()["auctions"][0]["paused"] is False

    database = sqlite3.connect(app.config["DATABASE"])
    auction_id = database.execute("SELECT id FROM endgame_auctions ORDER BY id DESC LIMIT 1").fetchone()[0]
    database.execute("UPDATE endgame_auctions SET ends_at='2000-01-01T00:00:00' WHERE id=?", (auction_id,))
    database.commit()
    database.close()
    closed = client.get("/api/endgame/auctions").get_json()["auctions"][0]
    assert closed["status"] == "Closed"

    confirmed = client.post(f"/endgame/auctions/{auction_id}/confirm", data={
        "csrf_token": "token", f"winner_{novio['id']}": "1",
    })
    assert confirmed.status_code == 302
    database = sqlite3.connect(app.config["DATABASE"])
    award = database.execute(
        "SELECT item,dkp_cost,distribution FROM endgame_loot_awards WHERE item='Novio Earring' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    status = database.execute("SELECT status FROM endgame_auctions WHERE id=?", (auction_id,)).fetchone()[0]
    database.close()
    assert award == ("Novio Earring", 2.0, "P1")
    assert status == "Confirmed"
    assert client.get("/api/endgame/auctions").get_json()["my_balance"] == 3
