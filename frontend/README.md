# Opportunity Agent — frontend

React 19 + Vite frontend for the Opportunity Agent platform.

## Run locally

Start the FastAPI backend on port 8000 first, then:

```powershell
cd F:\opportunity-agent\frontend
& F:\Tools\nodejs\npm.cmd install
& F:\Tools\nodejs\npm.cmd run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to
`http://127.0.0.1:8000`, so the browser uses same-origin requests and no
CORS configuration is needed for development.

## Build

```powershell
& F:\Tools\nodejs\npm.cmd run build
& F:\Tools\nodejs\npm.cmd run lint
```

The production files are written to `dist/`. FastAPI serves them when
`SERVE_FRONTEND=1`; otherwise deploy `dist/` to a static host and set
`VITE_API_BASE` at build time.

## Structure

| File | Purpose |
|---|---|
| `src/App.jsx` | Dashboard shell, data loading, filters, navigation |
| `src/AuthScreen.jsx` | Sign-in and registration |
| `src/OpportunityCard.jsx` | Opportunity card + save action |
| `src/OpportunityDetail.jsx` | Detail drawer, evidence, link check |
| `src/ProfileEditor.jsx` | Profile form |
| `src/api.js` | API base, token storage, fetch helpers |
| `src/utils.js` | Date, deadline, host, and URL helpers |

## Authentication

The app first calls `/api/auth/status`:

- **Demo mode** (`AUTH_REQUIRED=0`): the dashboard opens directly and the
  backend uses the local demo account.
- **Auth mode** (`AUTH_REQUIRED=1`): the sign-in screen is shown. The JWT
  is stored in `localStorage` and attached to `/api` requests.

The frontend never receives Gemini, Tavily, or Gmail credentials.

## Notes

- Use `npm.cmd` on this Windows machine because the PowerShell `npm`
  wrapper is blocked by execution policy.
- Node 24 / npm 11 are installed at `F:\Tools\nodejs`.
- Browser tests live in `../scripts/e2e_bookmarks.py` and
  `../scripts/e2e_auth.py`.