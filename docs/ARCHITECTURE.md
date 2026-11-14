# Architecture

## System overview

```text
Browser (React + Vite)
   |
   |  same-origin /api (Vite proxy in dev, FastAPI in production)
   v
FastAPI (api.py)
   |-- auth dependency (auth.py) ------------------> users table
   |-- profile service (profile.py) ---------------> user_profiles
   |-- bookmark service (bookmarks.py) ------------> user_bookmarks
   |-- opportunity service (storage.py) -----------> opportunities
   |-- recommendation engine (scorer.py)
   |-- on-demand verification (verification.py) ---> external websites
   |
   v
SQLite (database.py)
```

Discovery is a separate pipeline, callable from the CLI or the API:

```text
search.py (Tavily) -> ai.py (Gemini) -> validator.py -> dedup.py
                                          |              |
                                          v              v
                                  link/date rules     SQLite upsert
```

## Main request flows

### Dashboard load

1. React asks `GET /api/auth/status`.
2. In demo mode, the API resolves every user-scoped request to the demo
   account (id `1`).
3. In auth mode, the browser sends `Authorization: Bearer <jwt>`.
4. The API loads validated opportunities, the user's profile, the user's
   bookmarks, and ranked recommendations.
5. React combines them in memory for search, category filters, sorting,
   and the saved view.

### Discovery

1. `POST /api/discover` requires a user in auth mode.
2. A process-local mutex rejects a concurrent run with HTTP 409.
3. Tavily returns web results for one category.
4. Each result is sent to Gemini with strict extraction rules.
5. Gemini returns one JSON record plus evidence snippets.
6. `validator.py` rejects records with bad URLs, unsupported types, low
   confidence, malformed dates, past deadlines, or social-media-only
   application links.
7. `dedup.py` removes duplicates by normalized URL or title + organization.
8. `storage.py` replaces the opportunity collection in one transaction,
   preserving `created_at` for rows whose source key did not change.

> Note: the current repository `save_opportunities()` replaces the whole
> collection. This is intentional for a single global discovery corpus
> and is protected by a transaction. A row-level upsert API would be the
> next step for multi-worker deployments.

### Link verification

1. The user presses **Check links now** in the detail drawer.
2. `POST /api/opportunities/verify` accepts a **stored** source URL only.
3. The backend rejects private, loopback, link-local, reserved, and
   multicast hosts after DNS resolution.
4. It performs a streamed GET with a short timeout, reading only a small
   prefix of the body.
5. The response reports `reachable`, `blocked`, `timeout`, `unreachable`,
   or `invalid`, plus the HTTP status where available.
6. The UI explicitly states that a reachable link does not prove the role
   is open.

This design avoids an arbitrary-URL proxy (SSRF) while still giving the
user useful evidence.

## Database schema (version 2)

```sql
opportunities(
  id, source_key UNIQUE, source_url, title, type,
  payload JSON, created_at, updated_at
)

users(
  id, email UNIQUE, password_hash, display_name, created_at
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
```

Legacy tables `profile` and `bookmarks` are read once during migration
into the demo account and then left untouched as a rollback aid.
`opportunities.json` is imported once when the database is empty.

## Trust boundaries

| Input | Trust level | Handling |
|---|---|---|
| Web search snippets | Untrusted | Prompt-injection warning; facts must be quoted |
| Gemini output | Untrusted | Parsed defensively, validated, confidence threshold |
| Stored URLs | Untrusted | SSRF guard; only stored values may be fetched |
| User profile | Untrusted | Pydantic + dataclass validation, length limits |
| JWT | Untrusted until verified | Signature + expiry checked, user re-loaded |
| Email HTML | Rendered text | `html.escape` for every dynamic value |
| React UI | Escaped by default | No `dangerouslySetInnerHTML` |

## Authentication design

- Passwords: PBKDF2-HMAC-SHA256, 260,000 iterations, 16-byte salt.
- Tokens: HS256 JWT with `sub`, `email`, `iat`, `exp`; 7-day default.
- No refresh tokens; signing out clears the client token. Tokens cannot
  be revoked server-side yet, so a short lifetime is recommended for a
  public deployment.
- The demo user has an empty password hash and cannot sign in.
- Auth is opt-in so the project remains easy to demo locally.

## Design trade-offs

**SQLite over PostgreSQL.** Zero setup, transactional, and adequate for a
single portfolio instance. The repository layer isolates SQL so a
PostgreSQL adapter can replace it later.

**JSON payload column.** Opportunity fields evolve quickly during AI
experimentation. Storing the full record as JSON avoids a migration for
every prompt change, while indexed columns (`source_key`, `type`) support
lookups. A normalized table is a future optimization.

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
- Expired JWT → API returns 401 and the UI returns to sign-in.
- Verification blocked by a site → reported as `blocked`, not `dead`.
- Multi-worker discovery → the in-process mutex does not coordinate
  across processes. Use a queue or database lock before scaling out.