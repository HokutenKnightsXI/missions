"""Refresh complete job levels for roster members from the HorizonXI character API."""

import argparse
import json
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from missions import HORIZON_API, JOBS


def fetch_jobs(name):
    request = Request(
        f"{HORIZON_API}/chars/{quote(name)}",
        headers={"Accept": "application/json", "User-Agent": "MavenJobRosterRefresh/1.0"},
    )
    try:
        with urlopen(request, timeout=12) as response:
            player = json.load(response)
    except HTTPError as error:
        return name, None, f"HTTP {error.code}"
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        return name, None, str(error)
    jobs = {
        job: int(level)
        for job, level in player.get("jobs", {}).items()
        if job in JOBS and isinstance(level, (int, float)) and 1 <= int(level) <= 75
    }
    return name, jobs, None if jobs else "No job data returned"


def roster_names(database):
    connection = sqlite3.connect(database)
    try:
        return [row[0] for row in connection.execute(
            """SELECT name FROM members
               WHERE EXISTS(SELECT 1 FROM member_jobs j WHERE j.member_id=members.id)
                  OR EXISTS(SELECT 1 FROM progress p WHERE p.member_id=members.id)
               ORDER BY name COLLATE NOCASE"""
        )]
    finally:
        connection.close()


def fetch_roster(names, workers=4):
    results, failures = {}, {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_jobs, name): name for name in names}
        for future in as_completed(futures):
            name, jobs, error = future.result()
            if error:
                failures[name] = error
            else:
                results[name] = jobs
    return results, failures


def update_jobs(database, results):
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        for name, jobs in results.items():
            member = connection.execute("SELECT id FROM members WHERE name=?", (name,)).fetchone()
            if not member:
                continue
            connection.execute("DELETE FROM member_jobs WHERE member_id=?", (member[0],))
            connection.executemany(
                "INSERT INTO member_jobs(member_id,job,level) VALUES (?,?,?)",
                [(member[0], job, level) for job, level in jobs.items()],
            )
            connection.execute(
                "UPDATE members SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (member[0],)
            )
        connection.commit()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="instance/missions.db")
    parser.add_argument("--apply", action="store_true", help="Update the database; otherwise preview only")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    database = Path(args.database).resolve()
    if not database.exists():
        raise SystemExit(f"Database not found: {database}")
    names = roster_names(database)
    print(f"Checking {len(names)} roster characters against HorizonXI...")
    results, failures = fetch_roster(names, max(1, min(args.workers, 8)))
    print(f"Retrieved complete jobs for {len(results)} characters; {len(failures)} unavailable.")
    for name, error in sorted(failures.items()):
        print(f"  {name}: {error}")
    if not args.apply:
        print("Preview only. Re-run with --apply to update successful characters.")
        return
    backup = database.with_name(
        f"{database.stem}-before-horizon-refresh-{datetime.now():%Y%m%d-%H%M%S}{database.suffix}"
    )
    shutil.copy2(database, backup)
    update_jobs(database, results)
    print(f"Updated {len(results)} characters. Backup created at {backup}")


if __name__ == "__main__":
    main()
