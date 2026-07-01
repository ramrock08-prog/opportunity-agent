<div align="center">

# 🚁 UAV Drone Scout
### An autonomous AI agent that hunts down UAV/drone hackathons across India — so you never miss a deadline again.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-4285F4?logo=google&logoColor=white)
![Tavily](https://img.shields.io/badge/Search-Tavily%20API-orange)
![GitHub Actions](https://img.shields.io/badge/Automation-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

**Zero manual searching. Zero stale listings. Zero missed deadlines.**

</div>

---

## 💡 The Problem

Hackathon and competition announcements for UAV/drone teams are scattered across dozens of platforms — Unstop, university sites, MeitY portals, Devpost, random tweets. By the time a student finds out, registration is often already closed. There's no single place that filters *just* the relevant, *currently open*, India-based UAV competitions.

## 🎯 The Solution

**UAV Drone Scout** is a fully autonomous agent that runs itself on a schedule, searches the web, uses an LLM to intelligently filter noise, cross-checks every claim with a hard rule-based safety net, verifies every link is actually alive, and emails a clean digest — all without a human touching it.

No dashboards to check. No tabs to keep open. It comes to you.

---

## ✨ Key Features

| Feature | Why it matters |
|---|---|
| 🔁 **Fully autonomous** | Runs every 7 hours via GitHub Actions — no server, no manual runs needed |
| 🧠 **AI-powered filtering** | Gemini 2.5 Flash reads raw search noise and extracts only genuine, relevant events |
| 🛡️ **Dual-layer validation** | A rule-based Python safety net double-checks every AI decision against 9 hard filters, so hallucinated or stale results can't slip through |
| 🔗 **Live link verification** | Every registration link is pinged in real time — dead links never reach your inbox |
| 🧠 **Persistent memory** | Tracks previously seen events in `hackathons.json` so you're never spammed with repeats |
| 📧 **Polished email digest** | Auto-generated HTML report, split into "🔥 New" and "📌 Tracked", ready to read on mobile |
| ⚙️ **Zero infrastructure cost** | Runs entirely on GitHub Actions' free tier — no servers, no hosting bills |

---

## 🏗️ System Architecture

```
                ┌─────────────────────┐
                │   GitHub Actions     │
                │  (cron: every 7 hrs) │
                └──────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   Tavily Search API  │  ← 5 targeted queries
                │  (raw web results)   │
                └──────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Gemini 2.5 Flash    │  ← AI classification
                │  (9 strict rules)    │
                └──────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Hard Date Safety Net │  ← Pure Python re-check
                │  (no AI, no trust)   │
                └──────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Live Link Checker   │  ← Real HTTP verification
                └──────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  hackathons.json     │  ← Persistent memory
                │  (committed to repo) │
                └──────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   Gmail SMTP Email   │  ← Final digest
                └─────────────────────┘
```

---

## 🛠️ Tech Stack

- **Language:** Python 3.11
- **AI Model:** Google Gemini 2.5 Flash Lite (`google-genai` SDK)
- **Search Engine:** Tavily Search API
- **Automation:** GitHub Actions (cron scheduling + auto-commit memory)
- **Delivery:** Gmail SMTP (HTML email)
- **Storage:** Git-committed JSON (no external database required)

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/uav-drone-scout.git
cd uav-drone-scout
```

### 2. Get your API keys
| Secret | Source |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |
| `TAVILY_API_KEY` | [Tavily](https://tavily.com) |
| `SENDER_EMAIL` | Your Gmail address |
| `SENDER_PASSWORD` | A Gmail **App Password** (requires 2FA) |
| `RECEIVER_EMAIL` | Where the digest should land |

### 3. Add them as GitHub Secrets
`Settings → Secrets and variables → Actions → New repository secret`

### 4. Let it run
The workflow fires automatically every 7 hours — or trigger it instantly from the **Actions** tab.

### 5. Run locally (optional)
```bash
pip install -r requirements.txt
export GEMINI_API_KEY=... TAVILY_API_KEY=... SENDER_EMAIL=... SENDER_PASSWORD=... RECEIVER_EMAIL=...
python agent.py
```

---

## 📸 Sample Output

<img width="1917" height="1012" alt="image" src="https://github.com/user-attachments/assets/e502a4f9-d9df-4813-8012-f5f9fc0632e6" />
<img width="1908" height="923" alt="image" src="https://github.com/user-attachments/assets/8d7b709f-9bb8-4771-b03a-5c0c643a4040" />


---

## 🔮 Roadmap

- [ ] Expand beyond UAV to other robotics/aerospace competitions
- [ ] Add Telegram/WhatsApp delivery as an alternative to email
- [ ] Web dashboard to browse tracked hackathons instead of only email
- [ ] Multi-country support (currently India-only by design)
- [ ] Retry/backoff logic for API rate limits

---

## 👤 Author

Built solo as a personal automation project — combining web search, LLM reasoning, and CI/CD scheduling into one self-sufficient pipeline.
