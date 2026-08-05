# HK XI

A linkshell command board for coordinating HorizonXI **Chains of Promathia** and **Rise of the Zilart** mission progress. Members record their current mission, jobs, availability, and where they need help; the roster can then be filtered to find a party.

## Run locally

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python missions.py
```

Open <http://127.0.0.1:5000>. The SQLite database is created automatically at `instance/missions.db`.

## Tests

```powershell
pytest
```

## Import the live mission roster

The public Maven roster can be merged into a local or newly deployed database without
changing Help Requests. Preview the import first, then apply it:

```powershell
python import_live_roster.py
python import_live_roster.py --apply
```

The applied import creates a timestamped backup beside `instance/missions.db`, matches
characters case-insensitively, and updates their jobs, availability, CoP progress, and
Rise of the Zilart progress.

The public mission board only includes jobs members chose to advertise. Refresh every
available CoP-era job level directly from HorizonXI after importing:

```powershell
python refresh_horizon_jobs.py
python refresh_horizon_jobs.py --apply
```

Only successful character lookups are updated, and applying the refresh creates another
timestamped database backup.

On a host that blocks HorizonXI requests, apply the bundled offline snapshot instead:

```bash
python refresh_horizon_jobs.py --snapshot horizon_jobs_snapshot.json
python refresh_horizon_jobs.py --snapshot horizon_jobs_snapshot.json --apply
```

## Current scope

- Add and update linkshell members
- Look up job levels from HorizonXI by character name, then select available jobs
- Manually enter job levels when the external service is unavailable
- Track CoP and Zilart chapter, mission, status, and help needed
- Filter by campaign, mission text, available job, and status
- Store Discord name, timezone, and usual availability
- Post general help requests with level-cap-aware job selections and flexible scheduling
- Browse rolling and fixed-date requests on a monthly calendar
- Volunteer jobs, form a party roster, and track requests through completion

The board is public to view. Adding, updating, and deleting records requires the shared
linkshell password configured with `EDIT_PASSWORD`; the password is never stored in GitHub.

