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

## Free public deployment (PythonAnywhere)

PythonAnywhere is a good fit for this small SQLite app because its account files persist.
Free web apps currently need to be renewed once per month in the PythonAnywhere dashboard.

1. Create a free account at <https://www.pythonanywhere.com>. Your public URL will be
   `https://YOUR_USERNAME.pythonanywhere.com`.
2. Open a Bash console there and clone this GitHub repository, then install Flask:

   ```bash
   git clone YOUR_GITHUB_REPOSITORY_URL ~/Missions
   python -m venv ~/.virtualenvs/missions
   ~/.virtualenvs/missions/bin/pip install -r ~/Missions/requirements.txt
   ```

3. Create `~/Missions/.env` in the PythonAnywhere Files tab (it is ignored by Git):

   ```text
   EDIT_PASSWORD=your-shared-linkshell-password
   SECRET_KEY=a-long-random-value
   COOKIE_SECURE=true
   ```

   Generate the secret in a PythonAnywhere console with
   `python -c "import secrets; print(secrets.token_hex(32))"`.
4. In **Web**, choose **Add a new web app**, **Manual configuration**, and a current
   Python version. Set the virtualenv to `/home/YOUR_USERNAME/.virtualenvs/missions`.
5. Replace the WSGI configuration file contents with the following, substituting your
   username:

   ```python
   import os
   import sys

   project = "/home/YOUR_USERNAME/Missions"
   if project not in sys.path:
       sys.path.insert(0, project)

   with open(os.path.join(project, ".env"), encoding="utf-8") as settings:
       for line in settings:
           key, separator, value = line.strip().partition("=")
           if separator and key:
               os.environ[key] = value

   from missions import app as application
   ```

6. On the **Web** tab, add `/static/` mapped to `/home/YOUR_USERNAME/Missions/static`,
   reload the app, and open its public URL.

Free PythonAnywhere accounts restrict outbound web requests. If the HorizonXI job lookup
is not allowlisted, members can still enter job levels manually.
