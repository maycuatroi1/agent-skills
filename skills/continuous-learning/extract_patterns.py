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
                hint = inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
                parts.append(f"[tool:{name} {str(hint)[:300]}]")
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


def deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_project_config(cwd):
    candidates = [
        Path(cwd) / ".claude" / "continuous-learning.json",
        Path(cwd) / ".claude" / "continuous_learning.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"failed to load project config {p}: {e}", file=sys.stderr)
    return {}


def autodetect_cli(cwd):
    root = Path(cwd)
    for name in ("lms", "cli", "run", "dev", "bin/cli"):
        p = root / name
        if p.is_file() and os.access(p, os.X_OK):
            return {"entrypoint": f"./{name}", "autodetected": True}
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            scripts = list((data.get("scripts") or {}).keys())
            if scripts:
                return {
                    "entrypoint": "npm run <script>",
                    "framework": "npm scripts",
                    "existing_groups": scripts[:15],
                    "autodetected": True,
                }
        except Exception:
            pass
    makefile = root / "Makefile"
    if makefile.exists():
        return {"entrypoint": "make <target>", "framework": "Makefile", "autodetected": True}
    return None


def build_prompt(summary, config, project_cli):
    detect = ", ".join(config.get("patterns_to_detect", []))
    ignore = ", ".join(config.get("ignore_patterns", []))
    threshold = config.get("extraction_threshold", "medium")

    cli_section = ""
    if project_cli and project_cli.get("entrypoint"):
        cli_section = f"""
PROJECT CLI CONTEXT:
- Entrypoint: {project_cli.get("entrypoint")}
- Framework: {project_cli.get("framework", "unknown")}
- Module dir: {project_cli.get("module_dir", "(unspecified)")}
- Existing groups/commands: {project_cli.get("existing_groups", [])}
- Notes: {project_cli.get("notes", "")}

Produce "cli_suggestions" whenever you see a shell/tool-use pattern repeated (2+ times) with
structural similarity (same shape, different args). Propose a subcommand that fits this CLI's
conventions. Reuse existing groups when relevant; propose a new group only when no fit exists.
"""
    else:
        cli_section = "\nNo project CLI detected. Set cli_suggestions to [].\n"

    return f"""You analyze a Claude Code session transcript and extract two kinds of reusable artifacts:
(A) SKILLS — Agent Skill markdown files for non-obvious, reusable patterns.
(B) CLI_SUGGESTIONS — proposals to turn repeated shell/tool patterns into project CLI subcommands.

RULES:
- Only extract items that are NON-OBVIOUS and REUSABLE in FUTURE sessions.
- Skip ephemeral one-offs, simple typos, external-API outages.
- Threshold: "{threshold}" (low = extract liberally, medium = selective, high = only high-value).
- Focus: {detect}
- Ignore: {ignore}
{cli_section}
OUTPUT FORMAT — return ONLY a single JSON object. No prose, no code fences.
{{
  "skills": [
    {{
      "name": "kebab-case",
      "description": "one-line trigger-style description for frontmatter",
      "pattern_type": "one of the focus categories",
      "body": "markdown body with When-to-use / How / Example sections"
    }}
  ],
  "cli_suggestions": [
    {{
      "name": "kebab-case-suggestion-name",
      "command_path": "<entrypoint> <group> <subcommand> [ARGS]",
      "rationale": "what repeated pattern this replaces, why it's worth a subcommand",
      "occurrences": 3,
      "observed_calls": ["...actual command 1...", "...actual command 2..."],
      "proposed_location": "e.g. cli/modules/debug.py (add to existing debug group)",
      "implementation_sketch": "```python\\n@debug.command(\\"...\\")\\n...\\n```"
    }}
  ]
}}

If nothing worth saving: return {{"skills": [], "cli_suggestions": []}}.

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
        return {"skills": [], "cli_suggestions": []}
    except FileNotFoundError:
        print("claude CLI not found in PATH", file=sys.stderr)
        return {"skills": [], "cli_suggestions": []}
    if proc.returncode != 0:
        print(f"claude -p failed rc={proc.returncode}: {proc.stderr[:500]}", file=sys.stderr)
        return {"skills": [], "cli_suggestions": []}
    return parse_output(proc.stdout)


def parse_output(output):
    empty = {"skills": [], "cli_suggestions": []}
    if not output or not output.strip():
        return empty
    output = output.strip()

    fenced = re.search(r"```(?:json)?\s*([\{\[].*?[\]\}])\s*```", output, re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(output)
    obj_match = re.search(r"\{[\s\S]*\}", output)
    if obj_match:
        candidates.append(obj_match.group(0))
    arr_match = re.search(r"\[[\s\S]*\]", output)
    if arr_match:
        candidates.append(arr_match.group(0))

    for raw in candidates:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            skills = data.get("skills") or []
            suggestions = data.get("cli_suggestions") or []
            return {
                "skills": [s for s in skills if isinstance(s, dict) and s.get("name") and s.get("body")],
                "cli_suggestions": [c for c in suggestions if isinstance(c, dict) and c.get("name")],
            }
        if isinstance(data, list):
            return {
                "skills": [s for s in data if isinstance(s, dict) and s.get("name") and s.get("body")],
                "cli_suggestions": [],
            }
    return empty


def sanitize_name(name):
    s = re.sub(r"[^a-z0-9-]+", "-", (name or "").lower()).strip("-")
    return s or "unnamed"


def save_skill(skill, base_dir, auto_approve, session_id):
    target = Path(base_dir) / "skills" / ("learned" if auto_approve else "learned/_pending")
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


def save_cli_suggestion(sug, base_dir, auto_approve, session_id, project_cli):
    target = Path(base_dir) / "cli-suggestions" / ("accepted" if auto_approve else "_pending")
    target.mkdir(parents=True, exist_ok=True)
    name = sanitize_name(sug["name"])
    out_file = target / f"{name}.md"
    if out_file.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_file = target / f"{name}-{stamp}.md"

    observed = sug.get("observed_calls") or []
    observed_md = "\n".join(f"- `{str(c)[:400]}`" for c in observed) or "- (none captured)"
    framework = (project_cli or {}).get("framework", "unknown")
    entrypoint = (project_cli or {}).get("entrypoint", "?")
    sketch = sug.get("implementation_sketch") or ""
    if sketch and "```" not in sketch:
        sketch = f"```\n{sketch}\n```"

    frontmatter = (
        "---\n"
        f"name: {name}\n"
        f'command_path: "{sug.get("command_path", "")}"\n'
        f"occurrences: {sug.get('occurrences', 0)}\n"
        f'framework: "{framework}"\n'
        f'entrypoint: "{entrypoint}"\n'
        f'proposed_location: "{sug.get("proposed_location", "")}"\n'
        f"learned_at: {datetime.now().isoformat(timespec='seconds')}\n"
        f"source_session: {session_id}\n"
        "---\n\n"
    )
    body = (
        f"# CLI Suggestion: `{sug.get('command_path', name)}`\n\n"
        f"## Why\n{sug.get('rationale', '(no rationale)')}\n\n"
        f"## Observed calls ({sug.get('occurrences', 0)}x)\n{observed_md}\n\n"
        f"## Proposed location\n`{sug.get('proposed_location', '(unspecified)')}`\n\n"
        f"## Implementation sketch\n{sketch}\n"
    )
    out_file.write_text(frontmatter + body, encoding="utf-8")
    return out_file


def mark_processed(base_dir, session_id):
    processed = Path(base_dir) / "skills" / "learned" / ".processed"
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
        global_config = json.load(f)

    project_config = load_project_config(args.cwd)
    config = deep_merge(global_config, project_config)

    project_cli = (project_config.get("cli") if project_config else None) or autodetect_cli(args.cwd)

    base = Path(args.cwd) / ".claude"
    processed_marker = base / "skills" / "learned" / ".processed" / args.session_id
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
    prompt = build_prompt(summary, config, project_cli)
    result = call_claude(prompt, config)

    skills = result.get("skills", [])
    suggestions = result.get("cli_suggestions", [])
    if not skills and not suggestions:
        print("no patterns or CLI suggestions extracted")
        mark_processed(base, args.session_id)
        return

    auto = bool(config.get("auto_approve", False))
    saved_skills = []
    for p in skills:
        try:
            saved_skills.append(str(save_skill(p, base, auto, args.session_id)))
        except Exception as e:
            print(f"failed to save skill {p.get('name')!r}: {e}", file=sys.stderr)

    saved_suggestions = []
    for s in suggestions:
        try:
            saved_suggestions.append(str(save_cli_suggestion(s, base, auto, args.session_id, project_cli)))
        except Exception as e:
            print(f"failed to save suggestion {s.get('name')!r}: {e}", file=sys.stderr)

    mark_processed(base, args.session_id)
    print(f"saved {len(saved_skills)} skill(s), {len(saved_suggestions)} CLI suggestion(s)")
    for s in saved_skills:
        print(f"  skill: {s}")
    for s in saved_suggestions:
        print(f"  cli:   {s}")


if __name__ == "__main__":
    main()
