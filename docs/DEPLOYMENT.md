# Deployment guide

The repository is deployment-ready, but **no public deployment has been
performed yet**. You need your own hosting account, API keys, and domain.

## Production checklist

- [ ] Set `APP_ENV=production`.
- [ ] Set `AUTH_REQUIRED=1`.
- [ ] Set a long random `AUTH_SECRET` (not the development fallback).
- [ ] Set `CORS_ORIGINS` to the exact public frontend origin.
- [ ] Set `SERVE_FRONTEND=1` for the single-container build.
- [ ] Add `GEMINI_API_KEY` and `TAVILY_API_KEY` as host secrets.
- [ ] Mount persistent storage at `/app/data`.
- [ ] Use HTTPS (the hosting platform normally terminates TLS).
- [ ] Run `GET /api/health` and confirm `"status": "ok"`.
- [ ] Register a real account and verify profile/bookmark isolation.
- [ ] Add rate limiting before exposing discovery publicly.
- [ ] Do not commit `.env`, `profile.json`, `bookmarks.json`, or `*.db`.

## Option 1: Docker (single service)

```powershell
cd F:\opportunity-agent

# Build the React app and Python runtime into one image
docker build -t opportunity-agent .

docker run --rm -p 8000:8000 `
  --env-file .env `
  -e APP_ENV=production `
  -e SERVE_FRONTEND=1 `
  -e AUTH_REQUIRED=1 `
  -v opportunity_data:/app/data `
  opportunity-agent
```

Open <http://localhost:8000>. FastAPI serves the React build and the API
from the same origin.

`docker compose up --build` reads `.env` and uses the named volume
declared in `docker-compose.yml`.

### Building for a separate frontend host

If the UI is hosted separately, build it with an explicit API origin:

```powershell
cd frontend
$env:VITE_API_BASE = "https://your-api.example.com"
& F:\Tools\nodejs\npm.cmd run build
```

Then set the backend's `CORS_ORIGINS` to the frontend origin. Do not put
API keys in `VITE_*` variables; Vite exposes them to the browser.

## Option 2: Render

`render.yaml` defines a Docker web service with:

- health check `/api/health`
- generated `AUTH_SECRET`
- secret prompts for Gemini, Tavily, and email credentials
- a 1 GB disk mounted at `/app/data`

Update `CORS_ORIGINS` to your actual Render URL before deploying. The
blueprint uses the `starter` plan because persistent disks are not
available on every free tier. SQLite durability depends on that disk.

```text
New Render Blueprint -> select this repository -> apply render.yaml
```

## Option 3: Railway / Fly.io / a VPS

Use the Dockerfile directly. Requirements:

1. Persistent volume mounted at `/app/data`.
2. `$PORT` support — override the container command if the platform
   injects a port, for example:
   `uvicorn api:app --host 0.0.0.0 --port $PORT`
3. Environment variables from the checklist.
4. HTTPS at the edge.

## Database and backups

SQLite lives at `OPPORTUNITY_DB_PATH` (default
`data/opportunity_agent.db`). Back up the file, or export a portable
snapshot:

```powershell
.\.venv\Scripts\python.exe -c "from storage import export_opportunities_json; export_opportunities_json('opportunities.backup.json')"
```

The GitHub Actions workflow restores `opportunities.json` into a fresh
database, runs discovery, and commits the updated snapshot. This keeps a
versioned opportunity memory even if the hosted SQLite volume is lost.

Do **not** commit user bookmarks or profiles. The snapshot contains only
the shared opportunity corpus.

## Post-deployment smoke test

```powershell
Invoke-RestMethod https://your-domain/api/health
```

Expected:

```json
{
  "status": "ok",
  "app": "Opportunity Agent",
  "storage": "sqlite",
  "auth": "required",
  "auth_warning": ""
}
```

Then in the browser:

1. Create an account.
2. Save an opportunity, refresh, confirm it remains saved.
3. Sign out and create a second account; confirm the first account's
   bookmarks and profile are not visible.
4. Open a detail drawer and run **Check links now**.
5. Confirm the application page is truthful about uncertainty.

## Cost and abuse controls

Discovery calls Tavily and Gemini. Before making `/api/discover` public:

- add per-user/IP rate limiting,
- lower `limit` for normal users,
- consider a queue or admin-only discovery trigger,
- cache search results,
- monitor provider quotas.

The current request limit is capped at 3 Gemini extractions per call in
`api.py`.

## Rollback

- Redeploy the previous image.
- The SQLite schema is additive; keep a copy of the database before
  changing schema versions.
- Legacy JSON tables and the original `opportunities.json` remain
  available for recovery.