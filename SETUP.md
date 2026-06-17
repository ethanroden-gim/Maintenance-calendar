# GIM Maintenance Schedule — setup

This site is generated from the **private** GIM maintenance calendar and published
to GitHub Pages. The calendar stays private; only the formatted page is public.

**How it reads the calendar:** a small **Google Apps Script** web app (running under
your Google account's authorization — the same model as the Meeting Dashboard)
exposes *only* the maintenance calendar as JSON. An hourly GitHub Action fetches
that JSON and rebuilds the page. No service account, no key files.

## One-time setup

### 1. Deploy the Apps Script feed
1. Go to <https://script.google.com> → **New project**.
2. Paste the contents of [`apps-script/Maintenance-Feed.gs`](apps-script/Maintenance-Feed.gs)
   into `Code.gs`.
3. Editor left rail → **Services (+)** → add **Calendar API** (advanced service).
4. **Deploy → New deployment → Web app**:
   - **Execute as:** Me
   - **Who has access:** Anyone
   - Deploy, authorize when prompted, and **copy the `/exec` URL**.
5. *(Recommended)* lock the feed down: **Project Settings → Script Properties →
   Add property** `FEED_TOKEN` = some random string. The feed then only responds
   to `<exec-url>?token=<that string>`.

### 2. Add the feed URL as a GitHub secret
Repo → **Settings → Secrets and variables → Actions → Secrets → New repository secret**:
- Name: `CALENDAR_FEED_URL`
- Value: the `/exec` URL (append `?token=<FEED_TOKEN>` if you set one in step 1.5).

### 3. Switch Pages to GitHub Actions
**Settings → Pages → Build and deployment → Source → GitHub Actions.**

### 4. Run it
**Actions → "Build & deploy calendar page" → Run workflow.** After it succeeds the
page is live. It then rebuilds **hourly** and on every push to `main`.

## Local preview
```bash
pip install -r requirements.txt
DEMO=1 python generate.py                      # sample events → public/index.html
# or against the real feed:
CALENDAR_FEED_URL="https://script.google.com/.../exec?token=..." python generate.py
```

## Files
- `apps-script/Maintenance-Feed.gs` — Apps Script JSON feed (deploy in Google, not in CI).
- `generate.py` — fetches the feed and renders `public/index.html`.
- `template.html` — page shell / styling (GIM brand).
- `.github/workflows/deploy.yml` — hourly build + deploy.
- `requirements.txt` — Python deps (just `tzdata`).
