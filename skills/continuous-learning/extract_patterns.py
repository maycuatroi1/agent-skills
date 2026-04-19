#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def load_transcript(path):
    messages = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages


def role_of(msg):
    return msg.get("type") or msg.get("role") or ""


def extract_text(msg):
    content = msg.get("message", {}).get("content") if isinstance(msg.get("message"), dict) else None
    if content is None:
        content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            t = item.get("type")
            if t == "text":
                parts.append(item.get("text", ""))
            elif t == "tool_use":
                name = item.get("name", "?")
                inp = item.get("input") or {}
                cmd = inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
                parts.append(f"[tool:{name} {str(cmd)[:200]}]")
            elif t == "tool_result":
                tc = item.get("content", "")
                if isinstance(tc, list):
                    tc = " ".join(x.get("text", "") for x in tc if isinstance(x, dict))
                parts.append(f"[result:{str(tc)[:300]}]")
        return "\n".join(p for p in parts if p)
    return ""


def build_summary(messages, max_chars):
    chunks = []
    for m in messages:
        r = role_of(m)
        if r not in ("user", "assistant"):
            continue
        text = extract_text(m).strip()
        if not text:
            continue
        chunks.append(f"=== {r} ===\n{text[:3000]}")
    joined = "\n\n".join(chunks)
    if len(joined) > max_chars:
        half = max_chars // 2
        joined = joined[:half] + "\n\n[... truncated middle ...]\n\n" + joined[-half:]
    return joined


def build_prompt(summary, config):
    detect = ", ".join(config.get("patterns_to_detect", []))
    ignore = ", ".join(config.get("ignore_patterns", []))
    threshold = config.get("extraction_threshold", "medium")
    return f"""You analyze a Claude Code session transcript and extract reusable patterns worth saving as Agent Skills.

RULES:
- Only extract patterns that are NON-OBVIOUS and REUSABLE across future sessions.
- Skip ephemeral one-off fixes, simple typos, and issues caused by external APIs.
- Threshold is "{threshold}" (low = extract liberally, medium = selective, high = only high-value).
- Focus on: {detect}
- Ignore: {ignore}

OUTPUT FORMAT:
Return ONLY a JSON array. No prose, no code fences, no explanation.
Each element:
{{
  "name": "kebab-case-skill-name",
  "description": "one-line trigger description for skill frontmatter, written to match future requests",
  "pattern_type": "one of the detect categories",
  "body": "full markdown body for the skill, including When to use / How / Example sections"
}}

If nothing worth saving: return [].

=== TRANSCRIPT ===
{summary}
=== END ==="""


def call_claude(prompt, config):
    model = config.get("claude_model", "claude-haiku-4-5")
    timeout = int(config.get("claude_timeout_seconds", 300))
    env = os.environ.copy()
    env["CONTINUOUS_LEARNING_CHILD"] = "1"
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--model", model],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        print("claude -p timed out", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("claude CLI not found in PATH", file=sys.stderr)
        return []
    if proc.returncode != 0:
        print(f"claude -p failed rc={proc.returncode}: {proc.stderr[:500]}", file=sys.stderr)
        return []
    return parse_patterns(proc.stdout)


def parse_patterns(output):
    output = output.strip()
    if not output:
        return []
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", output, re.DOTALL)
    if fenced:
        output = fenced.group(1)
    match = re.search(r"\[\s*(?:\{.*?\}\s*,?\s*)*\]", output, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [p for p in data if isinstance(p, dict) and p.get("name") and p.get("body")]


def sanitize_name(name):
    s = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    return s or "unnamed"


def save_skill(skill, base_dir, auto_approve, session_id):
    target = Path(base_dir) / ("learned" if auto_approve else "learned/_pending")
    target.mkdir(parents=True, exist_ok=True)
    name = sanitize_name(skill["name"])
    skill_dir = target / name
    if skill_dir.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        skill_dir = target / f"{name}-{stamp}"
    skill_dir.mkdir(parents=True)
    desc = (skill.get("description") or "").replace("\n", " ").strip()
    frontmatter = (
        "---\n"
        f"name: {skill_dir.name}\n"
        f"description: {desc}\n"
        f"pattern_type: {skill.get('pattern_type', 'unknown')}\n"
        f"learned_at: {datetime.now().isoformat(timespec='seconds')}\n"
        f"source_session: {session_id}\n"
        "---\n\n"
    )
    (skill_dir / "SKILL.md").write_text(frontmatter + skill["body"].rstrip() + "\n", encoding="utf-8")
    return skill_dir


def mark_processed(base_dir, session_id):
    processed = Path(base_dir) / "learned" / ".processed"
    processed.mkdir(parents=True, exist_ok=True)
    (processed / session_id).write_text(datetime.now().isoformat(timespec="seconds"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    base = Path(args.cwd) / ".claude" / "skills"
    processed_marker = base / "learned" / ".processed" / args.session_id
    if processed_marker.exists():
        print(f"session {args.session_id} already processed")
        return

    messages = load_transcript(args.transcript)
    real = [m for m in messages if role_of(m) in ("user", "assistant")]
    min_len = int(config.get("min_session_length", 10))
    if len(real) < min_len:
        print(f"session too short ({len(real)} < {min_len})")
        mark_processed(base, args.session_id)
        return

    summary = build_summary(real, int(config.get("max_summary_chars", 40000)))
    prompt = build_prompt(summary, config)
    patterns = call_claude(prompt, config)

    if not patterns:
        print("no patterns extracted")
        mark_processed(base, args.session_id)
        return

    auto = bool(config.get("auto_approve", False))
    saved = []
    for p in patterns:
        try:
            path = save_skill(p, base, auto, args.session_id)
            saved.append(str(path))
        except Exception as e:
            print(f"failed to save {p.get('name')!r}: {e}", file=sys.stderr)

    mark_processed(base, args.session_id)
    print(f"saved {len(saved)} learned skill(s):")
    for s in saved:
        print(f"  {s}")


if __name__ == "__main__":
    main()
