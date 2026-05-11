#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("OMELET_CONFIG", str(Path.home() / ".omelet.json")))
TOKEN_URL = "https://oauth2.googleapis.com/token"


def main():
    dry_run = "--dry-run" in sys.argv

    if not CONFIG_PATH.exists():
        sys.stderr.write(f"config not found: {CONFIG_PATH}\n")
        sys.exit(1)

    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    rclone_section = data.get("rclone", {})
    token_section = rclone_section.get("token", {})
    refresh_token = token_section.get("refresh_token")
    if not refresh_token:
        sys.stderr.write("rclone.token.refresh_token missing in config\n")
        sys.exit(1)

    client_id = (
        os.environ.get("RCLONE_DRIVE_CLIENT_ID")
        or rclone_section.get("client_id")
    )
    client_secret = (
        os.environ.get("RCLONE_DRIVE_CLIENT_SECRET")
        or rclone_section.get("client_secret")
    )
    if not client_id or not client_secret:
        sys.stderr.write(
            "OAuth client credentials required.\n"
            "Set RCLONE_DRIVE_CLIENT_ID + RCLONE_DRIVE_CLIENT_SECRET env vars,\n"
            "or add rclone.client_id + rclone.client_secret keys to the config.\n"
            "Defaults are in rclone source: backend/drive/drive.go\n"
        )
        sys.exit(1)

    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode("utf-8")

    if dry_run:
        sys.stderr.write(
            f"dry-run: would POST to {TOKEN_URL} "
            f"with refresh_token={refresh_token[:10]}... and client_id={client_id}\n"
        )
        sys.exit(0)

    req = urllib.request.Request(TOKEN_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "replace")
        sys.stderr.write(f"token refresh failed: HTTP {e.code}\n{err_body}\n")
        sys.exit(1)
    except urllib.error.URLError as e:
        sys.stderr.write(f"network error: {e}\n")
        sys.exit(1)

    new_access = body.get("access_token")
    expires_in = int(body.get("expires_in", 3600))
    if not new_access:
        sys.stderr.write(f"no access_token in response: {body}\n")
        sys.exit(1)

    tz = timezone(timedelta(hours=7))
    expiry = (datetime.now(tz) + timedelta(seconds=expires_in)).isoformat()

    data["rclone"]["token"]["access_token"] = new_access
    data["rclone"]["token"]["expiry"] = expiry
    data["rclone"]["token"]["expires_in"] = expires_in

    tmp = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(CONFIG_PATH.parent), encoding="utf-8"
    )
    try:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
        tmp.close()
        os.chmod(tmp.name, 0o600)
        os.replace(tmp.name, CONFIG_PATH)
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise

    sys.stderr.write(f"refreshed rclone access_token, valid until {expiry}\n")


if __name__ == "__main__":
    main()
