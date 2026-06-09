# Security Policy

## Secrets

- **No secrets are committed to this repository.** Configuration is supplied via
  environment variables; see [`.env.example`](.env.example).
- This project began as a private capstone. Any credential that appeared in the original
  history — the GitLab token, Flask secret key, database/OAuth credentials, and the
  application's encryption keys — must be considered **compromised and rotated**:
  - Revoke the old GitLab personal access token.
  - Generate a new `FLASK_SECRET_KEY` and `FERNET_KEY`.
  - Set a fresh `PASSWORD_SALT`.
  - Rotate all database and OAuth credentials.
- A local `.env` is git-ignored. The Docker image never copies `.env` (`.dockerignore`).

## Authorized scanning only

**Only scan systems you own or have explicit written permission to test.** Unauthorized
scanning may be illegal. This tool is for authorized security testing and education.

## Scan-target controls

The scan backend validates every target before dispatching a scan:

- Only `http`/`https` URLs are accepted (no `file:`, `gopher:`, `javascript:`, etc.).
- Targets that resolve to **loopback, private (RFC1918), link-local, reserved,
  multicast, or unspecified** addresses are rejected.
- The **cloud metadata endpoint** (`169.254.169.254`) and internal hostnames
  (`localhost`, `*.local`, `*.internal`) are blocked. This mitigates SSRF.
- Demo (non-privileged) users may only scan hosts on the configurable `SCAN_ALLOWLIST`.
  Owner/admin roles bypass the allowlist but still pass the SSRF checks.
- A per-user cooldown (`SCAN_COOLDOWN_SECONDS`) rate-limits scan triggers.
- Every scan records the initiating user.

## Demo mode caveats

- Demo accounts are intentionally low-impact and operate on synthetic data.
- Registration is open by default; restrict it for a public deployment if desired.
- Demo credentials are configurable via `DEMO_*_PASSWORD` env vars — change them.

## Production hardening included

- Debug is disabled in production (`FLASK_ENV=production`).
- Secure session cookies (`HttpOnly`, `SameSite=Lax`, `Secure` over HTTPS).
- Baseline security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
- `ProxyFix` for correct scheme handling behind a TLS proxy.

## Known limitations (portfolio scope)

- Some legacy routes build SQL with string interpolation. New code uses parameterized
  queries; a full audit/refactor of the inherited routes is out of scope for this
  portfolio version. Do not expose this app to untrusted, unauthenticated input without
  that hardening.
- The inherited password-hashing parameters are weak by modern standards and are kept
  for compatibility; a production deployment should strengthen them.
- A Content-Security-Policy is not enforced (the UI uses inline scripts/styles).

## Responsible disclosure

Found an issue? Please open a private report to the repository maintainer
nguye805@msu.edu rather than filing a public issue with exploit details.
