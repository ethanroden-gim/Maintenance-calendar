# GIM Maintenance Schedule — setup

This site is generated from the **private** GIM Google Calendar by a GitHub
Action and published to GitHub Pages. The calendar stays private; only the
formatted page is public. No credentials live in the page — the service-account
key is stored as a GitHub **secret**.

## One-time setup

### 1. Create a Google service account
1. Go to <https://console.cloud.google.com/> → create (or pick) a project.
2. **APIs & Services → Library** → enable **Google Calendar API**.
3. **APIs & Services → Credentials → Create credentials → Service account**.
   Give it a name (e.g. `gim-calendar-reader`), create it.
4. Open the service account → **Keys → Add key → Create new key → JSON**.
   Download the JSON file. Note the service-account **email**
   (`...@<project>.iam.gserviceaccount.com`).

### 2. Share the calendar with the service account
1. In Google Calendar, hover the GIM maintenance calendar → **⋮ → Settings and
   sharing**.
2. Under **Share with specific people or groups → Add people** → paste the
   service-account email → permission **"See all event details"** → Send.
   *(The calendar stays private to the public; only this robot account can read it.)*

### 3. Add the secret + variable to GitHub
In the repo: **Settings → Secrets and variables → Actions**.
- **Secrets → New repository secret**
  - Name: `GCAL_CREDENTIALS`
  - Value: paste the entire contents of the downloaded JSON key file.
- **Variables → New repository variable** (optional — only if the calendar id changes)
  - Name: `CALENDAR_ID`
  - Value: the calendar id (defaults to the GIM calendar baked into `generate.py`).

### 4. Switch Pages to GitHub Actions
**Settings → Pages → Build and deployment → Source → GitHub Actions.**

### 5. Run it
**Actions → "Build & deploy calendar page" → Run workflow.** After it succeeds,
the page is live at the Pages URL. It then rebuilds **hourly** automatically and
on every push to `main`.

## Local preview
```bash
pip install -r requirements.txt
DEMO=1 python generate.py        # renders sample events to public/index.html
# or with real creds:
export GCAL_CREDENTIALS="$(cat key.json)"
python generate.py
```

## Files
- `generate.py` — fetches events and renders `public/index.html`.
- `template.html` — page shell / styling (GIM brand).
- `.github/workflows/deploy.yml` — hourly build + deploy.
- `requirements.txt` — Python deps.
