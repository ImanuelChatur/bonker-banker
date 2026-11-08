# Overnight log

Branch `overnight`, cut from `main` at `85318eb` ("Open sign-up: anyone can register at /register").
Times are America/Toronto.

| Time | What | Commit | Decision / why |
| :-- | :-- | :-- | :-- |
| 00:01 | Setup: fetched, `main` up to date, created and pushed `overnight`. `origin/main` = `85318eb`. | – | The uncommitted `.gitignore` change (a trailing newline) and the untracked `.mcp.json` are left out of every commit. |
| 00:02 | Starting state: 112 tests pass. Data present in `data/raw/` and `data/processed/`. No `CLAUDE.md` in the repo. | – | – |
| 00:03 | Read the routes, templates and CSS. | – | **Login decision:** the login is real password auth (users DB with hashed passwords, CSRF, lockout, open sign-up), added on purpose for hosting. Replacing it with a fake "demo sign-in" would remove the protection a teammate asked for, so I keep it and add a customer/advisor role choice to the login and sign-up forms instead (Priority 2). Locally `BB_AUTH=off` skips it entirely. |
