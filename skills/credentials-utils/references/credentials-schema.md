# `~/.omelet.json` credential schema

Full inventory of keys stored in `~/.omelet.json`, what each is for, lifetime, and how to rotate.

## Top-level keys

| Key | Purpose | Lifetime | How to rotate |
|-----|---------|----------|---------------|
| `backend_url` | Omelet private n8n webhook | Stable | Edit n8n workflow, copy new webhook URL |
| `public_webhook_url` | Omelet public n8n webhook | Stable | Same as above |
| `username` | Omelet account username | Stable | Change in Omelet account settings |
| `password` | Omelet account password (plaintext) | Stable | Change in Omelet account settings |
| `use_gcs` | Boolean toggle for GCS backend | Stable | Edit value directly |
| `gcs_bucket` | GCS bucket name for uploads | Stable | Set new bucket name |
| `ghost_api_url` | Ghost CMS blog URL | Stable | Change Ghost domain |
| `ghost_content_api_key` | Ghost Content API key (read-only) | Stable | Ghost Admin → Integrations → regenerate |
| `ghost_admin_api_key` | Ghost Admin API key, `<id>:<secret>` | Stable | Ghost Admin → Integrations → regenerate |
| `google_api_key` | Google API key (Gemini, Sheets, etc.) | Stable | Google Cloud Console → APIs & Services → Credentials |
| `openai_api_key` | OpenAI project API key | Stable | OpenAI dashboard → API keys → rotate |
| `quillbot_token` | QuillBot paraphraser Firebase JWT | ~1 hour, no refresh | Re-login to QuillBot, capture from browser |
| `cloudflare_api_token` | Cloudflare API token | Stable until rotated | Cloudflare dashboard → API Tokens |
| `openclaw_gateway_token` | OpenClaw gateway auth token | Stable | Issued by OpenClaw service |
| `kimi_code_api_key` | Moonshot Kimi Code API key | Stable | Moonshot dashboard |
| `google_sheets_sa_key_path` | Local path to GCP service account JSON | Stable | Generate new SA key in GCP, replace file |
| `google_sheets_sa_email` | GCP service account email | Stable | Service account email is permanent |

## Nested: `rclone`

| Key | Purpose | Lifetime | How to rotate |
|-----|---------|----------|---------------|
| `rclone.remote_name` | rclone remote name (default `gdrive`) | Stable | Match name in `rclone.conf` |
| `rclone.type` | rclone backend type (`drive`) | Stable | — |
| `rclone.scope` | OAuth scope granted (`drive`) | Stable | — |
| `rclone.root_folder_id` | Google Drive folder ID treated as rclone root | Stable | Change to a different Drive folder ID |
| `rclone.token.access_token` | Short-lived OAuth access token | ~1 hour | Run `scripts/refresh_rclone_token.py` |
| `rclone.token.token_type` | OAuth token type (`Bearer`) | Stable | — |
| `rclone.token.refresh_token` | Long-lived refresh token | Until revoked | Re-run `rclone config reconnect gdrive:` if revoked |
| `rclone.token.expiry` | Access token expiry ISO8601 | Updated each refresh | Auto-updated by refresh script |
| `rclone.token.expires_in` | TTL seconds at last issue | ~3599 | Auto-updated by refresh script |

## Token expiry checklist

Tokens that need active management:

- **`rclone.token.access_token`** — Check `rclone.token.expiry` before use. If past, run `python3 scripts/refresh_rclone_token.py`. Refresh is automatic via long-lived `refresh_token`.
- **`quillbot_token`** — JWT from Firebase Auth, ~1h. No programmatic refresh in this skill; re-extract from browser DevTools when needed.

Everything else is long-lived until manually rotated.

## Notes on sensitivity

- `password`, `ghost_admin_api_key`, all `*_api_key`, `*_api_token`, `rclone.token.*` are bearer credentials. Treat as secret.
- `google_sheets_sa_key_path` only stores a path, not the key itself. The referenced file (`~/.omelet-sheets-sa.json`) holds the actual private key and is NOT synced by this skill — sync it separately if needed.
- `username`, `*_url`, `gcs_bucket`, `google_sheets_sa_email` are low-sensitivity identifiers but still kept private.
