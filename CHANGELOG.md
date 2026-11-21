# Changelog

All notable changes to Opportunity Agent are recorded here. The README
and this changelog are updated together for every change.

## 2026-11-21

- Added a **location filter** (for example `India`, `Bengaluru`, `Remote`)
  to the advanced filter panel.
- Imported structured open-source internship datasets:
  **17,000+ listings scanned**, filtered for India/remote, producing
  **193 internships** live (198 records total).
- Added the **Apply flow**: saved contact details, one-click copy of an
  application kit, opens the official application page, and marks the
  opportunity as applied.
- Added profile contact fields: phone, college, graduation year, GitHub,
  LinkedIn, and portfolio.
- Added a **⤓ Sync curated internships** dashboard action.
- Added **application tracker** with Interested / Applied / Interview /
  Offer / Rejected stages and private notes.
- Added **skill match / skill gaps**, **similar opportunities**, and a
  **closing within 7 days** radar.
- Added a **keep-alive** GitHub Actions workflow to reduce Render cold
  starts.
- Fixed the scheduled discovery workflow so it skips cleanly without
  secrets, and configured the Gemini/Tavily action secrets.

### Changed (same day)
- Recommendation scoring now expands synonyms such as `AI/ML` →
  artificial intelligence / machine learning, matches skills against the
  listing text when a source omits required skills, and treats
  `India`/`Remote` preferences more accurately. This raises realistic
  match scores for AI, software, and forward-deployed engineering roles.

## 2026-11-15

- Added the **application tracker** (Interested / Applied / Interview /
  Offer / Rejected) with private notes and an Applications view.
- Added advanced filters: work mode, deadline window, stipend/prize
  listed, and matches-my-skills.
- Added a **closing within 7 days** radar.
- Added **skill match / skill gaps**, **similar opportunities**, and
  **share link** to the detail drawer.
- Added a keep-alive workflow and made scheduled discovery skip cleanly
  when secrets are missing.
- Discovery became profile-aware and can process up to 10 Gemini
  extractions per run.

## 2026-11-14

- Deployed publicly on Render with PostgreSQL.
- Added advanced filters, sorting, bookmark counts, and the details
  drawer.
- Added resume/CV onboarding (PDF, DOCX, TXT) with Gemini extraction.
- Added automatic first-run internship/job discovery.
- Added optional email verification, password reset, account lockout,
  revocable sessions, and database-backed rate limits.
- Added a PostgreSQL adapter and integration tests beside SQLite.
- Added candidate history so repeated discovery runs keep finding new
  listings.
- Added deployment docs, architecture docs, an interview guide, and
  product research notes.

## 2026-11-13

- Added evidence-based Gemini extraction (verbatim evidence and deadline
  evidence), on-demand link verification, and SSRF protection.
- Added the React dashboard, bookmarks, profile editor, search, filters,
  sorting, and the opportunity detail drawer.
- Renamed and expanded the original drone-hackathon scout into
  Opportunity Agent.

## 2026-11-10

- Added SQLite persistence with automatic JSON migration.
- Added on-demand link verification with SSRF protection.
- Added evidence snippets and deadline-evidence rules.
- Added the React details drawer and saved-opportunity flows.
- Added the email digest and generalized GitHub Actions discovery.
