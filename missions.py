import os
import sqlite3
import json
import hmac
import re
import secrets
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from pathlib import Path

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for


JOBS = (
    "WAR", "MNK", "WHM", "BLM", "RDM", "THF", "PLD", "DRK", "BST",
    "BRD", "RNG", "SAM", "NIN", "DRG", "SMN",
)
CAMPAIGNS = ("COP", "ZILART")
STATUSES = ("Not started", "In progress", "Ready for help", "Complete")
HORIZON_API = "https://api.horizonxi.com/api/v1"

MISSION_OPTIONS = {
    "ZILART": [
        ("Rise of the Zilart", [
            ("ZM1 – Through the Quicksand Caves", "ZM1"),
            ("ZM2 – The Chamber of Oracles", "ZM2"),
            ("ZM3 – Return to Delkfutt's Tower", "ZM3"),
            ("ZM4 – Ro'Maeve", "ZM4"),
            ("ZM5 – The Temple of Desolation", "ZM5"),
            ("ZM6 – Hall of the Gods", "ZM6"),
            ("ZM7 – The Mithra and the Crystal", "ZM7"),
            ("ZM8 – The Gate of the Gods", "ZM8"),
            ("ZM9 – Ark Angels", "ZM9"),
            ("ZM10 – The Sealed Shrine", "ZM10"),
            ("ZM11 – The Celestial Nexus", "ZM11"),
            ("ZM12 – Awakening", "ZM12"),
            ("ZM13 – The Last Verse (epilogue shared with CoP after Apocalypse Nigh)", "ZM13"),
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


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        DATABASE=os.path.join(app.instance_path, "missions.db"),
        EDIT_PASSWORD=os.environ.get("EDIT_PASSWORD", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def is_editor():
        return bool(app.config.get("AUTH_DISABLED") or session.get("is_editor"))

    def editor_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not is_editor():
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals.update(csrf_token=csrf_token, is_editor=is_editor)

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
            supplied = request.form.get("password", "")
            if configured and hmac.compare_digest(supplied, configured):
                session.clear()
                session["is_editor"] = True
                csrf_token()
                destination = request.form.get("next", "")
                if not destination.startswith("/") or destination.startswith("//"):
                    destination = url_for("index")
                return redirect(destination)
            flash("Incorrect linkshell password.", "error")
        return render_template("login.html", next=request.args.get("next", ""))

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

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        with app.open_resource("schema.sql") as schema:
            get_db().executescript(schema.read().decode("utf8"))

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
        )

    @app.route("/members/new", methods=("GET", "POST"))
    @app.route("/members/<int:member_id>/edit", methods=("GET", "POST"))
    @editor_required
    def member_form(member_id=None):
        db = get_db()
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
            mission_options=MISSION_OPTIONS,
        )

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
    @editor_required
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
