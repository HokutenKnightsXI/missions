import os
import sqlite3
import json
import hmac
import re
import secrets
import calendar
from datetime import date, datetime, time, timedelta
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for


JOBS = (
    "WAR", "MNK", "WHM", "BLM", "RDM", "THF", "PLD", "DRK", "BST",
    "BRD", "RNG", "SAM", "NIN", "DRG", "SMN",
)
CAMPAIGNS = ("ZILART", "COP", "TOAU", "WINDURST", "SANDORIA", "BASTOK")
CAMPAIGN_NAMES = {
    "COP": "Chains of Promathia", "ZILART": "Rise of the Zilart",
    "TOAU": "Treasures of Aht Urhgan", "SANDORIA": "San d'Oria Missions",
    "BASTOK": "Bastok Missions", "WINDURST": "Windurst Missions",
}
STATUSES = ("Not started", "In progress", "Ready for help", "Complete")
HELP_SECTIONS = {
    "🏰 Missions": (
        "City Missions", "Rise of the Zilart Missions", "Chains of Promathia Missions",
        "Treasures of Aht Urhgan Missions",
    ),
    "⚔️ Quests": ("Limit Break Quest", "Artifact Quests", "Other Quest Help", "Weapon Skill Quest"),
    "👹 Notorious Monsters": ("Lottery NM", "Timed NM", "Trigger NM", "Pop Item Farm"),
    "☁️ Sky": ("Sky Pop Farm",),
    "🌊 Sea": ("Organ Farm", "Chip Farm", "Sea Cape Farm"),
    "🏛️ Limbus": ("Temenos", "Apollyon"),
    "🏯 Aht Urhgan": (
        "Assault", "Nyzul Isle", "Salvage", "Besieged", "Imperial Standing Farm", "Mythic Milestone",
    ),
    "⚡ Battlefields": ("BCNM", "KSNM", "ENM", "Avatar Fights", "Divine Might", "Ark Angels"),
    "📈 Character Progression": ("Merit Party", "Skillup Party", "WeaponSkill Latent Break", "Testimony Farm"),
}
HELP_CATEGORIES = tuple(activity for activities in HELP_SECTIONS.values() for activity in activities)
BF_ZONES = (
    "Balga's Dais", "Horlais Peak", "Waughroon Shrine", "Ghelsba Outpost", "Qu'Bia Arena",
    "Chamber of Oracles", "Sacrificial Chamber", "Throne Room", "Monarch Linn",
    "Sealion's Den", "Riverne Site A01", "Riverne Site B01", "Bearclaw Pinnacle",
    "Boneyard Gully", "Mine Shaft #2716", "Full Moon Fountain", "Celestial Nexus",
    "La'Loff Amphitheater", "Empyreal Paradox", "The Shrouded Maw",
)
PARTY_ROLES = ("Tank", "DD", "Healer", "Support")
REGION_ZONES = {
    "Ronfaure": ("West Ronfaure", "East Ronfaure", "Ghelsba Outpost", "Fort Ghelsba", "Yughott Grotto"),
    "Zulkheim": ("La Theine Plateau", "Valkurm Dunes", "Konschtat Highlands", "Gusgen Mines"),
    "Gustaberg": ("North Gustaberg", "South Gustaberg", "Dangruf Wadi", "Zeruhn Mines", "Palborough Mines"),
    "Derfland": ("Pashhow Marshlands", "Rolanberry Fields", "Beadeaux", "Crawler's Nest"),
    "Sarutabaruta": ("West Sarutabaruta", "East Sarutabaruta", "Giddeus", "Inner Horutoto Ruins", "Outer Horutoto Ruins", "Central Horutoto Ruins"),
    "Kolshushu": ("Tahrongi Canyon", "Buburimu Peninsula", "Maze of Shakhrami", "Bibiki Bay", "Manaclipper"),
    "Aragoneu": ("Meriphataud Mountains", "Castle Oztroja"),
    "Norvallen": ("Jugner Forest", "Batallia Downs", "Davoi", "Eldieme Necropolis"),
    "Qufim": ("Qufim Island", "Lower Delkfutt's Tower", "Middle Delkfutt's Tower", "Upper Delkfutt's Tower"),
    "Li'Telor": ("The Sanctuary of Zi'Tah", "Ro'Maeve", "Hall of the Gods"),
    "Kuzotz": ("Eastern Altepa Desert", "Western Altepa Desert", "Rabao", "Quicksand Caves"),
    "Vollbow": ("Sauromugue Champaign", "Garlaige Citadel", "Cape Teriggan", "Valley of Sorrows"),
    "Elshimo Lowlands": ("Yuhtunga Jungle", "Temple of Uggalepih", "Den of Rancor"),
    "Elshimo Uplands": ("Yhoator Jungle", "Ifrit's Cauldron"),
    "Fauregandi": ("Beaucedine Glacier", "Fei'Yin"),
    "Valdeaunia": ("Xarcabard", "Castle Zvahl Baileys", "Castle Zvahl Keep"),
    "Tu'Lia (Sky)": ("Ru'Aun Gardens", "Shrine of Ru'Avitau", "Ve'Lugannon Palace"),
    "Tavnazian Archipelago": ("Lufaise Meadows", "Misareaux Coast", "Phomiuna Aqueducts", "Sacrarium", "Riverne - Site #A01", "Riverne - Site #B01"),
    "Movalpolos": ("Oldton Movalpolos", "Newton Movalpolos"),
    "Lumoria (Sea)": ("Al'Taieu", "Grand Palace of Hu'Xzoi", "The Garden of Ru'Hmet"),
}
HELP_ZONES = {
    activity: ({"Battlefields": BF_ZONES} if activity in ("BCNM", "KSNM", "ENM") else REGION_ZONES)
    for activity in HELP_CATEGORIES
}
HELP_STATUSES = ("Open", "Forming", "Full", "Completed", "Cancelled", "Expired")
ACTIVE_HELP_STATUSES = ("Open", "Forming", "Full")
LOGIN_CHARACTERS = (
    "Imaven", "Sexualpotato", "Vlathgar", "Soyabean", "Chickenbanana",
    "Alecy", "Rhode", "Shiru", "Venenua", "Teeje", "Mygas", "Starnack",
    "HMP", "Ivalin", "Cartuja", "Throkell", "Shurgajoe", "Zanth", "Zaelin",
    "Kaeru", "Firewater", "Anonym", "Ramenwarrior", "Kalindra", "Eunos",
    "Brewski", "Bodom", "Werx", "Palumbo", "Hikari", "Gravekeeper",
)
AVAILABILITY_MODES = {
    "now": "Today/Now — PM Me",
    "after": "Any Time After",
    "fixed": "Specific Date/Time",
}
HELP_STATUS_TRANSITIONS = {
    "Open": {"Forming", "Full", "Completed", "Cancelled"},
    "Forming": {"Open", "Full", "Completed", "Cancelled"},
    "Full": {"Open", "Forming", "Completed", "Cancelled"},
    "Completed": set(), "Cancelled": {"Open"}, "Expired": {"Open"},
}
EASTERN_TIME = ZoneInfo("America/New_York")
HORIZON_API = "https://api.horizonxi.com/api/v1"

MISSION_OPTIONS = {
    "ZILART": [
        ("Rise of the Zilart", [
            ("ZM1 – The New Frontier", "ZM1"),
            ("ZM2 – Welcome t'Norg", "ZM2"),
            ("ZM3 – Kazham's Chieftainess", "ZM3"),
            ("ZM4 – The Temple of Uggalepih", "ZM4"),
            ("ZM5 – Headstone Pilgrimage", "ZM5"),
            ("ZM6 – Through the Quicksand Caves", "ZM6"),
            ("ZM7 – The Chamber of Oracles", "ZM7"),
            ("ZM8 – Return to Delkfutt's Tower", "ZM8"),
            ("ZM9 – Ro'Maeve", "ZM9"),
            ("ZM10 – The Temple of Desolation", "ZM10"),
            ("ZM11 – The Hall of the Gods", "ZM11"),
            ("ZM12 – The Mithra and the Crystal", "ZM12"),
            ("ZM13 – The Gate of the Gods", "ZM13"),
            ("ZM14 – Ark Angels", "ZM14"),
            ("ZM15 – The Sealed Shrine", "ZM15"),
            ("ZM16 – The Celestial Nexus", "ZM16"),
            ("ZM17 – Awakening", "ZM17"),
            ("ZM18 – The Last Verse (epilogue shared with CoP after Apocalypse Nigh)", "ZM18"),
            ("Complete", "Complete"),
        ]),
    ],
    "COP": [
        ("Chapter 1 – Ancient Flames Beckon", [
            ("CoP 1-1 – The Rites of Life", "Chapter 1 – Ancient Flames Beckon"),
            ("CoP 1-2 – Below the Arks", "Chapter 1 – Ancient Flames Beckon"),
            ("CoP 1-3 – The Mothercrystals", "Chapter 1 – Ancient Flames Beckon"),
        ]),
        ("Chapter 2 – The Isle of Forgotten Saints", [
            ("CoP 2-1 – An Invitation West", "Chapter 2 – The Isle of Forgotten Saints"),
            ("CoP 2-2 – The Lost City", "Chapter 2 – The Isle of Forgotten Saints"),
            ("CoP 2-3 – Distant Beliefs", "Chapter 2 – The Isle of Forgotten Saints"),
            ("CoP 2-4 – An Eternal Melody", "Chapter 2 – The Isle of Forgotten Saints"),
            ("CoP 2-5 – Ancient Vows", "Chapter 2 – The Isle of Forgotten Saints"),
        ]),
        ("Chapter 3 – A Transient Dream", [
            ("CoP 3-1 – The Call of the Wyrmking", "Chapter 3 – A Transient Dream"),
            ("CoP 3-2 – A Vessel Without a Captain", "Chapter 3 – A Transient Dream"),
            ("CoP 3-3 – The Road Forks", "Chapter 3 – A Transient Dream"),
            ("CoP 3-4 – Tending Aged Wounds", "Chapter 3 – A Transient Dream"),
            ("CoP 3-5 – Darkness Named", "Chapter 3 – A Transient Dream"),
        ]),
        ("Chapter 4 – Dawn", [
            ("CoP 4-1 – Sheltering Doubt", "Chapter 4 – Dawn"),
            ("CoP 4-2 – The Savage", "Chapter 4 – Dawn"),
            ("CoP 4-3 – The Secrets of Worship", "Chapter 4 – Dawn"),
            ("CoP 4-4 – Flames for the Dead", "Chapter 4 – Dawn"),
            ("CoP 4-5 – The Warrior's Path", "Chapter 4 – Dawn"),
            ("CoP 4-6 – Garden of Antiquity (Chapter transition)", "Chapter 4 – Dawn"),
        ]),
        ("Chapter 5 – The Return Home to Jeuno", [
            ("CoP 5-1 – Desires of Emptiness", "Chapter 5 – The Return Home to Jeuno"),
            ("CoP 5-2 – Three Paths", "Chapter 5 – The Return Home to Jeuno"),
            ("Louverance's Path", "Chapter 5 – The Return Home to Jeuno"),
            ("Ulmia's Path", "Chapter 5 – The Return Home to Jeuno"),
            ("Tenzen's Path", "Chapter 5 – The Return Home to Jeuno"),
        ]),
        ("Chapter 6 – Eternal Transgression", [
            ("CoP 6-1 – For Whom the Verse Is Sung", "Chapter 6 – Eternal Transgression"),
            ("CoP 6-2 – A Place to Return", "Chapter 6 – Eternal Transgression"),
            ("CoP 6-3 – More Questions Than Answers", "Chapter 6 – Eternal Transgression"),
        ]),
        ("Chapter 7 – The Destiny Destroyers", [
            ("CoP 7-1 – One to Be Feared", "Chapter 7 – The Destiny Destroyers"),
            ("CoP 7-2 – Chains and Bonds", "Chapter 7 – The Destiny Destroyers"),
            ("CoP 7-3 – Flames in the Darkness", "Chapter 7 – The Destiny Destroyers"),
        ]),
        ("Chapter 8 – Emptiness Bleeds", [
            ("CoP 8-1 – Garden of Antiquity", "Chapter 8 – Emptiness Bleeds"),
            ("CoP 8-2 – A Fate Decided", "Chapter 8 – Emptiness Bleeds"),
            ("CoP 8-3 – When Angels Fall", "Chapter 8 – Emptiness Bleeds"),
            ("CoP 8-4 – Dawn", "Chapter 8 – Emptiness Bleeds"),
            ("CoP 8-5 – The Last Verse (shared ZM/CoP epilogue)", "Chapter 8 – Emptiness Bleeds"),
            ("Complete", "Complete"),
        ]),
    ],
}

CITY_MISSIONS = {
    "SANDORIA": (
        ("1-1", "Smash the Orcish Scouts"), ("1-2", "Bat Hunt"), ("1-3", "Save the Children"),
        ("2-1", "The Rescue Drill"), ("2-2", "The Davoi Report"), ("2-3", "Journey Abroad"),
        ("3-1", "Infiltrate Davoi"), ("3-2", "The Crystal Spring"), ("3-3", "Appointment to Jeuno"),
        ("4-1", "Magicite"), ("5-1", "The Ruins of Fei'Yin"), ("5-2", "The Shadow Lord"),
        ("6-1", "Leaute's Last Wishes"), ("6-2", "Ranperre's Final Rest"),
        ("7-1", "Prestige of the Papsque"), ("7-2", "Secret Weapon"),
        ("8-1", "Coming of Age"), ("8-2", "Lightbringer"),
        ("9-1", "Breaking Barriers"), ("9-2", "The Heir to the Light"),
    ),
    "BASTOK": (
        ("1-1", "The Zeruhn Report"), ("1-2", "A Geological Survey"), ("1-3", "Fetichism"),
        ("2-1", "The Crystal Line"), ("2-2", "Wading Beasts"), ("2-3", "The Emissary"),
        ("3-1", "The Four Musketeers"), ("3-2", "To the Forsaken Mines"), ("3-3", "Jeuno"),
        ("4-1", "Magicite"), ("5-1", "Darkness Rising"), ("5-2", "Xarcabard, Land of Truths"),
        ("6-1", "Return of the Talekeeper"), ("6-2", "The Pirates' Cove"),
        ("7-1", "The Final Image"), ("7-2", "On My Way"),
        ("8-1", "The Chains That Bind Us"), ("8-2", "Enter the Talekeeper"),
        ("9-1", "The Salt of the Earth"), ("9-2", "Where Two Paths Converge"),
    ),
    "WINDURST": (
        ("1-1", "The Horutoto Ruins Experiment"), ("1-2", "The Heart of the Matter"), ("1-3", "The Price of Peace"),
        ("2-1", "Lost for Words"), ("2-2", "A Testing Time"), ("2-3", "The Three Kingdoms"),
        ("3-1", "To Each His Own Right"), ("3-2", "Written in the Stars"), ("3-3", "A New Journey"),
        ("4-1", "Magicite"), ("5-1", "The Final Seal"), ("5-2", "The Shadow Awaits"),
        ("6-1", "Full Moon Fountain"), ("6-2", "Saintly Invitation"),
        ("7-1", "The Sixth Ministry"), ("7-2", "Awakening of the Gods"),
        ("8-1", "Vain"), ("8-2", "The Jester Who'd Be King"),
        ("9-1", "Doll of the Dead"), ("9-2", "Moon Reading"),
    ),
}
for campaign, missions in CITY_MISSIONS.items():
    city_name = {"SANDORIA": "San d'Oria", "BASTOK": "Bastok", "WINDURST": "Windurst"}[campaign]
    MISSION_OPTIONS[campaign] = [
        (f"Rank {rank}", [(f"{city_name} {number} – {title}", f"Rank {rank}")
                          for number, title in missions if number.startswith(f"{rank}-")])
        for rank in range(1, 10)
    ] + [("Rank 10", [("Complete", "Complete")])]

TOAU_TITLES = (
    "Land of Sacred Serpents", "Immortal Sentries", "President Salaheem", "Knight of Gold",
    "Confessions of Royalty", "Easterly Winds", "Westerly Winds", "A Mercenary Life",
    "Undersea Scouting", "Astral Waves", "Imperial Schemes", "Royal Puppeteer",
    "Lost Kingdom", "The Dolphin Crest", "The Black Coffin", "Ghosts of the Past",
    "Guests of the Empire", "Passing Glory", "Sweets for the Soul", "Teahouse Tumult",
    "Finders Keepers", "Shield of Diplomacy", "Social Graces", "Foiled Ambition",
    "Playing the Part", "Seal of the Serpent", "Misplaced Nobility", "Bastion of Knowledge",
    "Puppet in Peril", "Prevalence of Pirates", "Shades of Vengeance", "In the Blood",
    "Sentinels' Honor", "Testing the Waters", "Legacy of the Lost", "Gaze of the Saboteur",
    "Path of Darkness", "Fangs of the Lion", "Nashmeira's Plea", "The Rider Cometh",
    "Unraveling Reason", "Light of Judgment", "Path of Blood", "Stirrings of War",
    "The Final Battle", "The Wyrm God", "Eternal Mercenary", "Imperial Coronation",
)
MISSION_OPTIONS["TOAU"] = [
    ("Treasures of Aht Urhgan", [(f"ToAU {number:02d} – {title}", f"ToAU {number:02d}")
                                  for number, title in enumerate(TOAU_TITLES, 1)] + [("Complete", "Complete")])
]

ZILART_MISSION_MIGRATIONS = {
    "ZM1 – Through the Quicksand Caves": "ZM6 – Through the Quicksand Caves",
    "ZM2 – The Chamber of Oracles": "ZM7 – The Chamber of Oracles",
    "ZM3 – Return to Delkfutt's Tower": "ZM8 – Return to Delkfutt's Tower",
    "ZM4 – Ro'Maeve": "ZM9 – Ro'Maeve",
    "ZM5 – The Temple of Desolation": "ZM10 – The Temple of Desolation",
    "ZM6 – Hall of the Gods": "ZM11 – The Hall of the Gods",
    "ZM7 – The Mithra and the Crystal": "ZM12 – The Mithra and the Crystal",
    "ZM8 – The Gate of the Gods": "ZM13 – The Gate of the Gods",
    "ZM9 – Ark Angels": "ZM14 – Ark Angels",
    "ZM10 – The Sealed Shrine": "ZM15 – The Sealed Shrine",
    "ZM11 – The Celestial Nexus": "ZM16 – The Celestial Nexus",
    "ZM12 – Awakening": "ZM17 – Awakening",
    "ZM13 – The Last Verse (epilogue shared with CoP after Apocalypse Nigh)":
        "ZM18 – The Last Verse (epilogue shared with CoP after Apocalypse Nigh)",
}


def fetch_horizon_player(name):
    """Fetch a public character profile without exposing arbitrary URLs."""
    if not re.fullmatch(r"[A-Za-z]{2,15}", name):
        raise ValueError("Enter a valid HorizonXI character name.")
    req = Request(
        f"{HORIZON_API}/chars/{quote(name)}",
        headers={"Accept": "application/json", "User-Agent": "MissionsLinkshellRoster/1.0"},
    )
    with urlopen(req, timeout=6) as response:
        return json.load(response)


def split_mission(campaign, mission, chapter=""):
    """Return a compact mission number and readable mission title."""
    if mission == "Complete":
        return "Complete", "Campaign complete"
    if " – " in mission:
        number, title = mission.split(" – ", 1)
        return number, title
    if campaign == "COP" and mission.endswith("Path"):
        return "CoP 5-2", mission
    return chapter or campaign, mission


def build_progress_board(campaign, rows):
    by_mission = {}
    for row in rows:
        by_mission.setdefault(row["mission"], []).append(row)

    board = [{
        "number": "—",
        "title": "Not selected",
        "members": by_mission.get("", []),
    }]
    known = set()
    for _group, options in MISSION_OPTIONS[campaign]:
        for mission, chapter in options:
            known.add(mission)
            number, title = split_mission(campaign, mission, chapter)
            board.append({
                "number": number,
                "title": title,
                "members": by_mission.get(mission, []),
            })

    # Preserve older/custom entries rather than hiding their members.
    for mission, members in by_mission.items():
        if mission and mission not in known:
            number, title = split_mission(campaign, mission, members[0]["chapter"])
            board.append({"number": number, "title": title, "members": members})
    return board


def parse_local_datetime(value):
    """Parse an HTML local datetime into the app's consistently stored ISO form."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(second=0, microsecond=0)
    except ValueError:
        return None


def eastern_today():
    return datetime.now(EASTERN_TIME).date()


def request_occurs_on(help_request, day):
    """Return whether a request appears on a day without materializing occurrences."""
    if help_request["status"] not in ACTIVE_HELP_STATUSES:
        return False
    expires = parse_local_datetime(help_request["expires_at"])
    if expires and datetime.combine(day, time.max) > expires and day > expires.date():
        return False
    start = parse_local_datetime(help_request["start_at"])
    end = parse_local_datetime(help_request["end_at"])
    mode = help_request["availability_mode"]
    today = eastern_today()
    if mode == "now":
        return day == today
    if mode == "fixed":
        return bool(start and day == start.date())
    if mode == "range":
        return bool(start and end and start.date() <= day <= end.date())
    first_day = start.date() if start else today
    if mode == "after" and day > today + timedelta(days=6):
        return False
    return first_day <= day and (not expires or day <= expires.date())


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        DATABASE=os.path.join(app.instance_path, "missions.db"),
        EDIT_PASSWORD=os.environ.get("EDIT_PASSWORD", "Hokuten"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "Idonthave1"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def is_editor():
        return bool(app.config.get("AUTH_DISABLED") or session.get("is_editor") or session.get("is_admin"))

    def is_admin():
        return bool(session.get("is_admin") or (
            app.config.get("AUTH_DISABLED") and current_member_id() is None
        ))

    def current_member_id():
        value = session.get("member_id")
        return int(value) if value is not None else None

    def editor_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not is_editor():
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not is_admin():
                abort(403, description="Administrator access is required.")
            return view(*args, **kwargs)
        return wrapped

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals.update(
        csrf_token=csrf_token, is_editor=is_editor, is_admin=is_admin,
        current_member_id=current_member_id,
    )

    @app.before_request
    def protect_posts():
        if request.method == "POST" and not app.config.get("AUTH_DISABLED"):
            supplied = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not expected or not hmac.compare_digest(supplied, expected):
                abort(400, description="Invalid or expired form token. Go back, refresh, and try again.")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            configured = app.config.get("EDIT_PASSWORD", "")
            admin_password = app.config.get("ADMIN_PASSWORD", "")
            supplied = request.form.get("password", "")
            admin_login = bool(admin_password and hmac.compare_digest(supplied, admin_password))
            member_login = bool(
                hmac.compare_digest(supplied, "Hokuten")
                or (configured and hmac.compare_digest(supplied, configured))
            )
            if admin_login or member_login:
                session.clear()
                session["is_admin"] = admin_login
                session["is_editor"] = member_login
                member_id = request.form.get("member_id", "")
                if member_login and request.form.get("action") == "add_player":
                    name = request.form.get("new_member_name", "").strip()
                    if not re.fullmatch(r"[A-Za-z]{2,15}", name):
                        flash("Enter a valid HorizonXI character name (2–15 letters).", "error")
                        session.clear()
                        return redirect(url_for("login", next=request.form.get("next", "")))
                    db = get_db()
                    existing = db.execute("SELECT id, name FROM members WHERE name=?", (name,)).fetchone()
                    if existing:
                        session["member_id"] = existing["id"]
                        name = existing["name"]
                    else:
                        cursor = db.execute("INSERT INTO members(name) VALUES (?)", (name,))
                        db.commit()
                        session["member_id"] = cursor.lastrowid
                    flash(f"Added and signed in as {name}.", "success")
                elif member_login and member_id.isdigit():
                    session["member_id"] = int(member_id)
                elif member_login and request.form.get("action") == "sign_in":
                    session.clear()
                    flash("Choose your character or add a new player.", "error")
                    return redirect(url_for("login", next=request.form.get("next", "")))
                csrf_token()
                destination = request.form.get("next", "")
                if not destination.startswith("/") or destination.startswith("//"):
                    destination = url_for("index")
                return redirect(destination)
            flash("Incorrect linkshell password.", "error")
        members = get_db().execute(
            f"""SELECT id, name FROM members
                ORDER BY CASE name {''.join(f'WHEN ? THEN {index} ' for index in range(len(LOGIN_CHARACTERS)))}
                ELSE {len(LOGIN_CHARACTERS)} END, name COLLATE NOCASE""",
            LOGIN_CHARACTERS,
        ).fetchall()
        return render_template("login.html", next=request.args.get("next", ""), members=members)

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You are signed out.", "success")
        return redirect(url_for("index"))

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.post("/identity")
    @editor_required
    def set_identity():
        member_id = request.form.get("member_id", "")
        member = get_db().execute("SELECT id FROM members WHERE id=?", (member_id,)).fetchone()
        if not member:
            abort(400, description="Choose a valid linkshell character.")
        session["member_id"] = member["id"]
        destination = request.form.get("next", "")
        if not destination.startswith("/") or destination.startswith("//"):
            destination = url_for("help_board")
        return redirect(destination)

    @app.post("/identity/new")
    @editor_required
    def add_identity():
        name = request.form.get("name", "").strip()
        if not re.fullmatch(r"[A-Za-z]{2,15}", name):
            flash("Enter a valid HorizonXI character name (2–15 letters).", "error")
            return redirect(url_for("help_board"))
        db = get_db()
        try:
            cursor = db.execute("INSERT INTO members(name) VALUES (?)", (name,))
            db.commit()
            session["member_id"] = cursor.lastrowid
            flash(f"Added and selected {name}.", "success")
        except sqlite3.IntegrityError:
            db.rollback()
            existing = db.execute("SELECT id, name FROM members WHERE name=?", (name,)).fetchone()
            if existing:
                session["member_id"] = existing["id"]
                flash(f"Selected existing character {existing['name']}.", "success")
            else:
                flash("That character could not be added.", "error")
        return redirect(url_for("help_board"))

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        with app.open_resource("schema.sql") as schema:
            get_db().executescript(schema.read().decode("utf8"))
        progress_sql = get_db().execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='progress'"
        ).fetchone()["sql"]
        if "CHECK(campaign IN" in progress_sql:
            get_db().executescript(
                """ALTER TABLE progress RENAME TO progress_legacy;
                   CREATE TABLE progress (
                       member_id INTEGER NOT NULL,
                       campaign TEXT NOT NULL,
                       chapter TEXT NOT NULL DEFAULT '',
                       mission TEXT NOT NULL DEFAULT '',
                       status TEXT NOT NULL DEFAULT 'Not started'
                           CHECK(status IN ('Not started','In progress','Ready for help','Complete')),
                       details TEXT NOT NULL DEFAULT '',
                       PRIMARY KEY (member_id, campaign),
                       FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
                   );
                   INSERT INTO progress SELECT * FROM progress_legacy;
                   DROP TABLE progress_legacy;"""
            )
        role_columns = {
            row["name"] for row in get_db().execute("PRAGMA table_info(help_request_roles)")
        }
        if "kind" not in role_columns:
            get_db().execute("ALTER TABLE help_request_roles ADD COLUMN kind TEXT NOT NULL DEFAULT 'job'")
        if "quantity" not in role_columns:
            get_db().execute("ALTER TABLE help_request_roles ADD COLUMN quantity INTEGER")
        get_db().executemany(
            "INSERT OR IGNORE INTO members(name) VALUES (?)",
            [(name,) for name in LOGIN_CHARACTERS],
        )
        for old_mission, new_mission in ZILART_MISSION_MIGRATIONS.items():
            get_db().execute(
                "UPDATE progress SET mission=?, chapter=? WHERE campaign='ZILART' AND mission=?",
                (new_mission, new_mission.split(" – ", 1)[0], old_mission),
            )
        for campaign in CAMPAIGNS:
            get_db().execute(
                """INSERT OR IGNORE INTO progress(member_id,campaign)
                   SELECT m.id, ? FROM members m
                   WHERE EXISTS(SELECT 1 FROM member_jobs j WHERE j.member_id=m.id)""",
                (campaign,),
            )
        get_db().commit()

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Initialized the database.")

    def member_rows(campaign="", mission="", job="", status=""):
        db = get_db()
        clauses, params = [], []
        if campaign:
            clauses.append("p.campaign = ?")
            params.append(campaign)
        if mission:
            clauses.append("p.mission LIKE ?")
            params.append(f"%{mission}%")
        if status:
            clauses.append("p.status = ?")
            params.append(status)
        if job:
            clauses.append("EXISTS (SELECT 1 FROM member_jobs j2 WHERE j2.member_id=m.id AND j2.job=?)")
            params.append(job)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        rows = db.execute(
            f"""
            SELECT m.*, p.campaign, p.chapter, p.mission, p.status, p.details,
                   GROUP_CONCAT(j.job || ' ' || j.level, ', ') AS jobs
            FROM members m
            JOIN progress p ON p.member_id = m.id
            LEFT JOIN member_jobs j ON j.member_id = m.id
            {where}
            GROUP BY m.id, p.campaign
            ORDER BY CASE p.status WHEN 'Ready for help' THEN 0 WHEN 'In progress' THEN 1
                     WHEN 'Not started' THEN 2 ELSE 3 END, p.mission, m.name
            """,
            params,
        ).fetchall()
        return rows

    @app.route("/")
    def index():
        filters = {
            "campaign": request.args.get("campaign", "").upper(),
            "mission": request.args.get("mission", "").strip(),
            "job": request.args.get("job", "").upper(),
            "status": request.args.get("status", ""),
        }
        rows = member_rows(**filters)
        boards = {
            campaign: build_progress_board(
                campaign, [row for row in rows if row["campaign"] == campaign]
            )
            for campaign in CAMPAIGNS
        }
        db = get_db()
        basic_counts = db.execute(
            """SELECT (SELECT COUNT(*) FROM members) members,
                      SUM(status='Ready for help') ready,
                      COUNT(DISTINCT CASE WHEN campaign='COP' AND mission='Complete' THEN member_id END) cop_complete,
                      COUNT(DISTINCT CASE WHEN campaign='ZILART' AND mission='Complete' THEN member_id END) zilart_complete
               FROM progress"""
        ).fetchone()
        cop_order = [
            mission
            for _group, options in MISSION_OPTIONS["COP"]
            for mission, _chapter in options
        ]
        dreamlands_threshold = cop_order.index("CoP 3-5 – Darkness Named")
        dreamlands_members = {
            progress["member_id"]
            for progress in db.execute(
                "SELECT member_id, mission FROM progress WHERE campaign='COP'"
            ).fetchall()
            if progress["mission"] in cop_order
            and cop_order.index(progress["mission"]) > dreamlands_threshold
        }
        counts = dict(basic_counts)
        counts["dreamlands"] = len(dreamlands_members)
        return render_template(
            "index.html", rows=rows, counts=counts, filters=filters,
            jobs=JOBS, campaigns=CAMPAIGNS, statuses=STATUSES, boards=boards,
            campaign_names=CAMPAIGN_NAMES,
        )

    @app.route("/members/new", methods=("GET", "POST"))
    @app.route("/members/<int:member_id>/edit", methods=("GET", "POST"))
    @editor_required
    def member_form(member_id=None):
        db = get_db()
        if member_id is None and current_member_id() is not None and not is_admin():
            member_id = current_member_id()
        if member_id is not None and not is_admin() and current_member_id() != member_id:
            abort(403, description="You may only update your own mission progress.")
        member = db.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone() if member_id else None
        if member_id and member is None:
            return ("Member not found", 404)
        existing_jobs = {
            row["job"]: row["level"]
            for row in db.execute("SELECT * FROM member_jobs WHERE member_id=?", (member_id,)).fetchall()
        } if member_id else {}
        existing_progress = {
            row["campaign"]: row
            for row in db.execute("SELECT * FROM progress WHERE member_id=?", (member_id,)).fetchall()
        } if member_id else {}

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            selected_jobs = {}
            for job in JOBS:
                raw = request.form.get(f"job_{job}", "").strip()
                if raw:
                    try:
                        level = int(raw)
                    except ValueError:
                        level = 0
                    if not 1 <= level <= 75:
                        flash(f"{job} level must be from 1 to 75.", "error")
                        break
                    selected_jobs[job] = level
            else:
                if not name:
                    flash("Character name is required.", "error")
                elif not selected_jobs:
                    flash("Add at least one job and level.", "error")
                else:
                    try:
                        target_member_id = member_id
                        if target_member_id is None:
                            existing_member = db.execute(
                                "SELECT id FROM members WHERE name=?", (name,)
                            ).fetchone()
                            if existing_member:
                                target_member_id = existing_member["id"]

                        if not is_admin():
                            own_member_id = current_member_id()
                            if own_member_id is not None and target_member_id not in (None, own_member_id):
                                abort(403, description="You may only update your own mission progress.")
                            if own_member_id is None and target_member_id is not None:
                                abort(403, description="Select your character before updating progress.")

                        if target_member_id:
                            db.execute(
                                """UPDATE members SET name=?, discord_name=?, timezone=?, availability=?,
                                   notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                                (name, request.form.get("discord_name", "").strip(),
                                 request.form.get("timezone", "").strip(),
                                 request.form.get("availability", "").strip(),
                                 request.form.get("notes", "").strip(), target_member_id),
                            )
                        else:
                            cursor = db.execute(
                                """INSERT INTO members (name, discord_name, timezone, availability, notes)
                                   VALUES (?, ?, ?, ?, ?)""",
                                (name, request.form.get("discord_name", "").strip(),
                                 request.form.get("timezone", "").strip(),
                                 request.form.get("availability", "").strip(),
                                 request.form.get("notes", "").strip()),
                            )
                            target_member_id = cursor.lastrowid
                            if not is_admin():
                                session["member_id"] = target_member_id
                        db.execute("DELETE FROM member_jobs WHERE member_id=?", (target_member_id,))
                        db.executemany(
                            "INSERT INTO member_jobs (member_id, job, level) VALUES (?, ?, ?)",
                            [(target_member_id, job, level) for job, level in selected_jobs.items()],
                        )
                        for campaign in CAMPAIGNS:
                            mission_value = request.form.get(f"{campaign}_mission", "").strip()
                            status_value = request.form.get(f"{campaign}_status", "Not started")
                            if mission_value == "Complete":
                                status_value = "Complete"
                            db.execute(
                                """INSERT INTO progress (member_id, campaign, chapter, mission, status, details)
                                   VALUES (?, ?, ?, ?, ?, ?)
                                   ON CONFLICT(member_id, campaign) DO UPDATE SET
                                   chapter=excluded.chapter, mission=excluded.mission,
                                   status=excluded.status, details=excluded.details""",
                                (target_member_id, campaign,
                                 request.form.get(f"{campaign}_chapter", "").strip(),
                                 mission_value,
                                 status_value,
                                 request.form.get(f"{campaign}_details", "").strip()),
                            )
                        db.commit()
                        flash(f"Saved {name}'s mission progress.", "success")
                        return redirect(url_for("index"))
                    except sqlite3.IntegrityError:
                        db.rollback()
                        flash("That character name is already registered.", "error")

        return render_template(
            "member_form.html", member=member, existing_jobs=existing_jobs,
            progress=existing_progress, jobs=JOBS, campaigns=CAMPAIGNS, statuses=STATUSES,
            mission_options=MISSION_OPTIONS, campaign_names=CAMPAIGN_NAMES,
        )

    @app.get("/members")
    @admin_required
    def members_admin():
        members = get_db().execute(
            """SELECT m.*,
                      GROUP_CONCAT(DISTINCT j.job || ' ' || j.level) jobs,
                      GROUP_CONCAT(DISTINCT p.campaign || ': ' ||
                          COALESCE(NULLIF(p.mission, ''), 'Not selected')) progress_summary
               FROM members m
               LEFT JOIN member_jobs j ON j.member_id=m.id
               LEFT JOIN progress p ON p.member_id=m.id
               GROUP BY m.id ORDER BY m.name COLLATE NOCASE"""
        ).fetchall()
        return render_template("members_admin.html", members=members)

    @app.get("/job-roster")
    def job_roster():
        db = get_db()
        members = list(db.execute(
            """SELECT m.id, m.name, m.updated_at FROM members m
               WHERE EXISTS(SELECT 1 FROM member_jobs j WHERE j.member_id=m.id)
               ORDER BY m.name COLLATE NOCASE"""
        ).fetchall())
        levels = {
            member["id"]: {
                row["job"]: row["level"]
                for row in db.execute(
                    "SELECT job, level FROM member_jobs WHERE member_id=?", (member["id"],)
                ).fetchall()
            }
            for member in members
        }
        level_75_counts = {
            job: sum(levels[member["id"]].get(job) == 75 for member in members)
            for job in JOBS
        }
        filter_job = request.args.get("job", "").upper()
        if filter_job not in JOBS:
            filter_job = ""
        try:
            min_level = int(request.args.get("min_level", "1"))
            if not 1 <= min_level <= 75:
                raise ValueError
        except ValueError:
            min_level = 1
        if filter_job:
            members = [
                member for member in members
                if levels[member["id"]].get(filter_job, 0) >= min_level
            ]
        sort_job = request.args.get("sort", "").upper()
        if sort_job not in JOBS:
            sort_job = filter_job
        direction = "asc" if request.args.get("direction") == "asc" else "desc"
        if sort_job:
            members.sort(
                key=lambda member: (
                    levels[member["id"]].get(sort_job, 0), member["name"].casefold()
                ),
                reverse=direction == "desc",
            )
        elif request.args.get("sort") == "name" and direction == "desc":
            members.reverse()
        return render_template(
            "job_roster.html", members=members, levels=levels,
            jobs=JOBS, filter_job=filter_job, min_level=min_level,
            sort_job=sort_job, direction=direction, level_75_counts=level_75_counts,
        )

    def require_member_identity():
        member_id = current_member_id()
        if member_id is None and app.config.get("AUTH_DISABLED"):
            raw = request.form.get("requester_id") or request.form.get("member_id")
            member_id = int(raw) if raw and raw.isdigit() else None
        if member_id is None:
            abort(403, description="Select your linkshell character before continuing.")
        member = get_db().execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
        if not member:
            abort(403, description="Your selected character no longer exists.")
        return member

    def member_jobs(member_id):
        return {
            row["job"]: row["level"]
            for row in get_db().execute(
                "SELECT job, level FROM member_jobs WHERE member_id=? ORDER BY job", (member_id,)
            ).fetchall()
        }

    def help_request_or_404(request_id):
        row = get_db().execute(
            """SELECT h.*, m.name requester_name, m.discord_name
               FROM help_requests h JOIN members m ON m.id=h.requester_id WHERE h.id=?""",
            (request_id,),
        ).fetchone()
        if not row:
            abort(404)
        return row

    def can_manage(help_request):
        return bool(is_admin() or (
            is_editor() and current_member_id() == help_request["requester_id"]
        ))

    def expire_requests():
        now = datetime.now().isoformat(timespec="minutes")
        get_db().execute(
            """UPDATE help_requests SET status='Expired', updated_at=CURRENT_TIMESTAMP
               WHERE status IN ('Open','Forming','Full') AND expires_at IS NOT NULL AND expires_at < ?""",
            (now,),
        )
        get_db().commit()

    def validate_help_form(form):
        values = {key: form.get(key, "").strip() for key in (
            "title", "category", "zone", "description", "availability_mode",
            "start_at", "available_after", "end_at", "expires_at", "requirements", "notes",
        )}
        errors = []
        if not values["title"]:
            errors.append("Request title is required.")
        if values["category"] not in HELP_CATEGORIES:
            errors.append("Choose a valid category.")
        elif values["category"] in HELP_ZONES:
            valid_zones = {
                zone for zones in HELP_ZONES[values["category"]].values() for zone in zones
            }
            if values["zone"] not in valid_zones:
                errors.append("Choose a valid region and zone for this activity.")
        if values["availability_mode"] not in AVAILABILITY_MODES:
            errors.append("Choose a valid availability mode.")
        try:
            values["helpers_needed"] = int(form.get("helpers_needed", "1"))
            if not 1 <= values["helpers_needed"] <= 17:
                raise ValueError
        except ValueError:
            errors.append("Helpers needed must be from 1 to 17.")
            values["helpers_needed"] = 1
        raw_cap = form.get("level_cap", "").strip()
        try:
            values["level_cap"] = int(raw_cap) if raw_cap else None
            if values["level_cap"] is not None and not 1 <= values["level_cap"] <= 75:
                raise ValueError
        except ValueError:
            errors.append("Level cap must be from 1 to 75 or uncapped.")
            values["level_cap"] = None
        parsed = {key: parse_local_datetime(values[key]) for key in ("start_at", "end_at", "expires_at")}
        if values["availability_mode"] == "after" and not values["available_after"]:
            errors.append("Enter the time you are available after.")
        if values["availability_mode"] == "fixed" and not parsed["start_at"]:
            errors.append("Fixed requests require a start date and time.")
        if parsed["expires_at"] and parsed["expires_at"] <= datetime.now():
            errors.append("Expiration must be in the future.")
        return values, errors

    def requested_party(form):
        specs, errors = [], []
        for kind, field, allowed in (
            ("job", "requested_jobs", JOBS), ("role", "requested_party_roles", PARTY_ROLES),
        ):
            for name in set(form.getlist(field)):
                if name not in allowed:
                    errors.append("Choose only valid requested jobs or party roles.")
                    continue
                raw = form.get(f"requested_count_{kind}_{name}", "").strip()
                try:
                    quantity = int(raw) if raw else None
                    if quantity is not None and not 1 <= quantity <= 5:
                        raise ValueError
                except ValueError:
                    errors.append(f"Requested {name} count must be Any or from 1 to 5.")
                    continue
                specs.append((name, kind, quantity))
        return specs, errors

    @app.get("/help-requests")
    def help_board():
        expire_requests()
        db = get_db()
        filters = {key: request.args.get(key, "").strip() for key in (
            "q", "category", "level_cap", "status", "availability", "sort",
        )}
        clauses, params = [], []
        if filters["q"]:
            term = f"%{filters['q']}%"
            clauses.append("(h.title LIKE ? OR h.zone LIKE ? OR h.description LIKE ? OR m.name LIKE ?)")
            params.extend([term] * 4)
        if filters["category"].startswith("section:"):
            section = filters["category"].removeprefix("section:")
            activities = HELP_SECTIONS.get(section)
            if activities:
                placeholders = ",".join("?" for _ in activities)
                clauses.append(f"h.category IN ({placeholders})")
                params.extend(activities)
        elif filters["category"] in HELP_CATEGORIES:
            clauses.append("h.category=?"); params.append(filters["category"])
        if filters["level_cap"] == "uncapped":
            clauses.append("h.level_cap IS NULL")
        elif filters["level_cap"].isdigit():
            clauses.append("h.level_cap=?"); params.append(int(filters["level_cap"]))
        if filters["status"] in HELP_STATUSES:
            clauses.append("h.status=?"); params.append(filters["status"])
        else:
            clauses.append("h.status IN ('Open','Forming','Full')")
        if filters["availability"] in AVAILABILITY_MODES:
            clauses.append("h.availability_mode=?"); params.append(filters["availability"])
        order = {
            "recent": "h.created_at DESC", "now": "CASE WHEN h.availability_mode='now' THEN 0 ELSE 1 END, h.created_at DESC",
            "requester": "m.name COLLATE NOCASE", "soonest": "COALESCE(h.start_at, h.created_at)",
        }.get(filters["sort"], "COALESCE(h.start_at, h.created_at)")
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        rows = db.execute(
            f"""SELECT h.*, m.name requester_name,
                GROUP_CONCAT(j.job || ':' || j.level) requester_jobs
                FROM help_requests h JOIN members m ON m.id=h.requester_id
                LEFT JOIN member_jobs j ON j.member_id=m.id {where}
                GROUP BY h.id ORDER BY {order}, h.id""", params,
        ).fetchall()
        requests_data = []
        for row in rows:
            item = dict(row)
            selected_requester_jobs = {
                selected["job"] for selected in db.execute(
                    "SELECT job FROM help_request_jobs WHERE request_id=?", (item["id"],)
                ).fetchall()
            }
            jobs = []
            for pair in (item.pop("requester_jobs") or "").split(","):
                if pair:
                    job, level = pair.split(":")
                    eligible = item["level_cap"] is None or int(level) >= item["level_cap"]
                    if job in selected_requester_jobs and eligible:
                        jobs.append((job, int(level), True))
            item["jobs"] = jobs
            item["requested_party"] = [
                dict(spec) for spec in db.execute(
                    """SELECT role, kind, quantity FROM help_request_roles
                       WHERE request_id=? ORDER BY kind, role""", (item["id"],)
                ).fetchall()
            ]
            requests_data.append(item)
        try:
            year, month = map(int, request.args.get("month", "").split("-"))
            if not 1 <= month <= 12: raise ValueError
        except (ValueError, TypeError):
            year, month = date.today().year, date.today().month
        first = date(year, month, 1)
        cells = list(calendar.Calendar(firstweekday=6).itermonthdates(year, month))
        active = [item for item in requests_data if item["status"] in ACTIVE_HELP_STATUSES]
        calendar_days = [(day, [item for item in active if request_occurs_on(item, day)]) for day in cells]
        previous = first - timedelta(days=1)
        following = (date(year + (month == 12), 1 if month == 12 else month + 1, 1))
        members = db.execute(
            f"""SELECT id, name FROM members
                ORDER BY CASE name {''.join(f'WHEN ? THEN {index} ' for index in range(len(LOGIN_CHARACTERS)))}
                ELSE {len(LOGIN_CHARACTERS)} END, name COLLATE NOCASE""",
            LOGIN_CHARACTERS,
        ).fetchall()
        current_member = db.execute(
            "SELECT id, name FROM members WHERE id=?", (current_member_id(),)
        ).fetchone() if current_member_id() else None
        counts = db.execute("""SELECT COUNT(*) active,
            SUM(availability_mode='now') going_now,
            SUM(start_at BETWEEN datetime('now') AND datetime('now','+7 days')) scheduled
            FROM help_requests WHERE status IN ('Open','Forming','Full')""").fetchone()
        return render_template(
            "help_board.html", help_requests=requests_data, calendar_days=calendar_days,
            month_name=first.strftime("%B %Y"), month_key=first.strftime("%Y-%m"),
            previous_month=previous.strftime("%Y-%m"), next_month=following.strftime("%Y-%m"),
            categories=HELP_CATEGORIES, help_sections=HELP_SECTIONS, help_statuses=HELP_STATUSES,
            availability_modes=AVAILABILITY_MODES, filters=filters, counts=counts,
            members=members, current_member=current_member,
        )

    @app.route("/help-requests/new", methods=("GET", "POST"))
    @editor_required
    def create_help_request():
        member = require_member_identity()
        jobs = member_jobs(member["id"])
        if request.method == "POST":
            values, errors = validate_help_form(request.form)
            party_specs, party_errors = requested_party(request.form)
            errors.extend(party_errors)
            selected_jobs = {job for job in request.form.getlist("requester_jobs") if job in jobs}
            eligible = {job for job, level in jobs.items() if values["level_cap"] is None or level >= values["level_cap"]}
            if not selected_jobs:
                errors.append("Choose at least one job you are willing to bring.")
            elif not selected_jobs <= eligible:
                errors.append("Selected requester jobs must meet the level cap.")
            if not errors:
                db = get_db()
                cursor = db.execute(
                    """INSERT INTO help_requests
                    (requester_id,title,category,zone,description,level_cap,helpers_needed,
                     availability_mode,start_at,available_after,end_at,expires_at,requirements,notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (member["id"], values["title"], values["category"], values["zone"],
                     values["description"], values["level_cap"], values["helpers_needed"],
                     values["availability_mode"], values["start_at"] or None,
                     values["available_after"] or None, values["end_at"] or None,
                     values["expires_at"] or None, values["requirements"], values["notes"]),
                )
                request_id = cursor.lastrowid
                db.executemany("INSERT INTO help_request_jobs VALUES (?,?)", [(request_id, job) for job in selected_jobs])
                db.executemany(
                    "INSERT INTO help_request_roles(request_id,role,kind,quantity) VALUES (?,?,?,?)",
                    [(request_id, name, kind, quantity) for name, kind, quantity in party_specs],
                )
                db.commit()
                flash("Help request published.", "success")
                return redirect(url_for("help_request_detail", request_id=request_id))
            for error in errors: flash(error, "error")
        return render_template("help_request_form.html", help_request=None, member=member, member_jobs=jobs,
                               categories=HELP_CATEGORIES, help_sections=HELP_SECTIONS,
                               availability_modes=AVAILABILITY_MODES, help_zones=HELP_ZONES, all_jobs=JOBS,
                               party_roles=PARTY_ROLES, requested_specs={},
                               selected_jobs=set())

    @app.route("/help-requests/<int:request_id>/edit", methods=("GET", "POST"))
    @editor_required
    def edit_help_request(request_id):
        item = help_request_or_404(request_id)
        if not can_manage(item): abort(403)
        member = get_db().execute("SELECT * FROM members WHERE id=?", (item["requester_id"],)).fetchone()
        jobs = member_jobs(member["id"])
        selected_jobs = {r["job"] for r in get_db().execute("SELECT job FROM help_request_jobs WHERE request_id=?", (request_id,))}
        if request.method == "POST":
            values, errors = validate_help_form(request.form)
            party_specs, party_errors = requested_party(request.form)
            errors.extend(party_errors)
            submitted_jobs = {job for job in request.form.getlist("requester_jobs") if job in jobs}
            eligible = {job for job, level in jobs.items() if values["level_cap"] is None or level >= values["level_cap"]}
            if not submitted_jobs: errors.append("Choose at least one job you are willing to bring.")
            elif not submitted_jobs <= eligible: errors.append("Selected requester jobs must meet the level cap.")
            if not errors:
                db = get_db()
                db.execute("""UPDATE help_requests SET title=?,category=?,zone=?,description=?,level_cap=?,
                    helpers_needed=?,availability_mode=?,start_at=?,available_after=?,end_at=?,expires_at=?,
                    requirements=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (values["title"],values["category"],values["zone"],values["description"],values["level_cap"],
                     values["helpers_needed"],values["availability_mode"],values["start_at"] or None,
                     values["available_after"] or None,values["end_at"] or None,values["expires_at"] or None,
                     values["requirements"],values["notes"],request_id))
                db.execute("DELETE FROM help_request_jobs WHERE request_id=?", (request_id,))
                db.executemany("INSERT INTO help_request_jobs VALUES (?,?)", [(request_id, job) for job in submitted_jobs])
                db.execute("DELETE FROM help_request_roles WHERE request_id=?", (request_id,))
                db.executemany(
                    "INSERT INTO help_request_roles(request_id,role,kind,quantity) VALUES (?,?,?,?)",
                    [(request_id, name, kind, quantity) for name, kind, quantity in party_specs],
                )
                reactivated = item["status"] == "Cancelled" and request.form.get("reactivate") == "1"
                if reactivated:
                    db.execute(
                        "UPDATE help_requests SET status='Open',updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (request_id,),
                    )
                db.commit(); flash("Help request updated.", "success")
                if reactivated:
                    flash("The cancelled request was reactivated and is open again.", "success")
                return redirect(url_for("help_request_detail", request_id=request_id))
            selected_jobs = submitted_jobs
            for error in errors: flash(error, "error")
        requested_specs = {
            (r["kind"], r["role"]): r["quantity"]
            for r in get_db().execute(
                "SELECT role, kind, quantity FROM help_request_roles WHERE request_id=?", (request_id,)
            )
        }
        return render_template("help_request_form.html", help_request=item, member=member, member_jobs=jobs,
                               categories=HELP_CATEGORIES, help_sections=HELP_SECTIONS,
                               availability_modes=AVAILABILITY_MODES, help_zones=HELP_ZONES, all_jobs=JOBS,
                               party_roles=PARTY_ROLES, selected_jobs=selected_jobs,
                               requested_specs=requested_specs)

    @app.get("/help-requests/<int:request_id>")
    def help_request_detail(request_id):
        expire_requests()
        item = help_request_or_404(request_id)
        db = get_db()
        requester_jobs = member_jobs(item["requester_id"])
        chosen = {r["job"] for r in db.execute("SELECT job FROM help_request_jobs WHERE request_id=?", (request_id,))}
        roles = db.execute(
            "SELECT role, kind, quantity FROM help_request_roles WHERE request_id=? ORDER BY kind, role",
            (request_id,),
        ).fetchall()
        volunteers = db.execute(
            """SELECT v.*, m.name, GROUP_CONCAT(j.job) jobs FROM help_volunteers v
               JOIN members m ON m.id=v.member_id LEFT JOIN help_volunteer_jobs j ON j.volunteer_id=v.id
               WHERE v.request_id=? GROUP BY v.id ORDER BY v.selected DESC, v.created_at""", (request_id,)
        ).fetchall()
        viewer_jobs = member_jobs(current_member_id()) if current_member_id() else {}
        eligible_viewer_jobs = {job: level for job, level in viewer_jobs.items() if item["level_cap"] is None or level >= item["level_cap"]}
        return render_template("help_request_detail.html", help_request=item, requester_jobs=requester_jobs,
                               selected_jobs=chosen, roles=roles, volunteers=volunteers,
                               viewer_jobs=eligible_viewer_jobs, can_manage=can_manage(item),
                               help_statuses=HELP_STATUSES, transitions=HELP_STATUS_TRANSITIONS.get(item["status"], set()),
                               availability_modes=AVAILABILITY_MODES)

    @app.post("/help-requests/<int:request_id>/volunteer")
    @editor_required
    def volunteer(request_id):
        member = require_member_identity(); item = help_request_or_404(request_id)
        if item["status"] not in ACTIVE_HELP_STATUSES or member["id"] == item["requester_id"]:
            abort(400)
        jobs = member_jobs(member["id"])
        eligible = {job for job, level in jobs.items() if item["level_cap"] is None or level >= item["level_cap"]}
        selected = {job for job in request.form.getlist("jobs") if job in eligible}
        if not selected:
            flash("Choose at least one eligible job.", "error")
            return redirect(url_for("help_request_detail", request_id=request_id))
        db = get_db()
        db.execute("""INSERT INTO help_volunteers(request_id,member_id,note) VALUES(?,?,?)
            ON CONFLICT(request_id,member_id) DO UPDATE SET note=excluded.note,updated_at=CURRENT_TIMESTAMP""",
                   (request_id, member["id"], request.form.get("note", "").strip()))
        response = db.execute("SELECT id FROM help_volunteers WHERE request_id=? AND member_id=?", (request_id, member["id"])).fetchone()
        db.execute("DELETE FROM help_volunteer_jobs WHERE volunteer_id=?", (response["id"],))
        db.executemany("INSERT INTO help_volunteer_jobs VALUES (?,?)", [(response["id"], job) for job in selected])
        db.commit(); flash("Your volunteer response was saved.", "success")
        return redirect(url_for("help_request_detail", request_id=request_id))

    @app.post("/help-requests/<int:request_id>/withdraw")
    @editor_required
    def withdraw_volunteer(request_id):
        member = require_member_identity()
        get_db().execute("DELETE FROM help_volunteers WHERE request_id=? AND member_id=?", (request_id, member["id"]))
        get_db().commit(); flash("You withdrew from this request.", "success")
        return redirect(url_for("help_request_detail", request_id=request_id))

    @app.post("/help-requests/<int:request_id>/status")
    @editor_required
    def change_help_status(request_id):
        item = help_request_or_404(request_id)
        if not can_manage(item): abort(403)
        new_status = request.form.get("status", "")
        if new_status not in HELP_STATUS_TRANSITIONS.get(item["status"], set()): abort(400)
        get_db().execute("UPDATE help_requests SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_status, request_id))
        get_db().commit(); flash(f"Request marked {new_status.lower()}.", "success")
        return redirect(url_for("help_request_detail", request_id=request_id))

    @app.post("/help-requests/<int:request_id>/delete")
    @admin_required
    def delete_help_request(request_id):
        item = help_request_or_404(request_id)
        get_db().execute("DELETE FROM help_requests WHERE id=?", (request_id,))
        get_db().commit()
        flash(f"Removed help request “{item['title']}”.", "success")
        return redirect(url_for("help_board"))

    @app.post("/help-requests/<int:request_id>/volunteers/<int:volunteer_id>/select")
    @editor_required
    def select_volunteer(request_id, volunteer_id):
        item = help_request_or_404(request_id)
        if not can_manage(item): abort(403)
        selected = 1 if request.form.get("selected") == "1" else 0
        get_db().execute("UPDATE help_volunteers SET selected=? WHERE id=? AND request_id=?", (selected, volunteer_id, request_id))
        get_db().commit()
        return redirect(url_for("help_request_detail", request_id=request_id))

    @app.get("/my-help-requests")
    @editor_required
    def my_help_requests():
        member = require_member_identity()
        rows = get_db().execute("""SELECT DISTINCT h.*, m.name requester_name,
            EXISTS(SELECT 1 FROM help_volunteers v WHERE v.request_id=h.id AND v.member_id=?) volunteered
            FROM help_requests h JOIN members m ON m.id=h.requester_id
            WHERE h.requester_id=? OR volunteered=1 ORDER BY h.created_at DESC""", (member["id"], member["id"])).fetchall()
        return render_template("my_help_requests.html", help_requests=rows, member=member)

    @app.get("/api/horizon-player/<name>")
    def horizon_player(name):
        try:
            player = fetch_horizon_player(name)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        except HTTPError as error:
            if error.code == 404:
                return jsonify(error="Character not found on HorizonXI."), 404
            return jsonify(error="HorizonXI could not complete the lookup."), 502
        except (URLError, TimeoutError, json.JSONDecodeError):
            return jsonify(error="HorizonXI is temporarily unavailable. You can enter levels manually."), 502

        jobs = {
            job: int(level)
            for job, level in player.get("jobs", {}).items()
            if job in JOBS and isinstance(level, (int, float)) and 1 <= int(level) <= 75
        }
        return jsonify(name=player.get("name", name), jobs=jobs)

    @app.post("/members/<int:member_id>/delete")
    @admin_required
    def delete_member(member_id):
        db = get_db()
        db.execute("DELETE FROM members WHERE id=?", (member_id,))
        db.commit()
        flash("Member removed.", "success")
        return redirect(url_for("index"))

    with app.app_context():
        init_db()
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
