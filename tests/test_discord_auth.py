import sqlite3
from urllib.parse import parse_qs, urlparse

import missions
from missions import create_app


def discord_app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "discord.db"),
        "SECRET_KEY": "test",
        "AUTH_DISABLED": False,
        "DISCORD_CLIENT_ID": "client-id",
        "DISCORD_CLIENT_SECRET": "client-secret",
        "DISCORD_GUILD_ID": "hokuten-guild",
        "DISCORD_REDIRECT_URI": "https://example.test/discord/callback",
    })


def begin_discord_login(client):
    client.get("/discord/connect")
    with client.session_transaction() as session:
        csrf = session["csrf_token"]
    response = client.post("/discord/login", data={"csrf_token": csrf})
    assert response.status_code == 302
    query = parse_qs(urlparse(response.location).query)
    assert query["scope"] == ["identify guilds.members.read"]
    return query["state"][0]


def mock_discord(monkeypatch, nickname, user_id="discord-123"):
    monkeypatch.setattr(missions, "discord_exchange_code", lambda *_args: {"access_token": "token"})
    monkeypatch.setattr(
        missions, "discord_get",
        lambda _token, path: ({"id": user_id, "username": "discord-user", "global_name": "Discord User"}
                              if path == "/users/@me" else {"nick": nickname}),
    )


def test_discord_confirmation_requires_exact_server_nickname(tmp_path):
    client = discord_app(tmp_path).test_client()
    page = client.get("/discord/connect")
    assert b"Match your character name" in page.data
    assert b"exactly matches my HorizonXI character" in page.data
    assert b"Sign in with Discord" in page.data
    assert b"Your exact character name" in page.data
    assert b"Discord server nickname must be" in page.data
    assert b"2\xe2\x80\x9315 letters" not in page.data
    assert b"password sign-in" not in page.data
    assert b"Administrator access" in page.data and b"Imaven" in page.data


def test_existing_character_is_linked_without_duplicate(monkeypatch, tmp_path):
    app = discord_app(tmp_path)
    client = app.test_client()
    state = begin_discord_login(client)
    mock_discord(monkeypatch, "imaven")
    response = client.get(f"/discord/callback?code=valid&state={state}", follow_redirects=True)
    assert b"Signed in with Discord as Imaven" in response.data
    assert b"Alliance Builder" in response.data
    assert b">Members</a>" not in response.data
    with client.session_transaction() as session:
        assert session["is_admin"] is True
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT COUNT(*) FROM members WHERE name='Imaven'").fetchone()[0] == 1
    assert database.execute("SELECT discord_user_id FROM members WHERE name='Imaven'").fetchone()[0] == "discord-123"
    database.close()


def test_new_discord_nickname_creates_and_signs_in_character(monkeypatch, tmp_path):
    app = discord_app(tmp_path)
    client = app.test_client()
    state = begin_discord_login(client)
    mock_discord(monkeypatch, "Newhero", "discord-456")
    response = client.get(f"/discord/callback?code=valid&state={state}")
    assert response.status_code == 302 and "/members/" in response.location
    database = sqlite3.connect(app.config["DATABASE"])
    member = database.execute(
        "SELECT id,discord_user_id FROM members WHERE name='Newhero'"
    ).fetchone()
    assert member and member[1] == "discord-456"
    database.close()
    with client.session_transaction() as session:
        assert session["member_id"] == member[0]
        assert session["is_editor"] is True
        assert session["is_admin"] is False


def test_invalid_or_decorated_nickname_is_not_linked(monkeypatch, tmp_path):
    app = discord_app(tmp_path)
    client = app.test_client()
    state = begin_discord_login(client)
    mock_discord(monkeypatch, "Imaven | RDM")
    response = client.get(f"/discord/callback?code=valid&state={state}", follow_redirects=True)
    assert b"2\xe2\x80\x9315 letters only" in response.data
    database = sqlite3.connect(app.config["DATABASE"])
    assert database.execute("SELECT COUNT(*) FROM members WHERE discord_user_id<>''").fetchone()[0] == 0
    database.close()


def test_discord_callback_rejects_invalid_state(tmp_path):
    client = discord_app(tmp_path).test_client()
    assert client.get("/discord/callback?code=valid&state=forged").status_code == 400


def test_shared_member_password_is_disabled_when_discord_is_configured(tmp_path):
    app = discord_app(tmp_path)
    client = app.test_client()
    page = client.get("/login")
    assert b"Members now sign in securely with Discord" in page.data
    assert b'name="member_id"' not in page.data
    with client.session_transaction() as session:
        csrf = session["csrf_token"]
    rejected = client.post("/login", data={
        "csrf_token": csrf, "password": "Hokuten", "action": "sign_in",
    })
    assert b"Incorrect linkshell password" in rejected.data
