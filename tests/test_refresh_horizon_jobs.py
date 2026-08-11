import json
import sqlite3
from pathlib import Path

from refresh_horizon_jobs import load_snapshot, update_jobs
from github_refresh_horizon_jobs import JOBS as GITHUB_REFRESH_JOBS


def test_github_refresh_includes_all_toau_jobs():
    assert {"BLU", "COR", "PUP"} <= GITHUB_REFRESH_JOBS


def test_github_refresh_targets_current_site():
    workflow = Path(".github/workflows/refresh-job-roster.yml").read_text(encoding="utf-8")
    assert "ROSTER_BASE_URL: https://hokutenknights.com" in workflow
    assert "maven.pythonanywhere.com" not in workflow


def test_offline_snapshot_matches_names_case_insensitively_and_updates_jobs(tmp_path):
    database = tmp_path / "jobs.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """CREATE TABLE members (
               id INTEGER PRIMARY KEY, name TEXT UNIQUE, updated_at TEXT
           );
           CREATE TABLE member_jobs (
               member_id INTEGER, job TEXT, level INTEGER,
               PRIMARY KEY (member_id, job)
           );
           INSERT INTO members(id, name) VALUES (1, 'iMaven');
           INSERT INTO member_jobs VALUES (1, 'WAR', 1);"""
    )
    connection.commit()
    connection.close()
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps({"Imaven": {"PLD": 24, "DRK": 37, "INVALID": 75}}),
        encoding="utf-8",
    )

    results, failures = load_snapshot(snapshot, ["iMaven"])
    assert failures == {}
    assert results == {"iMaven": {"PLD": 24, "DRK": 37}}

    update_jobs(database, results)
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT job, level FROM member_jobs ORDER BY job"
    ).fetchall() == [("DRK", 37), ("PLD", 24)]
    connection.close()
