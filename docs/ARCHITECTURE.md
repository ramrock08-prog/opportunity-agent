# Architecture

## System overview

```text
Browser (React + Vite)
   |
   |  same-origin /api (Vite proxy in dev, FastAPI in production)
   v
FastAPI (api.py)
   |-- auth dependency (auth.py) ------------------> users/sessions
   |-- profile service (profile.py) ---------------> user_profiles
   |-- bookmark service (bookmarks.py) ------------> user_bookmarks
   |-- opportunity service (storage.py) -----------> opportunities
   |-- resume import (resume.py + ai.py) ----------> profile preview
   |-- recommendation engine (scorer.py)
   |-- rate limiter (rate_limit.py) ---------------> rate_limits
   |-- discovery lock (locks.py) -------------------> discovery_locks
   |-- on-demand verification (verification.py) ---> external websites
   |
   v
database.py adapter
   |-- SQLite (default)
   +-- PostgreSQL (DATABASE_URL)
```

Discovery is a separate pipeline, callable from the CLI or the API:

```text
search.py (Tavily) -> ai.py (Gemini) -> validator.py -> dedup.py
          |                               |              |
          |                               v              v
          |                       link/date rules     database upsert
          |
curated.py (open-source internship datasets) -> normalize -> dedup -> database
```

## Main request flows

### Dashboard load

1. React asks `GET /api/auth/status`.
2. In demo mode, every user-scoped request resolves to the demo account
   (id `1`).
3. In auth mode, the browser sends `Authorization: Bearer <jwt>`.
4. The JWT is verified, then its `jti` is checked against the
   `sessions` table. Revoked or expired sessions return 401.
5. The API loads validated opportunities, the user's profile, the user's
   bookmarks, and ranked recommendations.
6. React combines them in memory for search, category filters, sorting,
   and the saved view.

### Registration and verification

1. `POST /api/auth/register` is rate-limited by IP.
2. Passwords are validated and hashed with PBKDF2-SHA256.
3. If `AUTH_REQUIRE_VERIFIED=1`, the account starts unverified.
4. A single-use token is stored as a SHA-256 hash with a 24-hour expiry.
5. The verification email links to `PUBLIC_APP_URL/?verify_token=...`.
6. The frontend posts the token to `/api/auth/verify-email`; the API
   marks the account verified and creates a revocable session.
7. Without SMTP, `AUTH_DEV_SHOW_TOKENS=1` exposes the token only for
   local development. It must remain disabled publicly.

### Profile onboarding and resume import

1. A new account is prompted to complete its profile automatically.
2. The student can type details or upload PDF/DOCX/TXT (5 MB limit).
3. `resume.py` extracts text in memory; the file is never persisted.
4. Gemini maps only explicit resume facts into profile fields.
5. The frontend pre-fills the editable form; the student reviews and saves.
6. The first successful profile save starts internship/job discovery.

### Login, lockout, and logout

- Five failed passwords lock the account for 15 minutes.
- The password check is performed against a dummy hash for unknown
  accounts to reduce timing differences.
- Successful login resets failed-attempt counters and creates a session
  row.
- Logout marks the session revoked. Reusing the old JWT returns 401.
- Password reset revokes **all** sessions for that user.

### Password reset

1. `POST /api/auth/forgot-password` always returns a generic response.
2. If the account exists, a 30-minute single-use token is emailed.
3. `POST /api/auth/reset-password` validates the new password, marks the
   token used, updates the hash, clears lockout, and revokes sessions.

### Discovery

1. `POST /api/discover` requires a user and is rate-limited per user.
2. `locks.acquire_lock("discovery")` inserts a row with an expiry. The
   unique key makes the lock work across processes sharing the database.
3. A stale lock expires after 20 minutes and can be taken over.
4. Tavily runs profile-aware queries, including official `site:` career
   searches for internships and jobs.
5. Directory, social, and search-result pages are filtered out.
6. Recently attempted URLs are skipped for 14 days, so repeated runs
   move deeper into the result set.
7. Each remaining result is sent to Gemini with strict extraction rules.
8. Gemini returns one JSON record plus evidence snippets.
9. `validator.py` rejects bad URLs, unsupported types, low confidence,
   malformed/past deadlines, training-course listings, and
   social-media-only application links.
10. `dedup.py` removes duplicates by normalized URL or title +
    organization.
11. `storage.py` replaces the opportunity collection in one transaction,
    preserving `created_at` for unchanged source keys.
12. The lock is released in a `finally` block.

### Link verification

1. The user presses **Check links now** in the detail drawer.
2. `POST /api/opportunities/verify` accepts a **stored** source URL only.
3. The request is rate-limited per user.
4. The backend rejects private, loopback, link-local, reserved, and
   multicast hosts after DNS resolution.
5. Redirects are followed manually; every hop is re-checked.
6. The response reports `reachable`, `blocked`, `timeout`, `unreachable`,
   or `invalid`, plus the HTTP status where available.
7. The UI states that a reachable link does not prove the role is open.

This avoids an arbitrary-URL proxy (SSRF) while still giving the user
useful evidence.

## Database schema (version 3)

```sql
opportunities(
  id, source_key UNIQUE, source_url, title, type,
  payload JSON, created_at, updated_at
)

users(
  id, email UNIQUE, password_hash, display_name,
  email_verified, failed_login_attempts, locked_until, created_at
)

user_profiles(
  user_id PRIMARY KEY REFERENCES users(id),
  payload JSON, updated_at
)

user_bookmarks(
  user_id REFERENCES users(id),
  url, created_at,
  PRIMARY KEY(user_id, url)
)

sessions(
  jti PRIMARY KEY, user_id REFERENCES users(id),
  created_at, expires_at, revoked_at
)

auth_tokens(
  token_hash PRIMARY KEY, user_id REFERENCES users(id),
  purpose, created_at, expires_at, used_at
)

rate_limits(limit_key PRIMARY KEY, window_start REAL, count)

discovery_locks(name PRIMARY KEY, owner, acquired_at, expires_at)

discovery_candidates(
  url PRIMARY KEY, category, attempts, last_attempted, outcome
)

application_status(
  user_id REFERENCES users(id),
  opportunity_url, status, note, updated_at,
  PRIMARY KEY(user_id, opportunity_url)
)
```

Legacy tables `profile` and `bookmarks` are read once during migration
into the demo account. `opportunities.json` is imported once when the
database is empty.

## Portability layer

`database.py` wraps SQLite and PostgreSQL behind the same small API:

- `?` placeholders are translated to `%s` for psycopg.
- Rows support `row["column"]` on both backends.
- Transactions commit/rollback through the same context manager.
- Integrity errors become a shared `DatabaseIntegrityError`.
- SQLite pragmas are applied only to SQLite.
- Schema DDL uses backend-specific serial columns.
- `INSERT ... ON CONFLICT` is used instead of SQLite-only syntax.

PostgreSQL integration tests run against a real server in CI and through
`scripts/test_postgres.py` locally.

## Recommendation scoring

`scorer.py` returns a transparent 0–100 relevance score:

- Type (20), interests (35), skills (20), location (15), remote (10),
  extraction confidence (10), normalized by the components that apply.
- Interests and skills expand synonyms (`AI/ML` → artificial
  intelligence / machine learning; `software development` → software
  engineering).
- When a source omits required skills, profile skills are matched against
  the listing title/description, so structured datasets do not unfairly
  lower a strong profile.
- `India` matches Indian cities; `Remote` matches remote listings.
- Scores are relevance estimates, not eligibility decisions.

## Trust boundaries

| Input | Trust level | Handling |
|---|---|---|
| Web search snippets | Untrusted | Prompt-injection warning; facts must be quoted |
| Gemini output | Untrusted | Parsed defensively, validated, confidence threshold |
| Stored URLs | Untrusted | SSRF guard; only stored values may be fetched |
| User profile | Untrusted | Pydantic + dataclass validation, length limits |
| JWT | Untrusted until verified | Signature, expiry, and session row checked |
| Password | Untrusted | Length limits, PBKDF2-SHA256, lockout |
| Email tokens | Untrusted | SHA-256 hashed at rest, single-use, expiring |
| Email HTML | Rendered text | `html.escape` for every dynamic value |
| React UI | Escaped by default | No `dangerouslySetInnerHTML` |

## Authentication design

- Passwords: PBKDF2-HMAC-SHA256, 260,000 iterations, 16-byte salt.
- Tokens: HS256 JWT with `sub`, `email`, `jti`, `iat`, `exp`.
- Sessions: server-side row per login; logout/password reset revokes.
- Verification: 24-hour single-use token.
- Reset: 30-minute single-use token; all sessions revoked.
- Lockout: 5 failures → 15 minutes.
- Rate limits: fixed-window counters in the database, keyed by IP or
  user id. Works across processes sharing the database.
- The demo user has an empty password hash and cannot sign in.
- Auth is opt-in so the project remains easy to demo locally.

## Design trade-offs

**SQLite default, PostgreSQL optional.** SQLite gives zero-setup local
development. PostgreSQL is used when `DATABASE_URL` is set. The adapter
keeps SQL portable without a heavy ORM.

**JSON payload column.** Opportunity fields evolve quickly during AI
experimentation. Storing the full record as JSON avoids a migration for
every prompt change, while indexed columns (`source_key`, `type`) support
lookups.

**On-demand verification.** Checking every link on every dashboard load
would be slow and could trigger rate limits. A manual action keeps the UI
fast and makes the evidence explicit.

**Client-side filtering.** The dataset is small; filtering in React makes
search instant. Server-side pagination is the next step for a large
corpus.

## Known failure modes

- Tavily quota/network failure → discovery returns HTTP 502.
- Gemini refusal or invalid JSON → result skipped, not stored.
- Database locked → SQLite waits up to 5 seconds, then returns an error.
- Expired or revoked JWT → API returns 401 and the UI returns to sign-in.
- Unverified account → login returns 403 until verification completes.
- Email delivery unavailable → registration returns a setup error unless
  development tokens are enabled.
- Verification blocked by a site → reported as `blocked`, not `dead`.
- Multi-worker discovery → prevented by the database lock when workers
  share one database; separate databases require a queue.