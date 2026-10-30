"""Tests of the curator scripts on transcripts written here, in a home of their own.

python3 -m unittest discover -s skills/curator/tests
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import _context  # noqa: E402
import _figures  # noqa: E402
import _sources  # noqa: E402
import curator  # noqa: E402
from _redact import redact  # noqa: E402

LISTING = "\n".join(
    [
        '- deploy-tool: Deploy the app. Use when the user says "ship it" or "deploy now".',
        '- release-notes: Write release notes. Use when the user says "ship it".',
        "- execute-plan: Run a plan step by step.",
    ]
)


def jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")


def claude_session(root: str, index: int, *, blocked: bool = True, correction: str | None = None) -> list[dict]:
    """A Claude Code transcript: start-up attachments, a slash command, a blocked sleep, a skill, a big read."""
    base = {"cwd": root, "sessionId": f"s{index}", "entrypoint": "cli", "timestamp": f"2026-10-0{index}T10:00:00Z"}
    lines = [
        {
            **base,
            "type": "attachment",
            "attachment": {
                "type": "instructions",
                "files": [{"path": f"{root}/AGENTS.md", "type": "Project", "content": "x" * 400}],
            },
        },
        {**base, "type": "attachment", "attachment": {"type": "skill_listing", "content": LISTING}},
        {
            **base,
            "type": "attachment",
            "attachment": {
                "type": "mcp_instructions_delta",
                "addedNames": ["kg"],
                "addedBlocks": ["## kg\nuse kg_search"],
            },
        },
        {
            **base,
            "type": "user",
            "message": {
                "role": "user",
                "content": "<command-message>execute-plan</command-message>\n"
                "<command-name>/execute-plan</command-name>\n<command-args>demo</command-args>",
            },
        },
        {
            **base,
            "type": "assistant",
            "message": {
                "id": f"m{index}a",
                "model": "claude-test",
                "usage": {
                    "input_tokens": 10,
                    "cache_creation_input_tokens": 30000,
                    "cache_read_input_tokens": 0,
                    "output_tokens": 50,
                },
                "content": [
                    {
                        "type": "tool_use",
                        "id": f"t{index}1",
                        "name": "Bash",
                        "input": {"command": "sleep 60; tail -5 out.txt"},
                    },
                ],
            },
        },
        {
            **base,
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"t{index}1",
                        "is_error": blocked,
                        "content": "<tool_use_error>Blocked: sleep 60 followed by: tail -5 out.txt</tool_use_error>"
                        if blocked
                        else "ok",
                    }
                ],
            },
        },
        {
            **base,
            "type": "assistant",
            "message": {
                "id": f"m{index}b",
                "model": "claude-test",
                "usage": {
                    "input_tokens": 5,
                    "cache_creation_input_tokens": 100,
                    "cache_read_input_tokens": 30000,
                    "output_tokens": 20,
                },
                "content": [
                    {"type": "tool_use", "id": f"t{index}2", "name": "Skill", "input": {"skill": "deploy-tool"}},
                    {"type": "tool_use", "id": f"t{index}3", "name": "Read", "input": {"file_path": f"{root}/big.md"}},
                    {
                        "type": "tool_use",
                        "id": f"t{index}4",
                        "name": "Bash",
                        "input": {
                            "command": f"cd {root} && export PATH=/opt/venv/bin:$PATH && "
                            f"DSN=postgres://u@h/{index}0 pytest -q"
                        },
                    },
                    {
                        "type": "tool_use",
                        "id": f"t{index}5",
                        "name": "Bash",
                        "input": {
                            "command": "python3 - <<'EOF'\nimport yaml\n"
                            "print(yaml.safe_load(open('plans/active/demo.yaml')))\nEOF"
                        },
                    },
                ],
            },
        },
        {
            **base,
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": f"t{index}2", "content": "loaded"},
                    {"type": "tool_result", "tool_use_id": f"t{index}3", "content": "y" * 25000},
                    {"type": "tool_result", "tool_use_id": f"t{index}4", "content": "3 passed"},
                    {"type": "tool_result", "tool_use_id": f"t{index}5", "content": "{}"},
                ],
            },
        },
    ]
    if correction:
        lines.append({**base, "type": "user", "message": {"role": "user", "content": correction}})
    lines.append({**base, "type": "system", "subtype": "compact_boundary", "content": "Conversation compacted"})
    return lines


def codex_session(root: str, ident: str, imported: bool = False) -> list[dict]:
    turn = "external-import-turn-1" if imported else "turn-1"
    return [
        {
            "timestamp": "2026-10-05T10:00:00Z",
            "type": "session_meta",
            "payload": {"id": ident, "cwd": root, "originator": "Codex Desktop", "source": "vscode"},
        },
        {
            "timestamp": "2026-10-05T10:00:01Z",
            "type": "turn_context",
            "payload": {"turn_id": turn, "model": "gpt-test"},
        },
        {
            "timestamp": "2026-10-05T10:00:02Z",
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "turn_id": turn,
                "item": {"type": "UserMessage", "content": [{"type": "text", "text": "không, dùng uv thay vì pip"}]},
            },
        },
        {
            "timestamp": "2026-10-05T10:00:03Z",
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "turn_id": turn,
                "item": {
                    "type": "CommandExecution",
                    "command": ["/bin/zsh", "-lc", "pip install foo"],
                    "exit_code": 127,
                    "status": "failed",
                    "aggregated_output": "zsh: command not found: pip",
                },
            },
        },
        {
            "timestamp": "2026-10-05T10:00:04Z",
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "turn_id": turn,
                "item": {
                    "type": "McpToolCall",
                    "server": "kg",
                    "tool": "kg_search",
                    "status": "completed",
                    "result": {"content": [{"type": "text", "text": "hits"}], "isError": False},
                },
            },
        },
        {
            "timestamp": "2026-10-05T10:00:05Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {"input_tokens": 41000},
                    "total_token_usage": {"input_tokens": 41000, "cached_input_tokens": 1000, "output_tokens": 10},
                    "model_context_window": 200000,
                },
            },
        },
    ]


class Home(unittest.TestCase):
    """A machine of its own: a home, a Claude Code and a Codex directory, a curator state, and a harness root."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()  # runtimes record real paths: /private/var, not /var
        self.saved = {key: os.environ.get(key) for key in ("HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "CURATOR_STATE")}
        os.environ["HOME"] = str(base / "home")
        os.environ["CLAUDE_CONFIG_DIR"] = str(base / "home" / ".claude")
        os.environ["CODEX_HOME"] = str(base / "home" / ".codex")
        os.environ["CURATOR_STATE"] = str(base / "state")
        self.root = base / "home" / "work" / "harness"
        self.root.mkdir(parents=True)
        (self.root / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text(
            "# Map\n\nSee `docs/missing.md` and `CLAUDE.md`.\n\nStatus on 2026-10-01: step 3 pending.\n\n"
            "Always run the formatter before you commit any change at all.\n",
            encoding="utf-8",
        )
        claude = Path(os.environ["CLAUDE_CONFIG_DIR"])
        claude.mkdir(parents=True)
        (claude / "CLAUDE.md").write_text("Always run the formatter before you commit any change at all.\n")
        (claude / "skills" / "deploy-tool").mkdir(parents=True)
        (claude / "skills" / "deploy-tool" / "SKILL.md").write_text("---\nname: deploy-tool\n---\n")
        codex = Path(os.environ["CODEX_HOME"])
        codex.mkdir(parents=True)
        (codex / "AGENTS.md").write_text("Always run the formatter before you commit any change at all.\n")
        project = claude / "projects" / _sources.encode_path(str(self.root))
        for index in (1, 2, 3):
            jsonl(
                project / f"s{index}.jsonl",
                claude_session(str(self.root), index, correction="đừng dùng pip nữa" if index == 1 else None),
            )
        jsonl(
            project / "s1" / "subagents" / "agent-abc123.jsonl",
            [
                {"cwd": str(self.root), "type": "user", "isSidechain": True, "message": {"content": "find files"}},
                {
                    "cwd": str(self.root),
                    "type": "assistant",
                    "message": {
                        "id": "sub1",
                        "content": [{"type": "tool_use", "id": "x1", "name": "Grep", "input": {"pattern": "foo"}}],
                    },
                },
            ],
        )
        (project / "s1" / "subagents" / "agent-abc123.meta.json").write_text(json.dumps({"agentType": "Explore"}))
        other = claude / "projects" / (_sources.encode_path(str(self.root)) + "-other")
        jsonl(other / "s9.jsonl", claude_session(str(self.root) + "-other", 9))
        sessions = codex / "sessions" / "2026" / "10" / "05"
        jsonl(sessions / "rollout-2026-10-05-c1.jsonl", codex_session(str(self.root), "c1"))
        jsonl(sessions / "rollout-2026-10-05-c2.jsonl", codex_session(str(self.root), "c2", imported=True))
        jsonl(sessions / "rollout-2026-10-05-c3.jsonl", codex_session("/elsewhere", "c3"))

    def tearDown(self) -> None:
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def run_cli(self, *args: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            curator.main([*args, "--root", str(self.root)])
        return out.getvalue()

    def state(self) -> Path:
        return curator.state_dir(self.root)


class Sources(Home):
    def test_scope_reads_both_runtimes_and_skips_imports(self) -> None:
        sessions, skipped = _sources.load([str(self.root)], time.time() - 86400)
        keys = sorted(s.key for s in sessions)
        self.assertEqual(keys, ["claude:s1", "claude:s1/agent-abc123", "claude:s2", "claude:s3", "codex:c1"])
        self.assertEqual(skipped["codex:imported"], 1)
        self.assertEqual(skipped["claude:out_of_scope"], 1)

    def test_claude_session(self) -> None:
        session = _sources.read_claude(next(Path(os.environ["CLAUDE_CONFIG_DIR"]).rglob("s1.jsonl")))
        self.assertEqual(session.context[0], 30010)
        self.assertEqual(session.compactions, [len(claude_session(str(self.root), 1, correction="x"))])
        self.assertEqual([t.kind for t in session.turns], ["command", "prompt"])
        blocked = session.calls[0]
        self.assertTrue(blocked.failed)
        self.assertIn("Blocked", blocked.error)
        self.assertEqual(session.calls[1].skill, "deploy-tool")
        self.assertEqual(session.calls[2].output_chars, 25000)
        self.assertIn("skill_listing", session.loaded)
        self.assertEqual(session.mcp_servers, {"kg": len("## kg\nuse kg_search")})

    def test_subagent_has_parent_and_type(self) -> None:
        path = next(Path(os.environ["CLAUDE_CONFIG_DIR"]).rglob("agent-abc123.jsonl"))
        session = _sources.read_claude(path, parent="s1")
        self.assertEqual((session.kind, session.parent, session.agent_type), ("subagent", "s1", "Explore"))
        self.assertEqual(session.turns, [])

    def test_codex_session(self) -> None:
        session = _sources.read_codex(next(Path(os.environ["CODEX_HOME"]).rglob("*-c1.jsonl")))
        self.assertEqual((session.kind, session.cwd, session.window), ("interactive", str(self.root), 200000))
        self.assertEqual([c.tool for c in session.calls], ["shell", "mcp__kg__kg_search"])
        self.assertTrue(session.calls[0].failed)
        self.assertEqual(session.calls[0].command, "pip install foo")
        self.assertEqual(session.context, [41000])
        self.assertEqual(session.usage["cache_read"], 1000)

    def test_codex_fallback_without_items(self) -> None:
        path = Path(self.tmp.name) / "old.jsonl"
        jsonl(
            path,
            [
                {"type": "session_meta", "payload": {"id": "old", "cwd": str(self.root), "source": "cli"}},
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "shell",
                        "call_id": "c",
                        "arguments": json.dumps({"command": ["bash", "-lc", "make test"]}),
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": "c",
                        "output": json.dumps({"output": "boom", "metadata": {"exit_code": 2}}),
                    },
                },
                {"type": "event_msg", "payload": {"type": "user_message", "message": "run the tests"}},
            ],
        )
        session = _sources.read_codex(path)
        self.assertEqual(session.calls[0].command, "make test")
        self.assertTrue(session.calls[0].failed)
        self.assertEqual([t.text for t in session.turns], ["run the tests"])


class Figures(Home):
    def figures(self) -> dict:
        sessions, _ = _sources.load([str(self.root)], time.time() - 86400)
        return _figures.compute(sessions, min_sessions=3, root=str(self.root))

    def test_causes_and_errors(self) -> None:
        figures = self.figures()
        causes = {row["name"]: row["count"] for row in figures["causes"]}
        self.assertEqual(causes["harness_blocked"], 3)
        self.assertEqual(causes["missing_tool"], 1)
        bash = next(row for row in figures["tools"] if row["name"] == "Bash")
        self.assertEqual((bash["failed"], bash["calls"]), (3, 9))

    def test_repeated_commands_scripts_and_skills(self) -> None:
        figures = self.figures()
        names = [row["name"] for row in figures["commands"]]
        self.assertTrue(any("pytest -q" in name and "<n>" in name for name in names), names)
        self.assertEqual(figures["scripts"][0]["name"], "python3 script on plans/active/*.yaml")
        self.assertEqual(figures["scripts"][0]["sessions"], 3)
        skills = {row["name"]: row for row in figures["skills"]}
        self.assertEqual(skills["deploy-tool"]["sessions"], 3)
        self.assertEqual(skills["execute-plan"]["via"], {"slash": 3})

    def test_corrections_context_and_outputs(self) -> None:
        figures = self.figures()
        texts = [turn["text"] for turn in figures["corrections"]["turns"]]
        self.assertEqual(sorted(texts), ["không, dùng uv thay vì pip", "đừng dùng pip nữa"])
        self.assertEqual(figures["context"]["startup_tokens"]["claude:interactive"]["p50"], 30010)
        self.assertEqual(figures["context"]["compactions"]["claude:interactive"]["sessions"], 3)
        self.assertEqual(figures["outputs"]["big_count"], 3)
        self.assertEqual(figures["subagents"]["by_type"], {"Explore": 1})

    def test_programs_and_normalize(self) -> None:
        self.assertEqual(_figures.programs("cd /x && git -C repo push origin main | tee log"), ("git push", "tee"))
        self.assertEqual(_figures.main_program("ls && python -m pytest -q"), "python -m pytest")
        self.assertEqual(_figures.programs("FOO=1 sudo uv run pytest"), ("uv run",))
        self.assertEqual(_figures.normalize("cd /tmp && head -50 a.txt"), "head -<n> a.txt")
        self.assertIsNone(_figures.inline_script("python3 run.py"))
        self.assertEqual(
            _figures.inline_script("python3 -c 'import requests; print(1)'"), "python3 script using requests"
        )


class Context(Home):
    def test_inventory(self) -> None:
        inventory = _context.inventory(self.root, LISTING, {"skills": [{"name": "deploy-tool", "sessions": 3}]})
        files = {Path(f["path"]).name + ":" + f["scope"]: f for f in inventory["files"]}
        agents = files["AGENTS.md:import"]
        self.assertEqual(sorted(agents["runtimes"]), ["claude", "codex"])
        self.assertEqual(agents["smells"]["dated_lines"], 1)
        self.assertEqual([u["path"] for u in agents["smells"]["unresolved_paths"]], ["docs/missing.md"])
        # The rule sits in three files, but ~/.codex/AGENTS.md shares a runtime with only the project's AGENTS.md.
        places = inventory["duplicates"][0]["at"]
        self.assertEqual(len(places), 3)
        skills = inventory["skills"]
        self.assertEqual(skills["listed"], 3)
        self.assertEqual([row["name"] for row in skills["unused"]], ["release-notes", "execute-plan"])
        self.assertEqual(skills["overlapping_triggers"][0]["phrase"], "ship it")
        self.assertEqual({row["name"]: row["where"] for row in skills["largest"]}["deploy-tool"], "user")


class Cli(Home):
    def test_collect_report_show(self) -> None:
        out = self.run_cli("collect", "--days", "30")
        self.assertIn("5 sessions", out)
        report = (self.state() / "report.md").read_text()
        self.assertIn("## Context", report)
        self.assertIn("harness_blocked (environment): 3", report)
        shown = self.run_cli("show", "claude:s1:5")
        self.assertIn("tool_use Bash", shown)
        code = self.run_cli("show", "code:AGENTS.md:5")
        self.assertIn("5>", code)

    def test_propose_decide_outcomes(self) -> None:
        self.run_cli("collect", "--days", "30")
        draft = Path(self.tmp.name) / "p.md"
        draft.write_text(
            "---\ntitle: Point the status line at the plan\nlens: context\nkind: context\n"
            "target: AGENTS.md\nevidence:\n  - code:AGENTS.md:5\n  - claude:s2:5\n"
            "  - inventory:skills.unused\nmetric: file_chars:AGENTS.md\n---\n\n## Problem\n\ntoken "
            "ghp_abcdefghijklmnopqrstuvwxyz0123 in the text\n"
        )
        out = self.run_cli("propose", "--file", str(draft))
        ident = out.split()[0]
        self.assertIn("baseline file_chars:AGENTS.md", out)
        stored = (self.state() / "proposals" / f"{ident}.md").read_text()
        self.assertNotIn("abcdefghijklmnop", stored)
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.run_cli("propose", "--file", str(draft))
        self.run_cli("decide", ident, "applied", "--commit", "abc1234")
        self.assertIn("baseline", self.run_cli("outcomes"))
        events = [json.loads(line)["event"] for line in (self.state() / "ledger.jsonl").read_text().splitlines()]
        self.assertEqual(events, ["proposed", "applied"])

    def test_propose_refuses_missing_evidence(self) -> None:
        self.run_cli("collect", "--days", "30")
        draft = Path(self.tmp.name) / "bad.md"
        draft.write_text(
            "---\ntitle: Vague\nlens: context\nkind: docs\ntarget: README.md\nevidence:\n"
            "  - claude:nosuch:1\n  - code:nope.md\n---\nConsider adding more documentation.\n"
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(err):
            self.run_cli("propose", "--file", str(draft))
        self.assertIn("claude:nosuch:1", err.getvalue())
        self.assertIn("no file", err.getvalue())

    def draft(self, name: str, head: str, body: str = "## Problem\n\npip again.\n") -> Path:
        path = Path(self.tmp.name) / name
        path.write_text("---\n" + head + "---\n\n" + body, encoding="utf-8")
        return path

    def refused(self, path: Path) -> str:
        err = io.StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(err):
            self.run_cli("propose", "--file", str(path))
        return err.getvalue()

    CORRECTION = (
        "title: Stop pip in this harness\nlens: corrections\nkind: hook\ntarget: .claude/settings.json\n"
        "evidence:\n  - codex:c1:3\n  - codex:c1:4\n"
    )
    WHY = "## Why not higher\n\npip is on the PATH of every worker; it cannot be removed from the image.\n"

    def test_failing_example_required_for_a_correction(self) -> None:
        self.run_cli("collect", "--days", "30")
        err = self.refused(self.draft("c.md", self.CORRECTION + "guard: lint\n", self.WHY))
        for key in ("failing_ref", "failing_input", "failing_probe"):
            self.assertIn(f"missing {key}", err)

    def test_failing_example_must_quote_the_cited_line(self) -> None:
        self.run_cli("collect", "--days", "30")
        invented = self.CORRECTION + (
            "guard: lint\nfailing_ref: codex:c1:4\nfailing_input: pip install requests==2.0\n"
            "failing_probe: bash -lc 'pip --version'\n"
        )
        self.assertIn("failing_input is not in codex:c1:4", self.refused(self.draft("i.md", invented, self.WHY)))
        real = invented.replace("pip install requests==2.0", "pip install foo")
        out = self.run_cli("propose", "--file", str(self.draft("r.md", real, self.WHY)))
        self.assertIn("open (corrections, hook", out)
        stored = (self.state() / "proposals" / f"{out.split()[0]}.md").read_text()
        self.assertIn("failing_input: pip install foo", stored)

    def test_failing_example_from_a_hub_run(self) -> None:
        self.run_cli("collect", "--days", "30")
        head = self.CORRECTION + (
            "guard: lint\nfailing_ref: run:1273:42\nfailing_input: pip install foo --user\n"
            "failing_probe: evo-agents hub run logs 1273 --after 41 --kind tool_call\n"
        )
        self.assertIn("open", self.run_cli("propose", "--file", str(self.draft("h.md", head, self.WHY))))
        bad = head.replace("run:1273:42", "run:1273").replace("Stop pip", "Stop pip twice")
        self.assertIn("failing_ref run:1273", self.refused(self.draft("b.md", bad.replace("hook", "cli"), self.WHY)))

    def test_ladder_rung_required_and_justified(self) -> None:
        self.run_cli("collect", "--days", "30")
        example = (
            "failing_ref: codex:c1:4\nfailing_input: pip install foo\nfailing_probe: bash -lc 'pip --version'\n"
        )
        self.assertIn("missing guard", self.refused(self.draft("n.md", self.CORRECTION + example, self.WHY)))
        self.assertIn("guard is one of", self.refused(self.draft("x.md", self.CORRECTION + example + "guard: hook\n")))
        self.assertIn("Why not higher", self.refused(self.draft("w.md", self.CORRECTION + example + "guard: lint\n")))
        prose_hook = self.CORRECTION + example + "guard: prose\n"
        self.assertIn("guard prose is a change of kind", self.refused(self.draft("p.md", prose_hook, self.WHY)))
        rule = self.CORRECTION.replace("kind: hook", "kind: rule") + example + "guard: lint\n"
        self.assertIn("kind rule is prose", self.refused(self.draft("q.md", rule, self.WHY)))
        top = self.CORRECTION.replace("kind: hook", "kind: harness") + example + "guard: remove\n"
        self.assertIn("open", self.run_cli("propose", "--file", str(self.draft("t.md", top))))

    def test_ladder_optional_outside_the_failure_lenses(self) -> None:
        self.run_cli("collect", "--days", "30")
        head = "title: Shorter map\nlens: context\nkind: context\ntarget: AGENTS.md\nevidence:\n  - code:AGENTS.md:5\n"
        self.assertIn("open", self.run_cli("propose", "--file", str(self.draft("m.md", head))))

    def test_notice(self) -> None:
        self.assertIn("4 sessions", self.run_cli("notice", "--min", "3"))  # 3 Claude Code, 1 Codex
        self.run_cli("collect", "--days", "30")
        self.assertEqual(self.run_cli("notice", "--min", "1"), "")

    def test_backup(self) -> None:
        target = Path(self.run_cli("backup", str(self.root / "AGENTS.md")).strip())
        self.assertEqual(target.read_text(), (self.root / "AGENTS.md").read_text())


class Redaction(unittest.TestCase):
    def test_patterns(self) -> None:
        text = (
            "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123 curl -H 'Authorization: Bearer abcdefghijklmnop123' "
            "postgres://user:hunter22@db/x sk-ant-api03-abcdefgh AKIAABCDEFGHIJKLMNOP password: s3cretvalue"
        )
        clean = redact(text)
        for secret in (
            "abcdefghijklmnopqrstuvwxyz0123",
            "abcdefghijklmnop123",
            "hunter22",
            "api03-abcdefgh",
            "AKIAABCDEFGHIJKLMNOP",
            "s3cretvalue",
        ):
            self.assertNotIn(secret, clean)
        self.assertEqual(redact("git status --short"), "git status --short")


if __name__ == "__main__":
    unittest.main()
