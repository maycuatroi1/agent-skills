# /// script
# requires-python = ">=3.9"
# dependencies = ["evo_cli>=0.13.0"]
# ///

import json
import os
import queue
import sys
import tempfile
import threading
import traceback
from pathlib import Path

try:
    from evo_cli.tts import core, player
    from evo_cli.tts.errors import TtsError
except ImportError:
    sys.stderr.write(
        "evo-tts MCP: evo_cli is not importable. Run this server with "
        "`uv run --script server.py` so uv resolves it, or `pip install evo_cli` "
        "into the interpreter you are using.\n"
    )
    raise

SERVER_NAME = "evo-tts"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

DEFAULT_SPEED = float(os.environ.get("EVO_TTS_SPEED", "1.0"))

_play_queue = queue.Queue()
_play_thread = None
_play_lock = threading.Lock()


def log(message):
    sys.stderr.write(f"[{SERVER_NAME}] {message}\n")
    sys.stderr.flush()


def _playback_loop():
    while True:
        path = _play_queue.get()
        try:
            if not player.play(path):
                log(f"no audio player available - {player.player_hint()}")
        except Exception as exc:
            log(f"playback failed: {exc}")
        finally:
            _play_queue.task_done()


def enqueue_playback(path):
    global _play_thread
    with _play_lock:
        if _play_thread is None or not _play_thread.is_alive():
            _play_thread = threading.Thread(target=_playback_loop, daemon=True)
            _play_thread.start()
    _play_queue.put(str(path))


def audio_scratch_dir():
    target = Path(os.environ.get("EVO_TTS_DIR") or Path(tempfile.gettempdir()) / "evo-tts")
    target.mkdir(parents=True, exist_ok=True)
    return target


SPEAK_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": (
                "What to say, already written the way it should be heard: plain spoken "
                "sentences, no markdown, no code blocks, no bullet characters, no URLs. "
                "Keep technical terms in their normal English spelling even inside a "
                "Vietnamese sentence - write MCP, uv, PyPI, token. Never respell them "
                "phonetically; the model code-switches and reads English correctly."
            ),
        },
        "provider": {
            "type": "string",
            "enum": ["auto", "vbee", "openai"],
            "description": (
                "auto follows EVO_TTS_PROVIDER, falling back to whichever provider has "
                "credentials. Override per call only when you need the other one."
            ),
        },
        "voice": {"type": "string", "description": "Voice code; see the list_voices tool."},
        "speed": {"type": "number", "description": "Speaking rate. Vbee accepts 0.25 to 1.9."},
        "instructions": {
            "type": "string",
            "description": "OpenAI only: delivery direction, e.g. 'calm and encouraging'.",
        },
        "save_path": {"type": "string", "description": "Keep the audio here instead of a scratch file."},
        "wait": {
            "type": "boolean",
            "description": "Block until playback finishes. Default false so the agent keeps working.",
        },
        "play": {"type": "boolean", "description": "Play through the speakers. Default true."},
    },
    "required": ["text"],
}

SPEAK_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "description": "One entry per audio file to produce.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Output file stem."},
                    "text": {"type": "string"},
                    "voice": {"type": "string"},
                    "instructions": {"type": "string"},
                },
                "required": ["text"],
            },
        },
        "out_dir": {"type": "string", "description": "Directory for the audio files."},
        "provider": {"type": "string", "enum": ["auto", "vbee", "openai"]},
        "voice": {"type": "string", "description": "Voice applied to items without their own."},
        "output_format": {"type": "string", "enum": ["mp3", "wav"]},
        "speed": {"type": "number"},
        "concurrency": {"type": "integer", "description": "Items in flight at once. Default 4."},
    },
    "required": ["items"],
}

LIST_VOICES_SCHEMA = {
    "type": "object",
    "properties": {
        "provider": {"type": "string", "enum": ["auto", "vbee", "openai"]},
        "language": {"type": "string", "description": "Vbee language code, e.g. vi-VN or en-US."},
        "gender": {"type": "string", "enum": ["male", "female"]},
        "search": {"type": "string", "description": "Substring filter over code and name."},
        "limit": {"type": "integer"},
    },
}

TOOLS = [
    {
        "name": "speak",
        "description": (
            "Say something out loud through the user's speakers. Use this to deliver a short spoken "
            "summary when you finish a task, hit a blocker, or need the user's attention while they "
            "are looking away from the terminal. Keep it to a few sentences: the point, the outcome, "
            "and the next step. Write for the ear, not the eye - the text is read verbatim, so no "
            "markdown, file paths, or code. OpenAI gpt-4o-mini-tts is multilingual and handles a "
            "Vietnamese sentence with English technical terms in it, so write those terms normally. "
            "Returns as soon as the audio starts unless wait is true."
        ),
        "inputSchema": SPEAK_SCHEMA,
    },
    {
        "name": "speak_batch",
        "description": (
            "Synthesise many texts into audio files at once, one file per item, without playing them. "
            "Use for narration, chapter audio, or any bulk voiceover job. On Vbee this goes through "
            "the async batch API (up to 100k characters per item) and polls until each file is ready."
        ),
        "inputSchema": SPEAK_BATCH_SCHEMA,
    },
    {
        "name": "list_voices",
        "description": "List available voice codes for the speak and speak_batch tools.",
        "inputSchema": LIST_VOICES_SCHEMA,
    },
]


def tool_speak(arguments):
    text = (arguments.get("text") or "").strip()
    if not text:
        raise TtsError("text is empty - nothing to say")

    audio = core.synthesize(
        text,
        provider=arguments.get("provider") or "auto",
        mode="realtime",
        voice=arguments.get("voice"),
        output_format="mp3",
        speed=arguments.get("speed", DEFAULT_SPEED),
        instructions=arguments.get("instructions"),
    )

    save_path = arguments.get("save_path")
    if save_path:
        target = Path(save_path)
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        handle = tempfile.NamedTemporaryFile(
            suffix=".mp3", prefix="speak-", dir=str(audio_scratch_dir()), delete=False
        )
        handle.close()
        target = Path(handle.name)
    target.write_bytes(audio)

    if arguments.get("play", True) is False:
        return f"Synthesised {len(audio)} bytes to {target} (not played)."

    if arguments.get("wait"):
        played = player.play(target)
        if not played:
            return f"Synthesised {target} but could not play it - {player.player_hint()}"
        return f"Spoke {len(text)} characters ({target})."

    enqueue_playback(target)
    return f"Speaking now: {len(text)} characters queued ({target})."


def tool_speak_batch(arguments):
    raw_items = arguments.get("items") or []
    if not raw_items:
        raise TtsError("items is empty - nothing to synthesise")

    items = []
    for index, entry in enumerate(raw_items, start=1):
        if not (entry.get("text") or "").strip():
            raise TtsError(f"items[{index - 1}] has no text")
        items.append(
            {
                "name": entry.get("name") or f"item-{index:03d}",
                "text": entry["text"],
                "voice": entry.get("voice"),
                "instructions": entry.get("instructions"),
            }
        )

    output_format = arguments.get("output_format") or "mp3"
    out_dir = Path(arguments.get("out_dir") or audio_scratch_dir() / "batch")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = core.synthesize_many(
        items,
        concurrency=int(arguments.get("concurrency") or 4),
        provider=arguments.get("provider") or "auto",
        mode="batch",
        voice=arguments.get("voice"),
        output_format=output_format,
        speed=arguments.get("speed", DEFAULT_SPEED),
    )

    lines = []
    failures = 0
    for entry in results:
        if entry.get("error"):
            failures += 1
            lines.append(f"FAILED {entry['name']}: {entry['error']}")
            continue
        path = out_dir / f"{entry['name']}.{output_format}"
        path.write_bytes(entry["audio"])
        lines.append(f"{path} ({len(entry['audio'])} bytes)")
    header = f"{len(results) - failures}/{len(results)} items written to {out_dir}"
    return "\n".join([header, *lines])


def tool_list_voices(arguments):
    entries = core.list_voices(
        provider=arguments.get("provider") or "auto",
        language_code=arguments.get("language") or None,
        gender=arguments.get("gender"),
        limit=int(arguments.get("limit") or 50),
    )
    search = (arguments.get("search") or "").lower()
    if search:
        entries = [
            entry
            for entry in entries
            if search in str(entry.get("code", "")).lower() or search in str(entry.get("name", "")).lower()
        ]
    if not entries:
        return "No voices matched."
    return "\n".join(
        f"{entry.get('code', '')}\t{entry.get('name', '')}\t"
        f"{entry.get('language_code', '')}\t{entry.get('gender', '')}"
        for entry in entries
    )


HANDLERS = {
    "speak": tool_speak,
    "speak_batch": tool_speak_batch,
    "list_voices": tool_list_voices,
}


def call_tool(name, arguments):
    handler = HANDLERS.get(name)
    if handler is None:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
    try:
        return {"content": [{"type": "text", "text": handler(arguments or {})}]}
    except TtsError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    except Exception as exc:
        log(traceback.format_exc())
        return {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}


def handle(message):
    method = message.get("method")
    if method == "initialize":
        requested = ((message.get("params") or {}).get("protocolVersion")) or PROTOCOL_VERSION
        return {
            "protocolVersion": requested if requested in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        params = message.get("params") or {}
        return call_tool(params.get("name"), params.get("arguments"))
    if method == "ping":
        return {}
    if method in ("resources/list", "prompts/list"):
        return {"resources": [], "prompts": []}
    raise ValueError(f"method not found: {method}")


def serve():
    stdin = sys.stdin
    stdout = sys.stdout
    log("ready")
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            log(f"dropping non-JSON line: {line[:120]}")
            continue

        if "id" not in message:
            continue

        try:
            response = {"jsonrpc": "2.0", "id": message["id"], "result": handle(message)}
        except ValueError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": message["id"],
                "error": {"code": -32601, "message": str(exc)},
            }
        except Exception as exc:
            log(traceback.format_exc())
            response = {
                "jsonrpc": "2.0",
                "id": message["id"],
                "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"},
            }

        stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        stdout.flush()


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        pass
