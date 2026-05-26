"""
GitHub Actions scan backend.

Replaces the original MSU GitLab pipeline integration. Important properties:
  * NO network calls at import time (the app must boot without any scan backend).
  * If GitHub env vars are not configured, scanning is disabled gracefully and the
    app still serves the dashboard from data already stored in MySQL.
  * Raw scan artifacts are parsed in a temp dir and the results are persisted to
    MySQL, so nothing depends on the local filesystem surviving (Render free tier
    has an ephemeral disk).

Env vars: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_WORKFLOW_FILE, GITHUB_REF.
"""
import io
import os
import re
import sys
import tempfile
import zipfile

import requests
from flask import jsonify

# Make the sibling flask_app modules importable regardless of import order.
_FLASK_APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flask_app")
if _FLASK_APP_DIR not in sys.path:
    sys.path.insert(0, _FLASK_APP_DIR)

from scan_guard import validate_target, allowed_for_user, check_cooldown  # noqa: E402
from scan_parse import process_report  # noqa: E402

GITHUB_API = "https://api.github.com"
_TIMEOUT = 25


# ──────────────────────────────────────────────────────────────────────────────
# Config / helpers
# ──────────────────────────────────────────────────────────────────────────────
def _gh_config():
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    if token and owner and repo:
        return {
            "token": token,
            "owner": owner,
            "repo": repo,
            "workflow": os.getenv("GITHUB_WORKFLOW_FILE", "zap-scan.yml"),
            "ref": os.getenv("GITHUB_REF", "main"),
        }
    return None


def scanning_enabled():
    return _gh_config() is not None


def _headers(cfg):
    return {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _user_role(db, user_id):
    try:
        return db.query("SELECT role FROM users WHERE user_id = %s", [user_id])[0]["role"]
    except Exception:
        return "reader"


def _resolve_run(cfg, scan_id):
    """Best-effort: find the workflow run created by our dispatch (matched by run-name)."""
    try:
        url = (f"{GITHUB_API}/repos/{cfg['owner']}/{cfg['repo']}/actions/workflows/"
               f"{cfg['workflow']}/runs?event=workflow_dispatch&per_page=20")
        r = requests.get(url, headers=_headers(cfg), timeout=_TIMEOUT)
        if r.status_code != 200:
            return None, None
        # Match the exact "#<scan_id>" token so #1 doesn't also match #10/#100.
        pat = re.compile(rf"#{scan_id}(?!\d)")
        for run in r.json().get("workflow_runs", []):
            label = f"{run.get('name', '')} {run.get('display_title', '')}"
            if pat.search(label):
                return run["id"], run.get("html_url")
    except requests.RequestException:
        pass
    return None, None


# ──────────────────────────────────────────────────────────────────────────────
# Public API (consumed by routes.py and scheduler.py)
# ──────────────────────────────────────────────────────────────────────────────
def run_scan(scan_name, scan_url, website_id, db, user_id):
    """Validate, then dispatch a ZAP scan via GitHub Actions. Records the scan in MySQL."""
    ok, reason = validate_target(scan_url)
    if not ok:
        return jsonify({"error": f"Invalid scan target: {reason}"}), 400

    role = _user_role(db, user_id)
    if not allowed_for_user(scan_url, role):
        return jsonify({
            "error": "This target is not in the demo allowlist. Demo users may only scan "
                     "approved test targets. Configure SCAN_ALLOWLIST to allow more."
        }), 403

    cool_ok, wait = check_cooldown(db, user_id)
    if not cool_ok:
        return jsonify({"error": f"Please wait {wait}s before starting another scan."}), 429

    cfg = _gh_config()
    initial_status = "queued" if cfg else "disabled"

    columns = ["user_id", "scan_name", "website_url", "status", "high_risks", "medium_risks",
               "low_risks", "informational_risks", "report_url", "pipeline_id", "website_id"]
    values = [[user_id, scan_name, scan_url, initial_status, 0, 0, 0, 0, None, None, website_id]]
    try:
        scan_id = db.insertRows(table="scans", columns=columns, parameters=values)
    except Exception as e:
        return jsonify({"error": f"Error inserting scan data: {str(e)}"}), 500

    if not cfg:
        return jsonify({
            "message": "Scan recorded, but live scanning is disabled (no GitHub backend configured).",
            "scan_id": scan_id,
            "status": initial_status,
        }), 200

    try:
        dispatch_url = (f"{GITHUB_API}/repos/{cfg['owner']}/{cfg['repo']}/actions/workflows/"
                        f"{cfg['workflow']}/dispatches")
        payload = {"ref": cfg["ref"], "inputs": {
            "target_url": scan_url,
            "scan_name": str(scan_name),
            "scan_id": str(scan_id),
        }}
        resp = requests.post(dispatch_url, headers=_headers(cfg), json=payload, timeout=_TIMEOUT)
        if resp.status_code not in (201, 204):
            db.query("UPDATE scans SET status = %s WHERE scan_id = %s", ["failed", scan_id])
            return jsonify({"error": f"Failed to dispatch scan workflow (HTTP {resp.status_code})."}), 502
    except requests.RequestException as e:
        db.query("UPDATE scans SET status = %s WHERE scan_id = %s", ["failed", scan_id])
        return jsonify({"error": f"Scan dispatch error: {str(e)}"}), 502

    run_id, report_url = _resolve_run(cfg, scan_id)
    if run_id:
        db.query("UPDATE scans SET pipeline_id = %s, report_url = %s, status = %s WHERE scan_id = %s",
                 [run_id, report_url, "running", scan_id])

    return jsonify({
        "message": "Scan triggered successfully",
        "scan_id": scan_id,
        "run_id": run_id,
        "status": "running",
    }), 200


def refresh_scan_status(scan, db):
    """Poll a single scan's GitHub run; on success download + parse artifacts into MySQL."""
    cfg = _gh_config()
    if not cfg:
        return scan.get("status")

    scan_id = scan["scan_id"]
    run_id = scan.get("pipeline_id")
    if not run_id:
        run_id, report_url = _resolve_run(cfg, scan_id)
        if not run_id:
            return scan.get("status")
        db.query("UPDATE scans SET pipeline_id = %s, report_url = %s WHERE scan_id = %s",
                 [run_id, report_url, scan_id])

    try:
        r = requests.get(f"{GITHUB_API}/repos/{cfg['owner']}/{cfg['repo']}/actions/runs/{run_id}",
                         headers=_headers(cfg), timeout=_TIMEOUT)
        if r.status_code != 200:
            return scan.get("status")
        run = r.json()
    except requests.RequestException:
        return scan.get("status")

    if run.get("status") != "completed":
        db.query("UPDATE scans SET status = %s WHERE scan_id = %s", ["running", scan_id])
        return "running"

    if run.get("conclusion") != "success":
        db.query("UPDATE scans SET status = %s WHERE scan_id = %s", ["failed", scan_id])
        return "failed"

    _ingest_artifacts(cfg, run_id, scan_id, db)
    return "success"


def _ingest_artifacts(cfg, run_id, scan_id, db):
    """Download the run's artifact zip, extract scan.json, parse, and persist to MySQL."""
    try:
        arts = requests.get(
            f"{GITHUB_API}/repos/{cfg['owner']}/{cfg['repo']}/actions/runs/{run_id}/artifacts",
            headers=_headers(cfg), timeout=_TIMEOUT,
        ).json().get("artifacts", [])
        if not arts:
            db.query("UPDATE scans SET status = %s WHERE scan_id = %s", ["success", scan_id])
            return

        zip_resp = requests.get(arts[0]["archive_download_url"], headers=_headers(cfg), timeout=_TIMEOUT)
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                json_name = next((n for n in zf.namelist() if n.endswith(".json")), None)
                if not json_name:
                    db.query("UPDATE scans SET status = %s WHERE scan_id = %s", ["success", scan_id])
                    return
                json_path = os.path.join(tmp, os.path.basename(json_name))
                with zf.open(json_name) as src, open(json_path, "wb") as dst:
                    dst.write(src.read())

            values, vuln_counts, unique_urls = process_report(json_path, tmp, scan_id)

        if unique_urls:
            db.insertRows(table="scanned_websites", columns=["scan_id", "website_url"],
                          parameters=[[scan_id, u] for u in unique_urls])

        high, medium, low, info, host = values
        db.query(
            "UPDATE scans SET high_risks=%s, medium_risks=%s, low_risks=%s, "
            "informational_risks=%s, host=%s, status=%s WHERE scan_id=%s",
            [high, medium, low, info, host, "success", scan_id],
        )

        columns = ["scan_id", "vulnerability_name", "severity", "description", "solution",
                   "count", "instance_url"]
        for vuln_name, details in vuln_counts.items():
            try:
                count = int(details.get("count", 0))
            except Exception:
                count = 0
            description = str(details.get("description", ""))
            solution = str(details.get("solution", ""))
            db.insertRows(table="vulnerabilities", columns=columns, parameters=[[
                scan_id, str(vuln_name), str(details.get("severity", "")),
                description[3:-4], solution[3:-4], count, str(details.get("instance_url", "N/A")),
            ]])
    except Exception as e:
        print(f"Error ingesting scan artifacts: {e}")
        db.query("UPDATE scans SET status = %s WHERE scan_id = %s", ["success", scan_id])


def cancel_scan_run(db):
    """Cancel the most recent in-flight scan and remove its record."""
    rows = db.query(
        "SELECT * FROM scans WHERE status IN "
        "('queued','running','created','pending','in_progress') ORDER BY scan_id DESC LIMIT 1"
    )
    if not rows:
        return jsonify({"message": "No running scan to cancel"}), 200

    scan = rows[0]
    cfg = _gh_config()
    if cfg and scan.get("pipeline_id"):
        try:
            requests.post(
                f"{GITHUB_API}/repos/{cfg['owner']}/{cfg['repo']}/actions/runs/"
                f"{scan['pipeline_id']}/cancel",
                headers=_headers(cfg), timeout=_TIMEOUT,
            )
        except requests.RequestException:
            pass

    db.query("DELETE FROM scans WHERE scan_id = %s", [scan["scan_id"]])
    return jsonify({"message": "Scan Cancelled"})
