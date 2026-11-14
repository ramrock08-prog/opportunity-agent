# Opportunity Agent

**An AI-powered opportunity discovery platform for students.**

Opportunity Agent searches the web for internships, hackathons, jobs,
scholarships, fellowships, competitions, and research programs; extracts
structured records with Gemini; validates them; stores them in SQLite;
and ranks them against a student profile in a React dashboard.

This project grew out of the original
[`hackathon-agent`](https://github.com/ramrock08-prog/hackathon-agent)
drone-hackathon scout. The original search, AI filtering, link checking,
email digest, and GitHub Actions ideas are preserved and generalized.

> **Data-quality principle:** this app does not claim an opportunity is
> "verified open". Link checks prove only that a page responded. Deadline,
> eligibility, and open/closed status must be confirmed on the official
> page.

---

## Features

### Discovery and AI
- Tavily web search across seven opportunity categories.
- Gemini structured extraction with strict anti-hallucination rules.
- Verbatim evidence snippets stored with each record.
- Deadlines are only accepted when the source supports them.
- Rule-based validation (URLs, category, confidence, date format, past deadlines).
- URL and title/organization deduplication.
- Optional on-demand link verification with honest status reporting.
- SSRF protection: verification only fetches stored URLs on public hosts.

### Web application
- Responsive React dashboard with dark sidebar.
- Search, category filters, and sorting that work together.
- Personalized "For you" ranking with transparent reasons.
- Save/unsave opportunities with persistent per-user bookmarks.
- Saved opportunities view with a live count.
- Opportunity detail drawer with eligibility, skills, stipend, evidence,
  source/application links, and a manual link check.
- Profile editor for degree, branch, year, skills, interests, locations,
  remote preference, and categories.
- Loading, empty, error, and backend-offline states.

### Accounts and security
- Optional JWT authentication (`AUTH_REQUIRED=1`).
- PBKDF2-SHA256 password hashing with per-password salt.
- Strict per-user profiles, bookmarks, and recommendations.
- Demo workspace when authentication is disabled.
- Secrets stay server-side; the frontend never receives API keys.

### Operations
- SQLite persistence with automatic legacy JSON import.
- Transactional writes and a discovery mutex.
- HTML email digest (`notify.py --preview` / `--send`).
- GitHub Actions scheduled discovery with JSON snapshot persistence.
- Docker multi-stage build; Render blueprint included.
- 54 automated backend/API tests plus two Playwright browser flows.

---

## Architecture

```text
                    GitHub Actions (schedule)
                               |
                               v
   Tavily Search  ->  Gemini extraction  ->  validator  ->  deduplicator
                               |                              |
                               |                              v
                     evidence + deadline checks          SQLite
                                                             |
                                                             v
 React dashboard  <----------  FastAPI REST API  <------  services
       |                              |
       |                              +--> JWT auth (optional)
       |                              +--> on-demand link verification
       +--> save / search / filter / detail drawer / profile editor
```

**Backend stack:** Python 3.10+, FastAPI, Pydantic, SQLite, google-genai,
Tavily, PyJWT, requests.

**Frontend stack:** React 19, Vite 8, JavaScript, CSS, ESLint.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for request flows,
schema, and trust boundaries.

---

## Quick start (Windows PowerShell)

### 1. Backend

```powershell
cd F:\opportunity-agent

# Activate or create the virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Create local configuration (never commit .env)
Copy-Item .env.example .env
notepad .env   # add GEMINI_API_KEY and TAVILY_API_KEY

# Run the API
.\.venv\Scripts\python.exe -m uvicorn api:app --reload
```

- API: <http://127.0.0.1:8000>
- Interactive docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

### 2. Frontend

In a second terminal:

```powershell
cd F:\opportunity-agent\frontend
& F:\Tools\nodejs\npm.cmd install
& F:\Tools\nodejs\npm.cmd run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to FastAPI, so no CORS
setup is needed for local development.

> On this machine, use `npm.cmd` instead of `npm` because the PowerShell
> script wrapper is blocked by execution policy.

### 3. Production build

```powershell
cd F:\opportunity-agent\frontend
& F:\Tools\nodejs\npm.cmd run build
```

FastAPI serves `frontend/dist` at `/` when `SERVE_FRONTEND=1`:

```powershell
$env:SERVE_FRONTEND = "1"
.\.venv\Scripts\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000
```

---

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | Gemini extraction | required for discovery |
| `GEMINI_MODEL` | Gemini model ID | `gemini-3.5-flash-lite` |
| `TAVILY_API_KEY` | Web search | required for discovery |
| `OPPORTUNITY_DB_PATH` | SQLite file | `data/opportunity_agent.db` |
| `CORS_ORIGINS` | Comma-separated allowed origins | localhost:5173 |
| `SERVE_FRONTEND` | Serve React build from FastAPI | `0` |
| `AUTH_REQUIRED` | Require sign-in for user data | `0` |
| `AUTH_SECRET` | JWT signing secret | dev fallback |
| `AUTH_TOKEN_MINUTES` | Token lifetime | `10080` (7 days) |
| `SENDER_EMAIL` | Digest sender | optional |
| `SENDER_PASSWORD` | Gmail app password | optional |
| `RECEIVER_EMAIL` | Digest recipient | optional |

Generate a production secret:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

The configured Gemini model was verified against the API key with
`client.models.list()`; no generation credits were used.

---

## Discovery commands

```powershell
# One category, three Gemini extractions max
.\.venv\Scripts\python.exe .\run_agent.py --category internship --limit 3

# Revalidate stored records and export a JSON backup
.\.venv\Scripts\python.exe .\clean_saved.py

# Rank current opportunities in the terminal
.\.venv\Scripts\python.exe .\recommend.py

# Preview the email digest without sending
.\.venv\Scripts\python.exe .\notify.py --preview

# Send the digest (requires Gmail variables)
.\.venv\Scripts\python.exe .\notify.py --send
```

`run_agent.py` revalidates existing records before saving, so expired or
malformed rows do not silently accumulate.

---

## API overview

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/` | – | API info or production React app |
| GET | `/api` | – | API info |
| GET | `/api/health` | – | Status, storage, auth mode |
| GET | `/api/auth/status` | – | Whether sign-in is required |
| POST | `/api/auth/register` | – | Create account, return JWT |
| POST | `/api/auth/login` | – | Exchange credentials for JWT |
| GET | `/api/auth/me` | Bearer | Current user |
| GET | `/api/opportunities` | – | Validated opportunities |
| POST | `/api/opportunities/verify` | – | Check stored links on demand |
| GET | `/api/recommendations` | User | Ranked for current profile |
| GET | `/api/profile` | User | Current profile |
| PUT | `/api/profile` | User | Update current profile |
| POST | `/api/discover` | User | Run limited discovery |
| GET | `/api/bookmarks` | User | Current user's bookmarks |
| POST | `/api/bookmarks` | User | Save a bookmark |
| DELETE | `/api/bookmarks?url=...` | User | Remove a bookmark |

"User" means the demo user when `AUTH_REQUIRED=0`, or a valid bearer token
when authentication is enabled.

---

## Testing

```powershell
# Backend unit, database, auth, API, validation, scoring, digest tests
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Current result: **54 passed** (API tests use disposable temp databases).

### Browser tests

`scripts/e2e_bookmarks.py` verifies save → refresh → saved-view → remove →
details drawer → mocked link check. Requires:
- FastAPI on `127.0.0.1:8000`
- Vite on `127.0.0.1:5173`
- Microsoft Edge installed (Playwright uses `channel="msedge"`)

```powershell
.\.venv\Scripts\python.exe .\scripts\e2e_bookmarks.py
```

`scripts/e2e_auth.py` verifies registration → profile save → logout →
login → restored profile. It requires an auth-enabled backend on port
`8001` and a Vite server on port `5174` with
`VITE_API_BASE=http://127.0.0.1:8001`. See the script docstring.

Credit-consuming integration probes are deliberately isolated in
`scripts/manual/` so `pytest` never spends Tavily or Gemini credits.

---

## Docker

> Docker is not installed on this development machine, so the image
> recipe has not been executed here. The equivalent production path was
> verified locally by building `frontend/dist` and serving it from
> FastAPI with `SERVE_FRONTEND=1`.

```powershell
# Build the frontend and backend into one image
docker build -t opportunity-agent .

# Run with your local secrets
docker run --rm -p 8000:8000 --env-file .env `
  -e SERVE_FRONTEND=1 -e AUTH_REQUIRED=1 `
  -v opportunity_data:/app/data opportunity-agent
```

Or:

```powershell
docker compose up --build
```

SQLite needs a persistent volume at `/app/data`. The included
`render.yaml` describes a Render deployment; update `CORS_ORIGINS` to
your real URL. Full instructions: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Project structure

```text
opportunity-agent/
├── api.py                  FastAPI app, auth dependencies, routes
├── auth.py                 PBKDF2 hashing + JWT helpers
├── database.py             SQLite schema, migrations, legacy import
├── storage.py              Opportunity repository + JSON export
├── bookmarks.py            Per-user bookmark repository
├── profile.py              Per-user profile model + repository
├── opportunity.py          Opportunity dataclass
├── search.py               Tavily queries and search
├── ai.py                   Gemini extraction prompt + parsing
├── validator.py            Rule-based data validation
├── dedup.py                URL/title deduplication
├── verification.py         Honest on-demand link checks (SSRF-aware)
├── scorer.py               Transparent 0–100 relevance score
├── text_utils.py           Whitespace/encoding hygiene
├── run_agent.py            Discovery pipeline CLI
├── notify.py               HTML email digest
├── agent.py                Legacy original drone scout (kept for history)
├── tests/                  Pytest suite (54 tests)
├── scripts/
│   ├── e2e_bookmarks.py    Playwright bookmark/details flow
│   ├── e2e_auth.py         Playwright auth flow
│   └── manual/             Credit-consuming integration probes
├── frontend/
│   ├── src/App.jsx          Dashboard shell and data loading
│   ├── src/AuthScreen.jsx   Sign-in / registration
│   ├── src/OpportunityCard.jsx
│   ├── src/OpportunityDetail.jsx
│   ├── src/ProfileEditor.jsx
│   └── vite.config.js       Dev proxy to FastAPI
├── docs/
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
└── requirements-dev.txt
```

`data/opportunity_agent.db` is created at runtime and ignored by Git.
`bookmarks.json` and `profile.json` are legacy/private local files and are
also ignored.

---

## Data model

`Opportunity` fields: title, type, organization, description, source and
application URLs, deadline, start date, location, remote flag, eligibility,
required skills, fields, degree/year requirements, stipend, prize money,
source host, confidence, verbatim evidence, and deadline evidence.

Relevance scoring is deliberately transparent:

| Component | Maximum points |
|---|---|
| Selected opportunity type | 20 |
| Interest matches | 35 |
| Skill matches | 20 |
| Location match | 15 |
| Remote preference | 10 |

The final score is normalized to 0–100. It is a **relevance estimate**,
not an eligibility decision.

---

## Security notes

Implemented:
- `.env`, local profile, bookmarks, and the SQLite database are gitignored.
- Password hashing uses PBKDF2-SHA256 with random salts.
- JWTs are signed and expire.
- Per-user queries prevent cross-account profile/bookmark access.
- API keys never reach the browser.
- CORS uses an explicit allow-list.
- Link verification rejects private/loopback hosts to reduce SSRF risk.
- Frontend HTML escapes untrusted opportunity text via React; email HTML
  is explicitly escaped.

Not yet production-hardened:
- No rate limiting on discovery or authentication.
- No email verification, password reset, or account lockout.
- No refresh-token rotation or server-side token revocation.
- SQLite is suitable for a single instance, not horizontal scaling.
- The discovery mutex is per process; multi-worker deployments need a
  database/queue lock.

These are documented intentionally rather than hidden.

---

## Roadmap status

- **Phase A — Core frontend:** complete (details, saved count, filters,
  sorting, profile, search, states).
- **Phase B — Backend architecture:** complete for SQLite; JSON storage
  replaced with automatic migration. PostgreSQL is a future option.
- **Phase C — AI quality:** evidence snippets, deadline-evidence rules,
  on-demand link verification, deduplication, confidence scoring.
- **Phase D — Original functionality:** email digest and scheduled GitHub
  Actions restored on the generalized pipeline.
- **Phase E — Accounts:** optional JWT auth with per-user isolation.
- **Phase F — Deployment:** Docker, Render blueprint, documentation;
  an actual public deployment still needs your hosting account and keys.
- **Phase G — Interview readiness:** architecture, tests, and trade-offs
  documented here and in `docs/`.

---

## Honest limitations

- Search snippets can be incomplete; extraction may miss facts.
- A reachable URL does not prove a role is open.
- Eligibility and deadlines are only as reliable as the source snippet.
- Discovery quality depends on Tavily ranking and Gemini extraction.
- The app intentionally keeps records with unknown deadlines rather than
  inventing one (validation rejects only dates that are malformed or past).
- Existing stored records may contain older encoding artifacts; new
  records are cleaned automatically.

Always verify on the official page before applying.

---

## License

MIT. See [`LICENSE`](LICENSE). The original drone-scout project is also
MIT-licensed; the legacy `agent.py` is retained for history rather than
used by the web application.
