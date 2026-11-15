# Product research: Unstop and Internshala

This document records what the two reference platforms do well, and what
Opportunity Agent deliberately implements differently.

## What Unstop does well

- Aggregates many opportunity types: internships, jobs, hackathons,
  competitions, quizzes, scholarships, workshops, and festivals.
- Strong category navigation and filter bars for location and timeline.
- AI-assisted recommendations and talent sourcing.
- Organizer/hiring-challenge workflows, registrations, and dashboards.
- Large, frequently updated inventory.

## What Internshala does well

- Internship/job search with filters for duration, location, work mode
  (work-from-home/in-office), field, and stipend.
- Daily posting cadence, saved alerts, and application flows.
- Resume/profile creation and employer-facing application management.
- Clear stipend and duration labels on listing cards.
- Mobile-first discovery and “work from home” collections.

## Features added to Opportunity Agent (original versions)

| Feature | Our implementation |
|---|---|
| Rich filtering | Category + work mode + deadline window + stipend listed + “matches my skills” |
| Deadline visibility | “Closing within 7 days” radar and deadline sort |
| Application tracking | Interested / Applied / Interview / Offer / Rejected with private notes |
| Personalized discovery | Profile-aware queries from skills, interests, degree, branch |
| Resume onboarding | PDF/DOCX/TXT upload → AI-prefilled profile, reviewed before saving |
| Skill fit | Per-listing skill match and skill-gap comparison |
| Similar opportunities | Same type or shared skills inside the detail drawer |
| Saved opportunities | Private bookmarks with count and dedicated view |
| Deep search | Official-career `site:` queries, directory filtering, candidate history |
| Data honesty | Evidence snippets, deadline evidence, link checks, “not verified open” wording |
| Reliability | Database candidate history, rate limits, cross-process lock, keep-alive |

## What we intentionally do not copy

- **Directory spam:** Unstop/Internshala list many third-party postings.
  Opportunity Agent prefers one specific official source page.
- **Pay-to-rank or promoted listings:** ranking is profile relevance, not
  advertising.
- **Fake “verified/open” badges:** we report link reachability and
  extraction confidence separately.
- **Employer portal / organizer dashboards:** out of scope for this
  student-focused portfolio release.
- **Courses and training sales:** training/course listings are rejected.
- **Hundreds of low-quality records:** we prefer validated records with
  source provenance, even if the inventory is smaller.

## Product direction

The goal is not to become a listing directory. It is a **trust-first
opportunity agent**:

1. Understand the student through profile + resume.
2. Search broadly but filter aggressively.
3. Explain why a listing matches.
4. Show provenance and uncertainty.
5. Help the student act (save, track, compare skills, apply).