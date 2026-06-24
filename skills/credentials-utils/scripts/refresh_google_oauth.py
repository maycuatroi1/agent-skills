#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry import CREDENTIALS_DIR, META_FIELDS, dig, load_entries

TOKEN_URL = "https://oauth2.googleapis.com/token"
SERVICE_ALIASES = {
    "rclone": "rclone",
    "gmail": "gmail",
    "google-drive": "google_drive",
    "google_drive": "google_drive",
    "google-calendar": "google_calendar",
    "google_calendar": "google_calendar",
}


def usage():
    sys.stderr.write(
        "usage: refresh_google_oauth.py (--all | --service <name>) [--dry-run]\n"
        "  services: rclone, gmail, google-drive, google-calendar\n"
    )
    sys.exit(2)


def resolve_creds(entry):
    flat = entry["flat"]
    oauth = entry["oauth"]
    container = dig(flat, oauth["container"])
    if not isinstance(container, dict):
        return None, "token container missing"
    refresh_token = container.get("refresh_token")
    if not refresh_token:
        return None, "refresh_token missing"

    client_src = dig(flat, oauth["client_from"]) or {}
    client_id = (
        os.environ.get("RCLONE_DRIVE_CLIENT_ID")
        if entry["id"] == "rclone"
        else None
    ) or client_src.get("client_id")
    client_secret = (
        os.environ.get("RCLONE_DRIVE_CLIENT_SECRET")
        if entry["id"] == "rclone"
        else None
    ) or client_src.get("client_secret")
    if not client_id or not client_secret:
        return None, "client_id/client_secret missing (set env for rclone)"

    return {
        "container": container,
        "oauth": oauth,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }, None


def post_refresh(creds):
    payload = urllib.parse.urlencode(
        {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_entry(path, entry):
    ordered = {k: entry[k] for k in META_FIELDS if k in entry}
    ordered["flat"] = entry["flat"]
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    target = None
    if "--all" in args:
        target = "*"
    elif "--service" in args:
        i = args.index("--service")
        if i + 1 >= len(args):
            usage()
        name = args[i + 1]
        if name not in SERVICE_ALIASES:
            sys.stderr.write(f"unknown service: {name}\n")
            usage()
        target = SERVICE_ALIASES[name]
    else:
        usage()

    if not CREDENTIALS_DIR.exists():
        sys.stderr.write(f"credentials folder not found: {CREDENTIALS_DIR}\n")
        sys.exit(1)

    entries = [
        (path, entry)
        for path, entry in load_entries()
        if entry.get("oauth") and (target == "*" or entry.get("id") == target)
    ]
    if not entries:
        sys.stderr.write("no matching refreshable oauth entries\n")
        sys.exit(1)

    failures = 0
    refreshed = 0
    for path, entry in entries:
        sid = entry["id"]
        creds, err = resolve_creds(entry)
        if err:
            sys.stderr.write(f"{sid}: skip ({err})\n")
            failures += 1
            continue

        if dry_run:
            sys.stderr.write(
                f"{sid}: would POST {TOKEN_URL} "
                f"refresh_token={creds['refresh_token'][:10]}... client_id={creds['client_id'][:12]}...\n"
            )
            continue

        try:
            body = post_refresh(creds)
        except urllib.error.HTTPError as e:
            sys.stderr.write(f"{sid}: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]}\n")
            failures += 1
            continue
        except urllib.error.URLError as e:
            sys.stderr.write(f"{sid}: network error {e}\n")
            failures += 1
            continue

        new_access = body.get("access_token")
        if not new_access:
            sys.stderr.write(f"{sid}: no access_token in response\n")
            failures += 1
            continue
        expires_in = int(body.get("expires_in", 3600))
        tz = timezone(timedelta(hours=7))
        expiry = (datetime.now(tz) + timedelta(seconds=expires_in)).isoformat()

        oauth = creds["oauth"]
        creds["container"][oauth["access_field"]] = new_access
        creds["container"][oauth["expiry_field"]] = expiry
        if "expires_in" in creds["container"]:
            creds["container"]["expires_in"] = expires_in

        entry["expiry"] = expiry
        entry["status"] = "active"
        entry["last_rotated"] = datetime.now(tz).isoformat()
        write_entry(path, entry)
        refreshed += 1
        sys.stderr.write(f"{sid}: refreshed, valid until {expiry}\n")

    if not dry_run and refreshed:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "compile.py")], check=False)

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
