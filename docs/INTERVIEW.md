# Interview and demo guide

This document is a study aid for presenting Opportunity Agent in a
software engineering or AI/ML placement interview.

## 60-second pitch

> Opportunity Agent is a full-stack AI platform that discovers student
> opportunities from the web, extracts structured records with Gemini,
> validates them, stores them in SQLite or PostgreSQL, and ranks them against a
> personal profile. The hard part is not calling an LLM — it is refusing
> to trust it. I added evidence snippets, deadline-evidence rules, an
> honest link checker, deduplication, and per-user data isolation.

## Demo script (5 minutes)

1. **Dashboard** — show search, category filters, sorting, saved count.
2. **Detail drawer** — show eligibility, skills, evidence, source and
   application links.
3. **Link check** — click **Check links now**. Point out that a reachable
   response is explicitly *not* presented as "open".
4. **Save flow** — save a card, refresh the page, open Saved, remove it.
5. **Profile** — change a skill or interest, save, and show the
   recommendation score/reasons changing.
6. **API docs** — open `/docs`, mention validation and auth dependencies.
7. **Tests** — run `pytest`, mention 98 tests and the Playwright flows.
8. **Architecture** — open `docs/ARCHITECTURE.md`; discuss trust
   boundaries and SQLite trade-offs.

Do not trigger live discovery during a short interview unless the
interviewer asks; it spends Tavily/Gemini credits and takes time.

## Key engineering decisions

### 1. LLM output is untrusted input
- The extraction prompt forbids inferred deadlines and unsupported facts.
- Every stored fact can carry a verbatim evidence snippet.
- Pydantic/dataclass validation and a confidence threshold run outside
  the model.
- The app never labels a record "verified open".

### 2. Link verification is evidence, not proof
- Checks run on demand to avoid slowing the dashboard.
- Statuses distinguish `reachable`, `blocked` (401/403/429), `timeout`,
  and `unreachable`.
- Only stored URLs are fetched, and redirects are re-checked at every
  hop to reduce SSRF.
- A 200 response is described as reachability only.

### 3. Transparent recommendation scoring
- Type, interests, skills, location, remote preference, and extraction
  confidence are separate components.
- The API returns the component values and human-readable reasons.
- Scores are normalized 0–100 and explicitly not eligibility decisions.

### 4. Persistence and migration
- SQLite by default; PostgreSQL through `DATABASE_URL`.
- A thin adapter translates placeholders, rows, transactions, and
  integrity errors for both backends.
- The legacy JSON files are imported once, so the original project's
  data was not discarded.
- Schema version 3 adds sessions, auth tokens, rate limits, and a
  cross-process discovery lock.
- Per-user tables avoid the common portfolio mistake of one global
  profile/bookmark list.

### 5. Authentication without over-engineering
- Optional JWT mode keeps local demos frictionless.
- Passwords use PBKDF2-SHA256 with random salts.
- Sessions are server-side rows, so logout and password reset revoke
  tokens immediately.
- Email verification and reset tokens are hashed, single-use, and
  expiring.
- Five failed logins trigger a 15-minute lockout.
- Database-backed rate limits protect registration, login, reset,
  discovery, and link checks.
- Every user-scoped query includes `user_id`; tests prove Alice cannot
  read Bob's bookmarks or profile.

## Likely questions and answers

**Why not use LangChain?**
The pipeline is small and explicit: search → extract → validate →
deduplicate → store. A framework would hide the data-quality decisions
that matter most here. The current code is easier to test and debug.

**Why did the first version find so few internships?**
The pipeline was only sending 2–3 Tavily results to Gemini per run.
Now it builds profile-aware queries (skills/interests), searches official
career sites, filters directories, processes up to 10 results, and skips
recently attempted URLs so repeated runs keep finding new listings.

**How do you stop hallucinations?**
Multiple layers: strict prompt rules, evidence-only extraction,
null-for-unknown, confidence threshold, rule-based URL/date validation,
and a UI that separates extraction confidence from verification.

**What happens if Gemini returns invalid JSON?**
`ai.py` catches parse/type errors and returns `None`; the pipeline skips
that result rather than writing a malformed record. The discovery run
continues.

**How do you handle prompt injection from web pages?**
Page content is labeled untrusted in the prompt, the model is told not
to follow embedded instructions, and output is parsed as data — never
executed. The model also cannot run tools in this pipeline.

**Why SQLite, and why PostgreSQL too?**
SQLite gives real transactions and migrations with zero infrastructure.
PostgreSQL is available through `DATABASE_URL` when concurrency grows.
The same adapter and integration tests cover both; the discovery lock is
in the database, so it works across processes, not just threads.

**How is user data isolated?**
JWTs identify the user; every profile/bookmark query uses the authenticated
user id. API tests create two users and assert cross-account reads fail.

**What would you do before real production?**
Rate limiting, verification, reset, lockout, revocation, PostgreSQL, and
a cross-process lock are implemented. Remaining work: MFA, an admin
console, observability/alerting, email deliverability monitoring, a
managed queue for discovery at larger scale, and stronger cost controls.

**What was the hardest bug?**
A Gemini result pointing at an Instagram post with an invented deadline.
The fix was not just a validator rule; it was changing the extraction
contract so a deadline requires a quotable source snippet and social-media
application links are rejected.

**What is not solved?**
Search snippets can be stale or incomplete; a live page can change after
extraction; eligibility is often stated in PDFs the snippet never
contains. The product communicates this uncertainty instead of hiding it.

## Code tour

| Concern | File |
|---|---|
| HTTP routes and auth dependency | `api.py` |
| Password/JWT logic | `auth.py` |
| Schema, migration, demo account | `database.py` |
| Opportunity repository | `storage.py` |
| Per-user bookmarks/profile | `bookmarks.py`, `profile.py` |
| Gemini prompt and parsing | `ai.py` |
| Resume text extraction | `resume.py` |
| Validation rules | `validator.py` |
| Link checks / SSRF guard | `verification.py` |
| Ranking | `scorer.py` |
| React shell | `frontend/src/App.jsx` |
| Auth UI | `frontend/src/AuthScreen.jsx` |
| Detail/evidence UI | `frontend/src/OpportunityDetail.jsx` |

## Metrics to quote accurately

- 98 automated tests: 94 SQLite + 4 PostgreSQL integration tests.
- 2 Playwright browser flows (bookmarks/detail, verification/reset/profile).
- 7 opportunity categories.
- 6 scoring components with transparent reasons.
- Storage migration: legacy JSON → SQLite/PostgreSQL (schema version 3).
- Security controls: PBKDF2, revocable sessions, verification, reset,
  lockout, rate limits, SSRF guard.
- Product features: resume onboarding, deep discovery, advanced filters,
  application tracker, skill gaps, deadline radar, similar opportunities.

Avoid quoting user numbers or deployment traffic; the project has not
been publicly deployed yet.