# Changelog

All notable changes to Opportunity Agent are recorded here. The README and
this file must be updated together whenever the project changes.

## 2026-11-21

### Added
- **Curated internship import** (`curated.py`): reads maintained
  open-source internship datasets (SimplifyJobs, vanshb03 — 17,000+
  listings), filters them for India/remote, ranks them against the
  profile, deduplicates, and stores them. Exposed as
  `POST /api/discover/curated` and the **Sync curated internships**
  dashboard button, and as `scripts/import_curated.py`.
- **One-click Apply flow** (`frontend/src/ApplyModal.jsx`): saves name,
  phone, college, graduation year, GitHub, LinkedIn, and portfolio to the
  profile; shows a complete copy-ready application kit; opens the official
  application page; marks the opportunity as **Applied**.
- **Location filter** in the advanced filter panel.
- `AGENTS.md` maintenance checklist so documentation stays current.

### Changed
- Live feed grew from 29 records to **198 records** (193 internships,
  3 jobs, 1 scholarship, 1 fellowship).
- README feature list, live feed counts, and documentation rules updated.

## 2026-11-15

### Added
- **Application tracker** (`application_tracker.py`): Interested, Applied,
  Interview, Offer, Rejected, with private notes and an Applications view.
- **Advanced filters**: work mode, deadline window, stipend/prize listed,
  matches-my-skills.
- **Closing within 7 days** dashboard radar.
- **Skill match and skill gaps** in the opportunity detail drawer.
- **Similar opportunities** and **Share** in the detail drawer.
- **Keep-alive workflow** so the free Render instance stays awake.
- Scheduled discovery workflow now skips cleanly when secrets are absent.

### Changed
- Discovery is profile-aware and can process up to 10 Gemini extractions
  per run.
- Scheduled discovery secrets were configured in GitHub Actions.

## 2026-11-14

### Added
- Public Render deployment with Render PostgreSQL (Oregon).
- Resume/CV onboarding (PDF, DOCX, TXT) with Gemini profile extraction.
- Automatic internship/job discovery after the first profile save.
- First-run profile onboarding; first visit defaults to Create account.
- SQLite/PostgreSQL adapter with schema migrations.
- JWT sessions, email verification, password reset, lockout, rate limits.
- Scheduled discovery and email digest workflows.
- Docker, Docker Compose, Render blueprint, and deployment docs.

### Changed
- Legacy JSON storage migrated automatically into the database.
- Repository published publicly; the old drone scout repository was
  removed and its dead links cleaned from the README.

## 2026-11-13

### Added
- Evidence-based Gemini extraction (verbatim evidence and deadline
  evidence), on-demand link verification, SSRF protection.
- React dashboard with bookmarks, detail drawer, profile editor.
- Opportunity detail pages, saved view, search, filters, sorting.

### Changed
- Project renamed and expanded from a drone-hackathon scout into
  Opportunity Agent.