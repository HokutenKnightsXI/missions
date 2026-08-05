"""Fetch current HorizonXI jobs and submit them to the deployed roster."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


HORIZON_API = "https://api.horizonxi.com/api/v1"
JOBS = {
    "WAR", "MNK", "WHM", "BLM", "RDM", "THF", "PLD", "DRK", "BST",
    "BRD", "RNG", "SAM", "NIN", "DRG", "SMN",
}


def get_json(url, *, headers=None, timeout=20):
    request = Request(url, headers=headers or {"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def fetch_player(name):
    try:
        player = get_json(
            f"{HORIZON_API}/chars/{quote(name)}",
            headers={"Accept": "application/json", "User-Agent": "HokutenRosterRefresh/1.0"},
        )
        jobs = {
            job: int(level)
            for job, level in player.get("jobs", {}).items()
            if job in JOBS and isinstance(level, (int, float))
            and not isinstance(level, bool) and 1 <= int(level) <= 75
        }
        return name, jobs, None if jobs else "no job data returned"
    except HTTPError as error:
        return name, None, f"HTTP {error.code}"
    except (URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
        return name, None, str(error)


def main():
    base_url = os.environ.get("ROSTER_BASE_URL", "https://maven.pythonanywhere.com").rstrip("/")
    token = os.environ.get("ROSTER_REFRESH_TOKEN", "")
    if not token:
        raise SystemExit("ROSTER_REFRESH_TOKEN is required")

    roster = get_json(f"{base_url}/api/job-roster/members")
    names = roster.get("members", [])
    if not isinstance(names, list) or not names:
        raise SystemExit("The deployed roster returned no members; refusing an empty refresh")

    results, failures = {}, {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_player, name): name for name in names}
        for future in as_completed(futures):
            name, jobs, error = future.result()
            if error:
                failures[name] = error
            else:
                results[name] = jobs

    if not results:
        raise SystemExit("Every HorizonXI lookup failed; existing roster was left unchanged")
    body = json.dumps({"players": results}).encode("utf-8")
    update_request = Request(
        f"{base_url}/api/job-roster/refresh",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "HokutenRosterRefresh/1.0",
        },
    )
    try:
        with urlopen(update_request, timeout=30) as response:
            applied = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Roster update failed with HTTP {error.code}: {detail}") from error

    print(f"Updated {applied.get('updated', 0)} of {len(names)} registered characters.")
    if failures:
        print(f"Kept existing data for {len(failures)} unavailable characters:")
        for name, error in sorted(failures.items()):
            print(f"  {name}: {error}")


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"Refresh failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
