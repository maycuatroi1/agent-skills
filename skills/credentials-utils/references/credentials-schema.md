# Omelet credential store schema

Source of truth is the folder `${OMELET_DIR:-~/.omelet.d}/credentials/`, one JSON file per service. `compile.py` deep-merges every file's `flat` block into the generated flat `~/.omelet.json`. The key map lives in `scripts/_registry.py` (`SPECS`).

## Per-file schema

```json
{
  "id": "openai",
  "service": "OpenAI",
  "category": "ai",
  "description": "OpenAI project API key (genimg, aicheck)",
  "type": "api_key",
  "lifetime": "stable",
  "expiry": null,
  "status": "active",
  "rotate": "OpenAI dashboard -> API keys -> rotate",
  "added": "2026-06-24",
  "last_rotated": null,
  "flat": { "openai_api_key": "sk-..." }
}
```

| Field | Meaning |
|-------|---------|
| `id` | stable slug, matches the spec in `_registry.py` |
| `service` | human label shown by `doctor.py` |
| `category` | folder bucket: `accounts`, `cms`, `ai`, `infra`, `google-oauth`, `messaging`, `tools`, `firebase`, `_legacy`, `misc` (auto-bucket for unmapped keys from `migrate_to_folder.py`) |
| `type` | `api_key` \| `oauth_token` \| `basic_auth` \| `account` \| `service_account` \| `url` |
| `lifetime` | free-text note on how long it lives |
| `expiry` | ISO8601 for OAuth entries (mirrors the token expiry inside `flat`); `null` if stable |
| `status` | `active` \| `deprecated` \| `expired` (deprecated entries are skipped by `compile.py` unless `--include-legacy`) |
| `rotate` | how to rotate this credential |
| `oauth` | (OAuth only) descriptor used by the refresh script: `container` path, `access_field`, `expiry_field`, `client_from` path |
| `flat` | the exact JSON fragment merged into `~/.omelet.json` (preserves the historical flat keys) |

## Folder layout and key map

| File | Flat keys | Purpose / rotation |
|------|-----------|--------------------|
| `accounts/omelet.json` | `backend_url`, `public_webhook_url`, `username`, `password`, `use_gcs`, `gcs_bucket` | Omelet account + n8n webhooks + GCS backend. Rotate in Omelet settings / n8n workflow |
| `cms/ghost.json` | `ghost_api_url`, `ghost_content_api_key`, `ghost_admin_api_key` | Ghost CMS. Rotate: Ghost Admin -> Integrations |
| `ai/openai.json` | `openai_api_key` | OpenAI. Rotate: OpenAI dashboard |
| `ai/google.json` | `google_api_key` | Google API key (Gemini/Sheets). Rotate: GCP Console -> Credentials |
| `ai/kimi.json` | `kimi_code_api_key` | Moonshot Kimi Code. Rotate: Moonshot dashboard |
| `infra/cloudflare.json` | `cloudflare_api_token`, `cloudflare` | Cloudflare token + zone ids. Rotate: Cloudflare -> API Tokens |
| `infra/dokploy.json` | `dokploy_url`, `dokploy_api_key`, `dokploy_fu_url`, `dokploy_fu_api_key` | Dokploy default + fu instances. Rotate: Dokploy profile -> API |
| `infra/railway.json` | `railway_api_token` | Railway. Rotate: Railway account tokens |
| `infra/n8n.json` | `n8n_api_url`, `n8n_api_key`, `n8n_flutter_webhook_basic_auth` | n8n API + flutter webhook auth |
| `infra/observability.json` | `vlogs_password`, `metrics_basicauth_bcrypt_escaped`, `grafana` | VictoriaLogs / metrics / Grafana |
| `infra/ialab.json` | `ialab_dgx_sudo_password` | iaLab DGX sudo. Rotate: `passwd` on host |
| `google-oauth/rclone.json` | `rclone` | rclone Google Drive remote. Refresh: `refresh_google_oauth.py --service rclone` |
| `google-oauth/gmail.json` | `gmail` | Gmail OAuth (primary, used by `life mail`). Refresh: `--service gmail` |
| `google-oauth/google-drive.json` | `google_drive` | Google Drive OAuth (`evo gdrive`). Refresh: `--service google-drive` |
| `google-oauth/google-calendar.json` | `google_calendar` | Google Calendar OAuth (`life cal`). Refresh: `--service google-calendar` |
| `google-oauth/sheets-sa.json` | `google_sheets_sa_key_path`, `google_sheets_sa_email` | Path + email of GCP SA JSON. The referenced file holds the actual key and is NOT synced here |
| `messaging/lark.json` | `lark` | Lark/Feishu app + cookies |
| `messaging/facebook.json` | `facebook` | Facebook login (`life fb`) |
| `messaging/mailgun.json` | `mailgun` | Mailgun API |
| `tools/quillbot.json` | `quillbot_token` | QuillBot JWT (~1h, no programmatic refresh; re-extract from browser) |
| `tools/figma.json` | `figma_token` | Figma PAT |
| `tools/openclaw.json` | `openclaw_gateway_token` | OpenClaw gateway |
| `tools/cliproxy.json` | `cliproxy` | CLI proxy keys |
| `tools/lms.json` | `lms` | LMS SCORM CDN URL |
| `firebase/firebase-admin.json` | `firebase_admin_sdk` | Firebase Admin SDK (project omelet-f0b89) |
| `_legacy/gmail-socrat.json` | `gmail_socrat` | DEPRECATED, superseded by `gmail`. Excluded from compile by default |
| `_legacy/gmail-sometimesocrazy.json` | `gmail_sometimesocrazy` | DEPRECATED, superseded by `gmail`. Excluded from compile by default |

## Token expiry management

OAuth entries (`type: oauth_token` with an `oauth` descriptor) carry a short-lived access token:

- **rclone / gmail / google-drive / google-calendar** — run `refresh_google_oauth.py --all` (or `--service <name>`). Refresh uses the long-lived `refresh_token` and the client id/secret stored inside the file (rclone can override via `RCLONE_DRIVE_CLIENT_ID/SECRET`).
- **quillbot** — JWT from Firebase, ~1h, no programmatic refresh. Re-extract from the browser / `omelet aicheck refresh`.

`doctor.py` reports the live `EXPIRED` / `expiring` status by reading the token expiry inside each file. Everything else is long-lived until manually rotated.

## Sensitivity notes

- `password`, all `*_api_key`/`*_api_token`, `rclone.token.*`, OAuth tokens, `firebase_admin_sdk.private_key` are bearer secrets.
- `google_sheets_sa_key_path` stores only a path; the referenced SA JSON is not synced by this skill.
- `*_url`, `username`, `gcs_bucket`, `google_sheets_sa_email` are low-sensitivity identifiers but still private.
