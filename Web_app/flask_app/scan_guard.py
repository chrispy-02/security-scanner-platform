"""
Scan target safety controls for the public demo.

Prevents SSRF-style abuse (localhost / private IPs / metadata endpoint / non-http
schemes / internal hostnames) and restricts demo users to a configurable allowlist.
Owner/admin roles may scan any externally-resolvable http(s) target that passes the
SSRF checks. Keep this conservative: when in doubt, reject.
"""
import ipaddress
import os
import socket
from urllib.parse import urlparse

# Intentionally-vulnerable / safe demo targets. Override with the SCAN_ALLOWLIST env var.
DEFAULT_ALLOWLIST = "juice-shop.herokuapp.com,brokencrystals.com,testphp.vulnweb.com,scanme.nmap.org"

PRIVILEGED_ROLES = ("owner", "admin")


def allowlist():
    raw = os.getenv("SCAN_ALLOWLIST", DEFAULT_ALLOWLIST)
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def validate_target(url):
    """Return (ok: bool, reason: str). Blocks anything unsafe to scan."""
    if not url or not isinstance(url, str):
        return False, "empty target URL"

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return False, "only http/https URLs are allowed"

    host = parsed.hostname
    if not host:
        return False, "missing host"

    host_l = host.lower()
    if host_l == "localhost" or host_l.endswith(".local") or host_l.endswith(".internal"):
        return False, "internal hostnames are blocked"

    # Resolve every address the host maps to and reject any non-public range.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False, "host does not resolve"

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip_str == "169.254.169.254":
            return False, "cloud metadata endpoint is blocked"
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False, "target resolves to a private/internal address"

    return True, "ok"


def allowed_for_user(url, role):
    """Demo roles may only scan allowlisted hosts; owner/admin bypass the allowlist."""
    if role in PRIVILEGED_ROLES:
        return True
    host = (urlparse(url).hostname or "").lower()
    allowed = allowlist()
    return any(host == a or host.endswith("." + a) for a in allowed)


def check_cooldown(db, user_id):
    """Return (ok: bool, wait_seconds: int). Simple per-user cooldown between scans."""
    seconds = int(os.getenv("SCAN_COOLDOWN_SECONDS", "0") or 0)
    if seconds <= 0:
        return True, 0
    try:
        rows = db.query(
            "SELECT TIMESTAMPDIFF(SECOND, MAX(scan_date), NOW()) AS delta FROM scans WHERE user_id = %s",
            [user_id],
        )
    except Exception:
        return True, 0
    delta = rows[0]["delta"] if rows and rows[0]["delta"] is not None else None
    if delta is None or delta >= seconds:
        return True, 0
    return False, int(seconds - delta)
