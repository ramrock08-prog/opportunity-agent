# Deployment guide

The project is deployed on Render:

- **App:** <https://opportunity-agent-v39s.onrender.com>
- **Database:** Render PostgreSQL (free, Oregon)
- **CI:** GitHub Actions

Current live limitation: `AUTH_REQUIRE_VERIFIED=0` because no Gmail SMTP
credentials are configured yet. Add `SENDER_EMAIL` and
`SENDER_PASSWORD` in Render, then set `AUTH_REQUIRE_VERIFIED=1` and
redeploy to enforce verification.

## Production checklist

- [ ] Set `APP_ENV=production`.
- [ ] Set `AUTH_REQUIRED=1`.
- [ ] Set `AUTH_REQUIRE_VERIFIED=1`.
- [ ] Keep `AUTH_DEV_SHOW_TOKENS=0`.
- [ ] Set a long random `AUTH_SECRET`.
- [ ] Set `PUBLIC_APP_URL` to the public URL used in emails.
- [ ] Set `CORS_ORIGINS` to the exact public frontend origin.
- [ ] Set `SERVE_FRONTEND=1` for the single-container build.
- [ ] Configure `SENDER_EMAIL`, `SENDER_PASSWORD` (Gmail app password),
      and `RECEIVER_EMAIL` if you want verification/reset/digest email.
- [ ] Add `GEMINI_API_KEY` and `TAVILY_API_KEY` as host secrets.
- [ ] Choose storage: `OPPORTUNITY_DB_PATH` on a persistent disk, or
      `DATABASE_URL` pointing at PostgreSQL.
- [ ] Use HTTPS (the hosting platform normally terminates TLS).
- [ ] Run `GET /api/health` and confirm `"status": "ok"`.
- [ ] Register a real account, verify the email, and confirm
      profile/bookmark isolation with a second account.
- [ ] Do not commit `.env`, `profile.json`, `bookmarks.json`, or `*.db`.

## Option 1: Docker + SQLite (single service, persistent disk)

```powershell
cd F:\opportunity-agent

docker build -t opportunity-agent .

docker run --rm -p 8000:8000 `
  --env-file .env `
  -e APP_ENV=production `
  -e SERVE_FRONTEND=1 `
  -e AUTH_REQUIRED=1 `
  -e AUTH_REQUIRE_VERIFIED=1 `
  -e AUTH_DEV_SHOW_TOKENS=0 `
  -e PUBLIC_APP_URL=http://localhost:8000 `
  -v opportunity_data:/app/data `
  opportunity-agent
```

Open <http://localhost:8000>. FastAPI serves the React build and the API
from the same origin.

> Docker was not installed on the development machine, so the image was
> not built locally. The same production path was verified by building
> `frontend/dist` and serving it from FastAPI with `SERVE_FRONTEND=1`.

## Option 2: Docker + PostgreSQL

`docker-compose.postgres.yml` starts PostgreSQL 16 and the app:

```powershell
$env:POSTGRES_PASSWORD = "choose-a-strong-password"
docker compose -f docker-compose.postgres.yml up --build
```

Or point any deployment at a managed PostgreSQL server:

```text
DATABASE_URL=postgresql://user:password@host:5432/database
```

The app creates its schema automatically and runs the one-time JSON
import if the database is empty. `DATABASE_URL` takes precedence over
`OPPORTUNITY_DB_PATH`.

## Option 3: Render

`render.yaml` defines a free Docker web service with:

- health check `/api/health`
- generated `AUTH_SECRET`
- rate limiting enabled and `TRUST_PROXY=1`
- secret prompts for Gemini, Tavily, and email credentials
- free-plan SQLite fallback at `/app/data/opportunity_agent.db`

The live service uses a **Render PostgreSQL** database instead of the
ephemeral SQLite fallback. Create a free Render Postgres instance in the
same region (Oregon) and set `DATABASE_URL` from its internal connection
string. Cross-region internal URLs do not work.

```text
New Render Blueprint -> select this repository -> apply render.yaml
```

The free web plan has ephemeral storage; PostgreSQL is required for
durable accounts/bookmarks.

## Email configuration

User accounts require email delivery when verification is enforced.

- `SENDER_EMAIL`: Gmail address.
- `SENDER_PASSWORD`: Gmail **app password**, not the account password.
- `RECEIVER_EMAIL`: digest recipient (verification/reset emails go to the
  user's own address).
- `PUBLIC_APP_URL`: public site URL used to build email links.

For local development without SMTP, set:

```text
AUTH_REQUIRED=1
AUTH_REQUIRE_VERIFIED=1
AUTH_DEV_SHOW_TOKENS=1
```

The UI then exposes a **Verify now (development)** action. Never enable
this in production.

## Database and backups

### SQLite

SQLite lives at `OPPORTUNITY_DB_PATH` (default
`data/opportunity_agent.db`). Back up the file, or export a portable
snapshot:

```powershell
.\.venv\Scripts\python.exe -c "from storage import export_opportunities_json; export_opportunities_json('opportunities.backup.json')"
```

The GitHub Actions workflow restores `opportunities.json` into a fresh
database, runs discovery, and commits the updated snapshot.

### PostgreSQL

Use the provider's automated backups. Schema creation is automatic. The
integration test suite can be run against a real server with:

```powershell
.\.venv\Scripts\python.exe .\scripts\test_postgres.py
```

Do **not** commit user bookmarks or profiles. The snapshot contains only
the shared opportunity corpus.

## Post-deployment smoke test

```powershell
Invoke-RestMethod https://your-domain/api/health
```

Expected (SQLite example):

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
2. Verify the email from the delivered message.
3. Save an opportunity, refresh, and confirm it remains saved.
4. Sign out; confirm the old token is rejected.
5. Request a password reset; confirm the link works and old sessions are
   invalidated.
6. Create a second account; confirm it cannot see the first account's
   profile or bookmarks.
7. Open a detail drawer and run **Check links now**.
8. Confirm the application page is truthful about uncertainty.

## Cost and abuse controls

Discovery calls Tavily and Gemini. Rate limits are enabled by default,
but you should still monitor provider quotas. The API caps discovery at
3 Gemini extractions per call and 5 discovery runs per user per hour.

Consider lowering these limits or making discovery admin-only for a
public portfolio deployment.

## Rollback

- Redeploy the previous image.
- Keep a copy of the database before changing schema versions.
- Legacy JSON tables and the original `opportunities.json` remain
  available for recovery.
- `schema_meta.schema_version` records the applied schema version.