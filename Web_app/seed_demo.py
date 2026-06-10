"""
Seed the database with synthetic demo data for the public portfolio deployment.

Creates the schema, four demo users (owner/admin/employee/reader), a few demo
websites, and realistic scan + vulnerability records parsed from the bundled
demo-target ZAP artifacts (juice-shop / brokencrystals / zaproxy.org). Contains
NO real personal data. Safe to run repeatedly (users/websites use INSERT IGNORE;
scans are only seeded when the scans table is empty).

Run from the Web_app directory:  python seed_demo.py
"""
import glob
import os
import secrets
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from dotenv import load_dotenv

from flask_app.utils.database.database import database
from flask_app.scan_parse import process_report

if os.getenv("DOCKER_ENV") != "true":
    load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))

# Demo users: (email, role, password-env-var, default password)
DEMO_USERS = [
    ("owner@demo.local",    "owner",    "DEMO_OWNER_PASSWORD",    "demo-owner-pass"),
    ("admin@demo.local",    "admin",    "DEMO_ADMIN_PASSWORD",    "demo-admin-pass"),
    ("employee@demo.local", "employee", "DEMO_EMPLOYEE_PASSWORD", "demo-employee-pass"),
    ("reader@demo.local",   "reader",   "DEMO_READER_PASSWORD",   "demo-reader-pass"),
]

# Demo websites: (name, url, owner-email)
WEBSITES = [
    ("OWASP Juice Shop", "https://juice-shop.herokuapp.com/", "owner@demo.local"),
    ("Broken Crystals",  "https://brokencrystals.com/",       "owner@demo.local"),
    ("ZAP Project Site", "https://www.zaproxy.org/",          "admin@demo.local"),
]
NAME_BY_URL = {url: name for name, url, _ in WEBSITES}
OWNER_BY_URL = {url: owner for _, url, owner in WEBSITES}

# Scans to seed: (website url, bundled scan folder, days-ago). Folder also becomes
# pipeline_id so the "download raw scan" feature resolves the bundled file.
DEMO_SCANS = [
    ("https://juice-shop.herokuapp.com/", "94192", 40),
    ("https://juice-shop.herokuapp.com/", "94498", 30),
    ("https://juice-shop.herokuapp.com/", "94862", 20),
    ("https://juice-shop.herokuapp.com/", "95131", 8),
    ("https://brokencrystals.com/",       "93976", 35),
    ("https://www.zaproxy.org/",          "95204", 22),
    ("https://www.zaproxy.org/",          "96321", 6),
]

db = database()  # reused only for env-consistent password/api-key hashing


def conn():
    # Reuse the database class's connection settings (bounded timeout + optional TLS CA).
    return mysql.connector.connect(**db._conn_kwargs)


def apply_schema(c):
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        sql = f.read()
    cur = c.cursor()
    for stmt in (s.strip() for s in sql.split(";")):
        if stmt:
            cur.execute(stmt)
    c.commit()
    cur.close()
    print("schema applied")


def scalar(c, query, params=()):
    cur = c.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def seed_users(c):
    cur = c.cursor()
    for email, role, env, default in DEMO_USERS:
        pw = os.getenv(env, default)
        cur.execute(
            "INSERT IGNORE INTO users (role, email, password, api_key) VALUES (%s, %s, %s, %s)",
            (role, email, db.onewayEncrypt(pw), db.onewayEncrypt(secrets.token_hex(32))),
        )
    cur.execute("INSERT IGNORE INTO domains (domain) VALUES ('demo.local')")
    c.commit()
    cur.close()
    print(f"seeded {len(DEMO_USERS)} demo users + demo.local domain")


def seed_websites(c):
    cur = c.cursor()
    for name, url, owner in WEBSITES:
        owner_id = scalar(c, "SELECT user_id FROM users WHERE email = %s", (owner,))
        cur.execute(
            "INSERT IGNORE INTO websites (owner_id, website_name, website_url) VALUES (%s, %s, %s)",
            (owner_id, name, url),
        )
    c.commit()
    cur.close()
    print(f"seeded {len(WEBSITES)} demo websites")


def seed_shares(c):
    # Share the Juice Shop group with employee + reader so their dashboards aren't empty.
    juice_url = "https://juice-shop.herokuapp.com/"
    website_id = scalar(c, "SELECT website_id FROM websites WHERE website_url = %s", (juice_url,))
    name = NAME_BY_URL[juice_url]
    cur = c.cursor()
    for email in ("employee@demo.local", "reader@demo.local"):
        uid = scalar(c, "SELECT user_id FROM users WHERE email = %s", (email,))
        role = email.split("@")[0]
        exists = scalar(c, "SELECT auth_id FROM website_auth WHERE website_id = %s AND user_id = %s",
                        (website_id, uid))
        if not exists:
            cur.execute(
                "INSERT INTO website_auth (website_id, user_id, role, website_name) VALUES (%s, %s, %s, %s)",
                (website_id, uid, role, name),
            )
    c.commit()
    cur.close()
    print("shared Juice Shop with employee + reader")


def find_scan_json(folder):
    base = os.path.join(HERE, "flask_app", "scans", folder)
    hits = glob.glob(os.path.join(base, "**", "scan.json"), recursive=True)
    return hits[0] if hits else None


def seed_scans(c):
    if (scalar(c, "SELECT COUNT(*) FROM scans") or 0) > 0:
        print("scans already present; skipping scan seed")
        return
    seeded = 0
    for url, folder, days_ago in DEMO_SCANS:
        json_path = find_scan_json(folder)
        if not json_path:
            print(f"  (no bundled scan.json for folder {folder}; skipping)")
            continue
        website_id = scalar(c, "SELECT website_id FROM websites WHERE website_url = %s", (url,))
        owner_id = scalar(c, "SELECT user_id FROM users WHERE email = %s", (OWNER_BY_URL[url],))
        scan_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago)

        with tempfile.TemporaryDirectory() as tmp:
            values, vuln_counts, unique_urls = process_report(json_path, tmp, None)
        high, medium, low, info, host = values

        cur = c.cursor()
        cur.execute(
            "INSERT INTO scans (user_id, scan_name, website_url, scan_date, status, high_risks, "
            "medium_risks, low_risks, informational_risks, report_url, pipeline_id, host, website_id) "
            "VALUES (%s, %s, %s, %s, 'success', %s, %s, %s, %s, %s, %s, %s, %s)",
            (owner_id, NAME_BY_URL[url], url, scan_date, high, medium, low, info,
             None, int(folder), host, website_id),
        )
        scan_id = cur.lastrowid
        for vuln_name, d in vuln_counts.items():
            try:
                cnt = int(d.get("count", 0))
            except Exception:
                cnt = 0
            desc = str(d.get("description", ""))
            sol = str(d.get("solution", ""))
            cur.execute(
                "INSERT INTO vulnerabilities (scan_id, vulnerability_name, severity, description, "
                "solution, count, instance_url) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (scan_id, str(vuln_name), str(d.get("severity", "")),
                 desc[3:-4], sol[3:-4], cnt, str(d.get("instance_url", "N/A"))),
            )
        for u in unique_urls:
            cur.execute("INSERT INTO scanned_websites (scan_id, website_url) VALUES (%s, %s)",
                        (scan_id, u))
        c.commit()
        cur.close()
        seeded += 1
        print(f"  seeded scan {scan_id} {url}  H{high}/M{medium}/L{low}/I{info}  "
              f"{len(vuln_counts)} vuln types")
    print(f"seeded {seeded} demo scans")


def main():
    c = conn()
    try:
        apply_schema(c)
        seed_users(c)
        seed_websites(c)
        seed_shares(c)
        seed_scans(c)
    finally:
        c.close()
    print("Demo seed complete.")


if __name__ == "__main__":
    main()
