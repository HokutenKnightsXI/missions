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

## Discord sign-in

Create an application in the Discord Developer Portal and register the deployment callback
URL, for example `https://example.com/discord/callback`. Configure these environment
variables on the host:

```text
DISCORD_CLIENT_ID=your_application_id
DISCORD_CLIENT_SECRET=your_application_secret
DISCORD_GUILD_ID=your_hokuten_server_id
DISCORD_REDIRECT_URI=https://example.com/discord/callback
DISCORD_ADMIN_USER_ID=your_permanent_discord_user_id
```

Members should set their nickname in the Hokuten Discord server to their exact HorizonXI
character name before linking. If no server nickname is set, the Discord display name or
username is used. The OAuth application requests only `identify` and
`guilds.members.read`. An existing unlinked roster entry is matched case-insensitively;
otherwise a new member is created. The permanent Discord user ID is stored so later
nickname changes cannot transfer the character. The `Imaven` character is reserved for
`DISCORD_ADMIN_USER_ID`; administrator access is granted only when that permanent ID
signs in, never from an editable nickname.

Once Discord is configured, shared member and administrator password sign-in are
disabled. Password recovery remains available only when Discord configuration is
incomplete.

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

## Free daily roster refresh

The `Refresh HorizonXI job roster` GitHub Actions workflow fetches current player data
once per day and sends only successful lookups to the deployed site. A failed or missing
HorizonXI profile keeps its existing saved levels.

Configure the same long random value in both places:

1. Set `ROSTER_REFRESH_TOKEN` in the PythonAnywhere WSGI configuration before importing
   the application, then reload the web app.
2. In GitHub, open **Settings → Secrets and variables → Actions**, create a repository
   secret named `ROSTER_REFRESH_TOKEN`, and paste the same value.
3. Open **Actions → Refresh HorizonXI job roster → Run workflow** to test it immediately.

Generate a suitable token locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The workflow runs daily at 10:17 UTC. Its update endpoint does not use the linkshell or
administrator passwords and modifies only `member_jobs` plus each updated member's
timestamp.

## Hourly auction values

The general loot table retrieves the complete HorizonXI market snapshot from PSXI and
caches a compact copy at `instance/psxi_market_snapshot.json` for one hour. Configure a
free PSXI API token on the host so the integration continues working after anonymous
market access is retired:

```text
PSXI_API_TOKEN=psxi_your_token
```

The token remains server-side and is never returned to the browser. If PSXI is temporarily
unavailable, the loot table continues working and displays unavailable market values.

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

The board is public to view. When Discord OAuth is configured, members authenticate through
the Hokuten server and only linked administrators can manage other characters. Without
Discord configuration, the legacy shared password remains available for compatibility.

