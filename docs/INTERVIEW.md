# Interview and demo guide

This document is a study aid for presenting Opportunity Agent in a
software engineering or AI/ML placement interview.

## 60-second pitch

> Opportunity Agent is a full-stack AI platform that discovers student
> opportunities from the web, extracts structured records with Gemini,
> validates them, stores them in SQLite, and ranks them against a
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
7. **Tests** — run `pytest`, mention 55 tests and the Playwright flows.
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
- SQLite with WAL, transactions, and unique keys.
- The legacy JSON files are imported once, so the original project's
  data was not discarded.
- Per-user tables avoid the common portfolio mistake of one global
  profile/bookmark list.

### 5. Authentication without over-engineering
- Optional JWT mode keeps local demos frictionless.
- PBKDF2-SHA256 with random salt avoids a heavyweight dependency.
- Every user-scoped query includes `user_id`.
- Tests prove Alice cannot read Bob's bookmarks or profile.

## Likely questions and answers

**Why not use LangChain?**
The pipeline is small and explicit: search → extract → validate →
deduplicate → store. A framework would hide the data-quality decisions
that matter most here. The current code is easier to test and debug.

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

**Why SQLite?**
It gives real transactions and migrations with zero infrastructure. The
repository layer isolates SQL, and the schema is ready to move to
PostgreSQL when there are multiple writers. The current discovery mutex
is per process, which is an honest limitation.

**How is user data isolated?**
JWTs identify the user; every profile/bookmark query uses the authenticated
user id. API tests create two users and assert cross-account reads fail.

**What would you do before real production?**
Rate limiting, email verification, password reset, refresh-token
revocation, PostgreSQL, a distributed discovery lock/queue, observability,
and provider-cost limits.

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
| Validation rules | `validator.py` |
| Link checks / SSRF guard | `verification.py` |
| Ranking | `scorer.py` |
| React shell | `frontend/src/App.jsx` |
| Auth UI | `frontend/src/AuthScreen.jsx` |
| Detail/evidence UI | `frontend/src/OpportunityDetail.jsx` |

## Metrics to quote accurately

- 55 automated backend/API tests.
- 2 Playwright browser flows (bookmarks/detail, auth/profile).
- 7 opportunity categories.
- 6 scoring components with transparent reasons.
- 2 storage layers during migration: legacy JSON → SQLite (version 2 schema).

Avoid quoting user numbers or deployment traffic; the project has not
been publicly deployed yet.