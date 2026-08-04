"""Import the public Maven mission roster into a local Missions SQLite database."""

import argparse
import html
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from missions import CAMPAIGNS, JOBS, MISSION_OPTIONS, split_mission


LIVE_ROSTER_URL = "https://maven.pythonanywhere.com/"


def mission_lookup():
    lookup = {}
    for campaign in CAMPAIGNS:
        lookup[(campaign, "—", "Not selected")] = ("", "")
        for _group, options in MISSION_OPTIONS[campaign]:
            for mission, chapter in options:
                number, title = split_mission(campaign, mission, chapter)
                lookup[(campaign, number, title)] = (mission, chapter)
    return lookup


def text_content(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def parse_member_title(value):
    fields = {}
    for part in html.unescape(value).split(" | "):
        key, separator, content = part.partition(": ")
        if separator:
            fields[key] = content
    jobs = {}
    if fields.get("Jobs") and fields["Jobs"] != "None":
        for item in fields["Jobs"].split(", "):
            job, separator, level = item.rpartition(" ")
            if separator and job in JOBS and level.isdigit():
                jobs[job] = int(level)
    return {
        "jobs": jobs,
        "status": fields.get("Status", "Not started"),
        "availability": "" if fields.get("Availability") == "Not provided" else fields.get("Availability", ""),
        "details": "" if fields.get("Extra notes") == "None" else fields.get("Extra notes", ""),
    }


def parse_live_roster(page):
    lookup = mission_lookup()
    members = {}
    section_pattern = re.compile(
        r'<section class="progress-panel (cop|zilart)">(.*?)(?=<section class="progress-panel|</div>\s*</main>)',
        re.DOTALL,
    )
    for campaign_class, section in section_pattern.findall(page):
        campaign = campaign_class.upper()
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", section, re.DOTALL):
            number_match = re.search(r'<td class="mission-number">(.*?)</td>', row, re.DOTALL)
            title_match = re.search(r'<td class="mission-name">(.*?)</td>', row, re.DOTALL)
            if not number_match or not title_match:
                continue
            number, title = text_content(number_match.group(1)), text_content(title_match.group(1))
            mission, chapter = lookup.get((campaign, number, title), (number + " – " + title, number))
            for title_attr, name in re.findall(
                r'<span\s+class="member-pill [^"]+"\s+title="([^"]*)">([^<]+)<span class="member-tooltip">',
                row,
            ):
                name = html.unescape(name).strip()
                parsed = parse_member_title(title_attr)
                member = members.setdefault(name.casefold(), {"name": name, "jobs": {}, "availability": "", "progress": {}})
                member["jobs"].update(parsed["jobs"])
                member["availability"] = parsed["availability"] or member["availability"]
                member["progress"][campaign] = {
                    "mission": mission, "chapter": chapter,
                    "status": parsed["status"], "details": parsed["details"],
                }
    return list(members.values())


def fetch_live_roster(url=LIVE_ROSTER_URL):
    request = Request(url, headers={"User-Agent": "MavenMissionRosterImporter/1.0"})
    with urlopen(request, timeout=20) as response:
        return parse_live_roster(response.read().decode("utf-8"))


def merge_roster(database, members):
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        for member in members:
            existing = connection.execute("SELECT id FROM members WHERE name=?", (member["name"],)).fetchone()
            if existing:
                member_id = existing[0]
                connection.execute(
                    "UPDATE members SET availability=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (member["availability"], member_id),
                )
            else:
                member_id = connection.execute(
                    "INSERT INTO members(name,availability) VALUES (?,?)",
                    (member["name"], member["availability"]),
                ).lastrowid
            connection.execute("DELETE FROM member_jobs WHERE member_id=?", (member_id,))
            connection.executemany(
                "INSERT INTO member_jobs(member_id,job,level) VALUES (?,?,?)",
                [(member_id, job, level) for job, level in member["jobs"].items()],
            )
            for campaign, progress in member["progress"].items():
                connection.execute(
                    """INSERT INTO progress(member_id,campaign,chapter,mission,status,details)
                       VALUES (?,?,?,?,?,?) ON CONFLICT(member_id,campaign) DO UPDATE SET
                       chapter=excluded.chapter,mission=excluded.mission,
                       status=excluded.status,details=excluded.details""",
                    (member_id, campaign, progress["chapter"], progress["mission"],
                     progress["status"], progress["details"]),
                )
        connection.commit()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="instance/missions.db")
    parser.add_argument("--apply", action="store_true", help="Merge into the database; otherwise preview only")
    args = parser.parse_args()
    members = fetch_live_roster()
    print(f"Retrieved {len(members)} members from {LIVE_ROSTER_URL}")
    if not args.apply:
        print("Preview only. Re-run with --apply to merge the roster.")
        return
    database = Path(args.database).resolve()
    if not database.exists():
        raise SystemExit(f"Database not found: {database}. Start the app once before importing.")
    backup = database.with_name(f"{database.stem}-before-live-import-{datetime.now():%Y%m%d-%H%M%S}{database.suffix}")
    shutil.copy2(database, backup)
    merge_roster(database, members)
    print(f"Merged {len(members)} members into {database}")
    print(f"Backup created at {backup}")


if __name__ == "__main__":
    main()
