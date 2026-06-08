# Deployment Guide

A free-tier-friendly path: **Render** (Docker web service) + **Aiven** (managed MySQL) +
**GitHub Actions** (OWASP ZAP scanning). Any container host + managed MySQL works the same way.

> Provider free tiers change often. Verify current limits and terms on each provider's
> site before relying on them.

---

## 1. Prepare the repository

Push this repo to GitHub (public name suggestion: `security-scanner-platform`). The scan
workflow lives at `.github/workflows/zap-scan.yml` and is triggered via `workflow_dispatch`.

## 2. Database — Aiven MySQL (or any managed MySQL)

1. Create a free **MySQL** service and wait for it to start.
2. Copy the connection details: host, port, user, password, database name.
3. You will set these as `MYSQL_*` env vars on the web service.
4. Create the schema and demo data (run once, from your machine, pointing at the managed DB):

   ```bash
   cd Web_app
   MYSQL_HOST=... MYSQL_PORT=... MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=... \
   FERNET_KEY=... PASSWORD_SALT=... \
   python seed_demo.py
   ```

   `seed_demo.py` creates the tables (idempotent) and seeds demo users + scans.

## 3. Web app — Render Docker service

1. New → **Web Service** → connect the GitHub repo.
2. Environment: **Docker**.
3. **Dockerfile path:** `Web_app/Dockerfile` &nbsp; **Build context:** `Web_app`.
4. **Docker command** (override, so schema/seed runs on deploy):

   ```sh
   sh -c "python seed_demo.py || true && gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 app:app"
   ```

5. **Health check path:** `/healthz`.
6. Add the environment variables (next section). Deploy.

## 4. Environment variables to set on the web service

Required:

```
FLASK_ENV=production
FLASK_SECRET_KEY=<python -c "import secrets;print(secrets.token_hex(32))">
FERNET_KEY=<python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())">
PASSWORD_SALT=<any random string>
MYSQL_HOST=<aiven host>
MYSQL_PORT=<aiven port>
MYSQL_USER=<aiven user>
MYSQL_PASSWORD=<aiven password>
MYSQL_DATABASE=<aiven database>
```

Demo + safety (optional, recommended):

```
DEMO_MODE=true
DEMO_OWNER_PASSWORD=...   DEMO_ADMIN_PASSWORD=...
DEMO_EMPLOYEE_PASSWORD=...   DEMO_READER_PASSWORD=...
SCAN_ALLOWLIST=juice-shop.herokuapp.com,brokencrystals.com,testphp.vulnweb.com,scanme.nmap.org
SCAN_COOLDOWN_SECONDS=120
```

Live scanning via GitHub Actions (optional — the dashboard works without it):

```
GITHUB_TOKEN=<fine-grained PAT: Actions read/write on the repo>
GITHUB_OWNER=<your-github-username>
GITHUB_REPO=security-scanner-platform
GITHUB_WORKFLOW_FILE=zap-scan.yml
GITHUB_REF=main
```

Google OAuth (optional):

```
OAUTH_ID=<google client id>
OAUTH_SECRET=<google client secret>
```

## 5. GitHub Actions setup (live scanning)

1. The repo already contains `.github/workflows/zap-scan.yml`.
2. Create a **fine-grained personal access token** scoped to this repo with
   **Actions: read and write** permission; set it as `GITHUB_TOKEN` on the web service.
3. The app dispatches the workflow with a `target_url`, `scan_name`, and `scan_id`, then
   polls the run and downloads the report artifact to store results in MySQL.
4. Verify the action version (`zaproxy/action-baseline@v0.12.0`) is current and bump if needed.

## 6. Google OAuth redirect URI

In Google Cloud Console → Credentials → your OAuth client → Authorized redirect URIs, add:

```
https://<your-app-domain>/authorize/google
```

The app is `ProxyFix`-aware in production, so redirect URIs resolve to `https` behind
Render's proxy.

## 7. Verify the deployment

- `GET /healthz` → `{"status":"ok"}`
- Open the site → redirected to `/home`.
- Log in at `/login` with a demo account → dashboard shows seeded websites + scans.
- (If GitHub configured) trigger a scan against an allowlisted target and watch the
  run appear in the repo's Actions tab.

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| 500 on every page | DB env vars wrong, or schema not created — run `seed_demo.py`. |
| Dashboard empty | Seed didn't run; re-run `seed_demo.py` against the managed DB. |
| OAuth redirect mismatch | Redirect URI in Google must exactly match `https://<domain>/authorize/google`. |
| Login works then logs out | Use a single worker, or set a stable `FERNET_KEY` (sessions break across workers/restarts without it). |
| Scan stays "queued" | `GITHUB_*` not set, token lacks Actions write, or workflow file name mismatch. |
| First request very slow | Free host spun down on idle — expected cold start. |

## 9. Free-tier limitations

- **Spin-down on idle** → slow cold starts.
- **Ephemeral filesystem** → raw artifacts not persisted; parsed results live in MySQL.
- **Database storage caps** → keep the dataset small.
- **GitHub Actions** → minute and artifact-retention limits on free accounts.
