#!/usr/bin/env python3
import json


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


def content_items(msg):
    content = msg.get("message", {}).get("content") if isinstance(msg.get("message"), dict) else None
    if content is None:
        content = msg.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [i for i in content if isinstance(i, dict)]
    return []


def extract_text(msg):
    parts = []
    for item in content_items(msg):
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
    return "\n".join(p for p in parts if p)


def tool_uses(msg):
    out = []
    for item in content_items(msg):
        if item.get("type") == "tool_use":
            out.append({"name": item.get("name", "?"), "input": item.get("input") or {}})
    return out


def result_text(item):
    tc = item.get("content", "")
    if isinstance(tc, list):
        tc = " ".join(x.get("text", "") for x in tc if isinstance(x, dict))
    return str(tc)


def tool_results(msg):
    out = []
    for item in content_items(msg):
        if item.get("type") == "tool_result":
            out.append({"is_error": bool(item.get("is_error")), "text": result_text(item)})
    return out


def is_meta(msg):
    return bool(msg.get("isMeta")) or role_of(msg) not in ("user", "assistant")
