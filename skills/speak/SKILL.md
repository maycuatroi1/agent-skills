---
name: speak
description: This skill should be used when the user asks to "speak", "say it out loud", "đọc cho tôi nghe", "nói tóm tắt", "tts", "text to speech", "tạo giọng đọc", "lồng tiếng", "voiceover", "narrate this", or when you have finished a long task and want to hand the result over by voice instead of a wall of text. Covers both the `evo tts` CLI (Vbee for Vietnamese, OpenAI gpt-4o-mini-tts otherwise) and the `evo-tts` MCP server whose `speak` tool plays audio through the user's speakers.
version: 0.1.0
---

# speak

Turn text into speech and play it, either from the terminal (`evo tts`) or from inside an agent
session (the `evo-tts` MCP server).

**This skill owns no synthesis code.** The engine lives in evo-cli (`evo_cli/tts/`, surfaced as
`evo tts`) and the MCP wrapper lives in this repo at `mcp/tts/server.py`. If a flag here does not
exist, the skill is stale - run `evo tts --help` and trust the CLI, then fix this file.

## Providers

| Provider | Model / API | Good for | Limits |
|---|---|---|---|
| `vbee` | `https://api.vbee.vn/v1/tts` | Vietnamese - natural, correct tones | realtime 300 chars/request, batch 100k chars/request |
| `openai` | `gpt-4o-mini-tts` | English and other languages, steerable delivery via `instructions` | 4000 chars/request, no batch speech endpoint |

`--provider auto` (the default) picks Vbee when its credentials exist, otherwise OpenAI.

Two request shapes, and the CLI picks the right one for you:

- **Realtime** (`evo tts speak`, MCP `speak`) - Vbee `mode: sync`, audio comes back in the response
  in about half a second. Text longer than the limit is split on sentence boundaries and the
  resulting audio is joined back into one file.
- **Batch** (`evo tts batch`, MCP `speak_batch`) - Vbee `mode: async`, returns a `requestId`, and evo
  polls `/v1/tts/requests/{id}` until `audioLink` appears, then downloads it. The Vbee API demands a
  `webhookUrl` even when you poll, so evo sends a placeholder unless you pass `--webhook`. OpenAI has
  no batch speech endpoint, so there the items are just run concurrently.

## Credentials

Never hardcode keys. Everything comes from the omelet store via `evo cred` (see the
`credentials-utils` skill):

```bash
evo cred add vbee.app_id --from-stdin      # UUID from https://studio.vbee.vn/apps
evo cred add vbee.token --from-stdin       # JWT from the same app page
evo cred add openai_api_key --from-stdin
```

`VBEE_APP_ID`, `VBEE_TOKEN`, and `OPENAI_API_KEY` in the environment override the store, which is how
you point a CI job at a different app without touching the machine's credentials.

Vbee tokens expire according to the app's setting (7/30/60/90 days, or never). A `HTTP 401
UNAUTHORIZED` from `evo tts` means the token lapsed: create a new app at studio.vbee.vn and re-run the
two `evo cred add` lines above.

## CLI

```bash
evo tts speak "Xin chào, bản build đã xong"          # synthesise and play now
evo tts speak -f notes.md -o notes.mp3               # read a file, keep the audio
evo tts speak "hello" -p openai -V nova \
  --instructions "calm and encouraging"              # steer OpenAI delivery
git log -1 --format=%s | evo tts speak               # read stdin
evo tts speak "hi" --stdout > out.mp3                # raw bytes to a pipe

evo tts batch chapters/ -o audio/                    # one mp3 per .txt/.md, async API
evo tts batch a.txt b.txt -c 8                       # 8 items in flight
evo tts batch --manifest jobs.jsonl                  # {"id":..,"text":..,"voice":..} per line

evo tts voices                                       # Vbee Vietnamese voices
evo tts voices -l en-US --gender male
evo tts voices -p openai
```

Useful flags: `--no-play`, `--format mp3|wav`, `--speed` (Vbee 0.25-1.9), `--bitrate`, `--voice`,
`--timeout` and `--poll-interval` for the async path.

## MCP server

`mcp/tts/server.py` is a stdio MCP server with no SDK dependency - it speaks JSON-RPC directly and
declares its one requirement (`evo_cli`) in PEP 723 inline metadata, so `uv` resolves it on first
run. Register it once:

```bash
bash mcp/tts/install.sh
```

That smoke-tests `tools/list`, then registers the server with every agent CLI it finds on PATH,
skipping the ones that are absent:

| CLI | How it is registered | Config it lands in |
|---|---|---|
| Claude Code | `claude mcp add --scope user` | `~/.claude.json` |
| Codex | `codex mcp add` | `~/.codex/config.toml` |
| OpenCode | `evo mcp add --opencode-only` | `~/.config/opencode/opencode.jsonc` |

OpenCode goes through `evo` because evo-cli owns the jsonc writer; the other two have first-class
`mcp add` subcommands. Idempotent, safe on a fresh machine, and nothing is installed into the system
interpreter.

Verify with `claude mcp get evo-tts`, `codex mcp get evo-tts`, and `opencode mcp list`.

The smoke test passes `--refresh` because uv caches its PyPI index: right after an evo-cli release,
a plain `uv run` resolves against the stale index and reports the new version as nonexistent. The
registered MCP command deliberately omits `--refresh` so normal runs stay fast.

To develop against a local evo-cli checkout instead of the published package, `pip install -e` it and
pass the interpreter: `EVO_TTS_PYTHON=$(which python) bash mcp/tts/install.sh`.

The server negotiates the MCP protocol version: it echoes the client's version when it recognises it
(`2025-11-25` back to `2024-11-05`) and otherwise answers with the current spec revision.

Tools it exposes:

| Tool | What it does |
|---|---|
| `speak` | Synthesise and play through the speakers. Returns as soon as playback is queued (`wait: true` to block). |
| `speak_batch` | Bulk voiceover to files via the async API. No playback. |
| `list_voices` | Voice codes for the `voice` argument. |

### Picking the default provider for a machine

`--provider auto` (and the MCP `provider` argument) resolves in this order: `EVO_TTS_PROVIDER`, then
whichever provider has credentials. Set it once and both the CLI and the MCP server follow:

| Variable | Effect |
|---|---|
| `EVO_TTS_PROVIDER` | `vbee` or `openai`. Decides what `auto` means. |
| `EVO_TTS_VOICE_OPENAI` / `EVO_TTS_VOICE_VBEE` | Default voice for that provider only. |
| `EVO_TTS_VOICE` | Default voice for whichever provider is active. Scoped wins over this. |
| `EVO_TTS_SPEED` | Default speaking rate for the MCP tools. |
| `EVO_TTS_DIR` | Where scratch audio lands. |

Prefer the scoped voice variables. A bare `EVO_TTS_VOICE=nova` breaks the moment you pass
`--provider vbee`, because `nova` is not a Vbee voice code.

`install.sh` reads whichever of these are exported and bakes them onto each MCP entry, rather than
relying on the agent CLI inheriting them - these are often launched from a GUI that never sourced a
shell profile. Re-run `install.sh` after changing one; it replaces the existing entries.

```bash
export EVO_TTS_PROVIDER=openai
export EVO_TTS_VOICE_OPENAI=nova
bash mcp/tts/install.sh
```

## When the agent should call `speak`

Use it to hand over, not to narrate. Good moments:

- A long task finished and the user has probably looked away from the terminal.
- You are blocked and need a decision.
- The user explicitly asked to be told out loud.

**Write for the ear.** The text is read verbatim, so:

- Plain spoken sentences. No markdown, no bullet characters, no code, no file paths, no URLs.
- A few sentences at most: what you did, what came out of it, what is next.
- Vietnamese must carry full diacritics. Both engines read the tones; unaccented text comes out wrong.

**Keep English technical terms in English.** `gpt-4o-mini-tts` is multilingual and code-switches
mid-sentence, so write `MCP`, `uv`, `PyPI`, `token`, `commit`, `repo` exactly as you would type them.
Do **not** respell them phonetically for a Vietnamese reader - that was a workaround for Vbee, it is
unreadable in the transcript, and on OpenAI it actively produces worse audio because the model no
longer recognises the word.

Good:

> Đã push xong ba repo. MCP server chạy qua uv, evo-cli đã lên PyPI phiên bản 0.13.0, và ba tool tốn
> khoảng 830 token context.

Bad - phonetic respelling, the old Vbee workaround:

> Đã push xong ba repo. Em xi pi server chạy qua u vê, e vô cli đã lên pai pi ai.

Bad - reads punctuation and paths out loud:

> Done! Created `evo_cli/tts/core.py` - 3 files changed, +212/-0. See **batch mode** for details.

Numbers are fine as digits; both engines expand them. Prefer writing `0.13.0` and `830 token` over
spelling them out.

## Playback

`evo_cli/tts/player.py` tries `ffplay`, `mpv`, `cvlc`, plus `afplay` on macOS and `paplay`/`aplay` on
Linux, and falls back to `System.Windows.Media.MediaPlayer` through PowerShell on Windows. If none is
available the CLI warns and still writes the file. Installing ffmpeg is the one-line fix on every
platform.

## Gotchas

- Vbee `audioLink` from the async API **expires after 3 minutes**. evo downloads it immediately; if
  you keep a link around, call `GET /v1/tts/requests/{id}` again for a fresh one (the audio itself is
  retained for 3 days).
- Vbee realtime only supports a handful of voices (Ngọc Huyền, Mai Phương, Lan Trinh, Thảo Trinh,
  Tường Vy). Other codes work in batch mode but 400 in realtime - use `evo tts batch` for them.
- Vbee realtime rejects `pcm` in batch mode but accepts it in sync mode; stick to `mp3` unless you
  have a reason.
- Joining chunks concatenates MP3 frames (and stitches WAV via the `wave` module). `opus`, `aac`, and
  `flac` cannot be joined, so multi-chunk text with those formats is refused rather than silently
  truncated.
- `gpt-4o-mini-tts` ignores `speed`; use `instructions` ("speak slowly and deliberately") instead.
- The three tool definitions cost about **830 tokens** of context in every session that loads them
  (measured with `o200k_base` over the real `tools/list` payload, including the `mcp__evo-tts__`
  name prefix). That is 0.4% of a 200k window, and the bulk of it is `speak`'s schema at 398 tokens.
  It is charged once per request as part of the system prompt, so prompt caching absorbs it.
- Under Git Bash, `pwd` returns `/c/Users/...`. MSYS rewrites that to a Windows path only for
  arguments handed straight to a native binary, so a path embedded in a longer string reaches the
  config verbatim and `uv` cannot open it. `install.sh` normalises with `cygpath -m` first.
