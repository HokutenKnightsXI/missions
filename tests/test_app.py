import pytest
import json
import re

import missions
from missions import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "SECRET_KEY": "test", "AUTH_DISABLED": True})
    return app.test_client()


def test_updates_require_shared_password(tmp_path):
    app = create_app({
        "TESTING": True, "DATABASE": str(tmp_path / "auth.db"),
        "SECRET_KEY": "test", "EDIT_PASSWORD": "shell-secret",
    })
    client = app.test_client()
    response = client.get("/members/new")
    assert response.status_code == 302
    assert "/login?next=/members/new" in response.location

    client.get("/login")
    with client.session_transaction() as session:
        token = session["csrf_token"]
    wrong = client.post("/login", data={"password": "wrong", "csrf_token": token})
    assert b"Incorrect linkshell password" in wrong.data
    signed_in = client.post("/login", data={
        "password": "shell-secret", "csrf_token": token, "next": "/members/new",
    })
    assert signed_in.status_code == 302
    assert signed_in.location == "/members/new"
    assert client.get("/members/new").status_code == 200


def test_post_rejects_missing_csrf_token(tmp_path):
    app = create_app({
        "TESTING": True, "DATABASE": str(tmp_path / "csrf.db"),
        "SECRET_KEY": "test", "EDIT_PASSWORD": "shell-secret",
    })
    assert app.test_client().post("/login", data={"password": "shell-secret"}).status_code == 400


def test_empty_board_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Chains of Promathia" in response.data
    assert b"Rise of the Zilart" in response.data
    assert b"Not selected" in response.data


def test_add_and_filter_member(client):
    response = client.post("/members/new", data={
        "name": "Aldo", "discord_name": "aldo", "timezone": "Central",
        "availability": "Friday evenings", "job_PLD": "75", "job_WHM": "60",
        "COP_chapter": "Chapter 2", "COP_mission": "The Mothercrystals",
        "COP_status": "Ready for help", "COP_details": "Promyvion-Mea",
        "ZILART_chapter": "ZM4", "ZILART_mission": "The Temple of Uggalepih",
        "ZILART_status": "In progress", "ZILART_details": "Need keys",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Saved Aldo" in response.data
    assert b"The Mothercrystals" in response.data
    assert b"PLD 75" in response.data
    assert b"The Temple of Uggalepih" in response.data

    filtered = client.get("/?campaign=COP&job=PLD&status=Ready+for+help")
    assert b"The Mothercrystals" in filtered.data
    assert b"Need keys" not in filtered.data


def test_requires_a_job(client):
    response = client.post("/members/new", data={"name": "Lion"})
    assert response.status_code == 200
    assert b"Add at least one job" in response.data


def test_horizon_job_lookup(client, monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps({
                "name": "Akaldok",
                "jobs": {"WAR": 37, "RDM": 75, "NIN": 75, "SMN": 0},
            }).encode()

    monkeypatch.setattr(missions, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    response = client.get("/api/horizon-player/Akaldok")
    assert response.status_code == 200
    assert response.json == {"name": "Akaldok", "jobs": {"WAR": 37, "RDM": 75, "NIN": 75}}


def test_horizon_lookup_rejects_invalid_name(client):
    response = client.get("/api/horizon-player/not-a-name")
    assert response.status_code == 400


def test_mission_form_uses_grouped_dropdowns(client):
    response = client.get("/members/new")
    assert response.status_code == 200
    assert b"Look up jobs" not in response.data
    assert b"enter its current level" in response.data
    assert b'optgroup label="Chapter 1' in response.data
    assert "CoP 1-3 – The Mothercrystals".encode() in response.data
    assert "ZM1 – The New Frontier".encode() in response.data
    assert "ZM14 – Ark Angels".encode() in response.data
    assert "ZM18 – The Last Verse".encode() in response.data
    assert b'data-chapter-input="COP"' in response.data
    cop_complete = response.data.index(b'value="Complete"', response.data.index(b'data-mission-select="COP"'))
    assert cop_complete > response.data.index("CoP 8-5".encode())


def test_progress_form_selects_registered_member_and_populates_jobs(client):
    client.post("/members/new", data={
        "name": "Prishe", "job_WHM": "75", "job_BRD": "60",
    })

    chooser = client.get("/members/new")
    assert b'id="progress-member-select"' in chooser.data
    assert b'>Prishe</option>' in chooser.data

    member_id = re.search(rb'/members/(\d+)/edit[^>]*>Prishe</option>', chooser.data).group(1).decode()
    edit_form = client.get(f"/members/{member_id}/edit")
    assert b'value="75" placeholder=' in edit_form.data
    assert b'value="60" placeholder=' in edit_form.data
    assert edit_form.data.count(b'class="job-available" checked') == 2


def test_dashboard_groups_members_by_mission(client):
    client.post("/members/new", data={
        "name": "Tarantula", "job_NIN": "75", "job_WAR": "37",
        "COP_chapter": "Chapter 1 – Ancient Flames Beckon",
        "COP_mission": "CoP 1-3 – The Mothercrystals",
        "COP_status": "Ready for help",
        "COP_details": "Cutscenes done",
        "ZILART_mission": "ZM14 – Ark Angels", "ZILART_chapter": "ZM14",
        "ZILART_status": "In progress",
    })
    response = client.get("/")
    assert b'<table class="progress-table">' in response.data
    assert b"CoP 1-3" in response.data
    assert b"Tarantula" in response.data
    assert b"Jobs:</b> NIN 75, WAR 37" in response.data
    assert b"Status:</b> Ready for help" in response.data
    assert b"Extra notes:</b> Cutscenes done" in response.data
    assert b'class="availability"' in response.data
    assert b"ZM14" in response.data


def test_old_zilart_numbering_is_migrated_without_losing_progress(tmp_path):
    database = str(tmp_path / "migration.db")
    config = {"TESTING": True, "DATABASE": database, "SECRET_KEY": "test", "AUTH_DISABLED": True}
    first_client = create_app(config).test_client()
    first_client.post("/members/new", data={
        "name": "Lion", "job_THF": "75", "COP_status": "Not started",
        "ZILART_mission": "ZM9 – Ark Angels", "ZILART_chapter": "ZM9",
        "ZILART_status": "Ready for help",
    })

    migrated_client = create_app(config).test_client()
    response = migrated_client.get("/")
    assert b"ZM14" in response.data
    assert b"Ark Angels" in response.data
    assert b">Lion<span" in response.data


def test_add_progress_updates_an_existing_character(client):
    client.post("/members/new", data={
        "name": "Lion", "job_WHM": "50",
        "COP_mission": "CoP 1-2 – Below the Arks",
        "COP_chapter": "Chapter 1 – Ancient Flames Beckon",
        "COP_status": "In progress",
        "ZILART_status": "Not started",
    })
    response = client.post("/members/new", data={
        "name": "lion", "job_WHM": "60", "job_BLM": "40",
        "COP_mission": "CoP 1-3 – The Mothercrystals",
        "COP_chapter": "Chapter 1 – Ancient Flames Beckon",
        "COP_status": "Ready for help",
        "ZILART_status": "Not started",
    }, follow_redirects=True)
    assert response.status_code == 200
    # One appearance in each campaign table, not duplicate roster records.
    assert response.data.count(b'>lion<span class="member-tooltip">') == 6
    assert b"CoP 1-3" in response.data
    assert b"BLM 40, WHM 60" in response.data
    assert b"CoP 1-2" in response.data  # The standard empty mission row still exists.


def test_complete_selection_places_member_in_final_helper_row(client):
    response = client.post("/members/new", data={
        "name": "Prishe", "job_MNK": "75",
        "COP_mission": "Complete", "COP_chapter": "Complete",
        "COP_status": "In progress", "ZILART_status": "Not started",
    }, follow_redirects=True)
    assert b"Campaign complete" in response.data
    assert b">Prishe<span" in response.data
    assert b"Status:</b> Complete" in response.data


def test_summary_counts_dreamlands_and_each_campaign_clear(client):
    client.post("/members/new", data={
        "name": "Tenzen", "job_SAM": "75",
        "COP_mission": "CoP 4-1 – Sheltering Doubt", "COP_status": "In progress",
        "ZILART_mission": "Complete", "ZILART_status": "Complete",
    })
    client.post("/members/new", data={
        "name": "Ulmia", "job_BRD": "75",
        "COP_mission": "Complete", "COP_status": "Complete",
        "ZILART_status": "Not started",
    })
    response = client.get("/")
    assert b"2</strong><span>Dynamis Dreamlands" in response.data
    assert b"1</strong><span>CoP cleared" in response.data
    assert b"1</strong><span>ZM cleared" in response.data


def test_dashboard_includes_toau_and_three_city_mission_tables(client):
    response = client.get("/")
    for heading in ("Treasures of Aht Urhgan", "San d&#39;Oria Missions",
                    "Bastok Missions", "Windurst Missions"):
        assert heading.encode() in response.data
    assert b"ToAU 01" in response.data
    assert b"San d&#39;Oria 1-1" in response.data
    assert b"Bastok 1-1" in response.data
    assert b"Windurst 1-1" in response.data
    headings = [response.data.index(name) for name in (
        b"Rise of the Zilart", b"Chains of Promathia", b"Treasures of Aht Urhgan",
        b"Windurst Missions", b"San d&#39;Oria Missions", b"Bastok Missions",
    )]
    assert headings == sorted(headings)
