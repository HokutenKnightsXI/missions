# Missions

A lightweight linkshell command board for coordinating HorizonXI **Chains of Promathia** and **Rise of the Zilart** mission progress. Members record their current mission, jobs, availability, and where they need help; the roster can then be filtered to find a party.

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

## Current scope

- Add and update linkshell members
- Look up job levels from HorizonXI by character name, then select available jobs
- Manually enter job levels when the external service is unavailable
- Track CoP and Zilart chapter, mission, status, and help needed
- Filter by campaign, mission text, available job, and status
- Store Discord name, timezone, and usual availability

The board is public to view. Adding, updating, and deleting records requires the shared
linkshell password configured with `EDIT_PASSWORD`; the password is never stored in GitHub.

