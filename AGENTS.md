# Maintenance rules for this repository

These rules keep the published documentation in sync with the code.

## Definition of done

A change is not complete until:

1. **`README.md` is updated** when the change affects:
   - features or user-facing behavior
   - setup or run commands
   - API endpoints
   - environment variables
   - test counts
   - deployment or live feed
   - known limitations
2. **`docs/CHANGELOG.md` is updated** with a dated bullet.
3. **`docs/ARCHITECTURE.md`** is updated when data flow, schema, auth,
   discovery, or infrastructure changes.
4. **`docs/PRODUCT.md`** is updated when product features or the
   Unstop/Internshala comparison change.
5. **`docs/INTERVIEW.md`** is updated when the story, metrics, or code
   tour changes.

## README checklist

- [ ] Feature list matches what the app actually does.
- [ ] Commands still work (backend, frontend, tests, curated import).
- [ ] Test counts match `pytest` and the PostgreSQL suite.
- [ ] Live URL and current feed counts are accurate.
- [ ] Limitations are honest and current.
- [ ] "Last updated" date is changed.

## Test commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\scripts\test_postgres.py
cd frontend; & F:\Tools\nodejs\npm.cmd run lint; & F:\Tools\nodejs\npm.cmd run build
```

## Commit checklist

- [ ] Tests pass.
- [ ] README/CHANGELOG updated when relevant.
- [ ] No secrets committed (`.env`, `profile.json`, `bookmarks.json`, DB).
- [ ] Render deploy triggered if the live app changed.
- [ ] CI is green.