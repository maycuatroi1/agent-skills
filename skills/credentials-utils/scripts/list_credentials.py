#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("OMELET_CONFIG", str(Path.home() / ".omelet.json")))

DESCRIPTIONS = {
    "backend_url": "Omelet n8n private backend webhook",
    "public_webhook_url": "Omelet n8n public webhook",
    "username": "Omelet account username",
    "password": "Omelet account password (plaintext)",
    "use_gcs": "Flag enabling Google Cloud Storage backend",
    "gcs_bucket": "GCS bucket for omelet uploads",
    "ghost_api_url": "Ghost CMS blog URL",
    "ghost_content_api_key": "Ghost Content API key (read-only)",
    "ghost_admin_api_key": "Ghost Admin API key (id:secret for JWT signing)",
    "google_api_key": "Google API key (Gemini, Sheets, etc.)",
    "openai_api_key": "OpenAI API key (project key)",
    "quillbot_token": "QuillBot paraphraser JWT (Firebase, ~1h expiry, no refresh)",
    "cloudflare_api_token": "Cloudflare API token",
    "openclaw_gateway_token": "OpenClaw gateway auth token",
    "kimi_code_api_key": "Moonshot Kimi Code API key",
    "google_sheets_sa_key_path": "Path to GCP service account JSON for Sheets",
    "google_sheets_sa_email": "GCP service account email for Sheets",
    "rclone.remote_name": "rclone remote name",
    "rclone.type": "rclone backend type",
    "rclone.scope": "OAuth scope granted to rclone",
    "rclone.root_folder_id": "Google Drive folder ID acting as rclone root",
    "rclone.token.access_token": "Short-lived OAuth access token (~1h)",
    "rclone.token.token_type": "OAuth token type (Bearer)",
    "rclone.token.refresh_token": "Long-lived refresh token (refresh_rclone_token.py)",
    "rclone.token.expiry": "Access token expiry ISO8601",
    "rclone.token.expires_in": "Access token TTL seconds at issue time",
}


def mask(value) -> str:
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if len(s) <= 12:
        return "***"
    return f"{s[:4]}...{s[-4:]} (len={len(s)})"


def walk(data, prefix=""):
    rows = []
    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                rows.extend(walk(v, path))
            else:
                rows.append((path, v))
    return rows


def main():
    if not CONFIG_PATH.exists():
        sys.stderr.write(f"config not found: {CONFIG_PATH}\n")
        sys.exit(1)

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"invalid JSON in {CONFIG_PATH}: {e}\n")
        sys.exit(1)

    rows = walk(data)
    if not rows:
        sys.stderr.write("no credentials found\n")
        sys.exit(0)

    key_w = max(len(r[0]) for r in rows)
    type_w = 6
    val_w = 28

    header = f"{'KEY'.ljust(key_w)}  {'TYPE'.ljust(type_w)}  {'VALUE'.ljust(val_w)}  DESCRIPTION"
    print(header)
    print("-" * len(header))

    for path, value in rows:
        t = type(value).__name__
        display = mask(value)
        desc = DESCRIPTIONS.get(path, "(undocumented)")
        print(f"{path.ljust(key_w)}  {t.ljust(type_w)}  {display.ljust(val_w)}  {desc}")

    print(f"\nconfig: {CONFIG_PATH}  ({len(rows)} keys)")


if __name__ == "__main__":
    main()
