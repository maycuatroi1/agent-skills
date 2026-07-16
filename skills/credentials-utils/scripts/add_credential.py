#!/usr/bin/env python3
import getpass
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry import (
    CREDENTIALS_DIR,
    META_FIELDS,
    load_entries,
    spec_for_flat_key,
)

HERE = Path(__file__).resolve().parent


def usage():
    sys.stderr.write(
        "usage: add_credential.py <key.path> [source] [--json]\n"
        "  writes into the per-service file under credentials/, then recompiles ~/.omelet.json\n"
        "  source (one of):\n"
        "    (omitted)             prompt interactively without echo (recommended)\n"
        "    --from-stdin          read value from stdin\n"
        "    --from-env VAR_NAME   read value from environment variable\n"
        "    --value VALUE         inline value (avoid: leaks to shell history)\n"
        "  --json                  parse value as JSON (bool/number/object/array)\n"
        "examples:\n"
        "    add_credential.py openai_api_key\n"
        "    add_credential.py rclone.token.access_token --from-stdin\n"
        "    add_credential.py use_gcs --value true --json\n"
    )
    sys.exit(2)


def find_file_for_top_key(top_key):
    for path, entry in load_entries():
        if top_key in entry.get("flat", {}):
            return path, entry
    spec = spec_for_flat_key(top_key)
    if spec:
        path = CREDENTIALS_DIR / spec["path"]
        if path.exists():
            return path, json.loads(path.read_text(encoding="utf-8"))
        entry = {
            "id": spec["id"],
            "service": spec["service"],
            "category": spec["category"],
            "description": spec.get("description", ""),
            "type": spec.get("type", "api_key"),
            "lifetime": spec.get("lifetime", "stable"),
            "status": spec.get("status", "active"),
            "rotate": spec.get("rotate", ""),
            "added": None,
            "last_rotated": None,
            "expiry": None,
            "flat": {},
        }
        if spec.get("oauth"):
            entry["oauth"] = spec["oauth"]
        return path, entry
    path = CREDENTIALS_DIR / "tools" / f"{top_key}.json"
    entry = {
        "id": top_key,
        "service": top_key,
        "category": "tools",
        "description": "(added via add_credential.py)",
        "type": "api_key",
        "lifetime": "stable",
        "status": "active",
        "rotate": "",
        "added": None,
        "last_rotated": None,
        "expiry": None,
        "flat": {},
    }
    return path, entry


def write_entry(path, entry):
    ordered = {k: entry[k] for k in META_FIELDS if k in entry}
    ordered["flat"] = entry["flat"]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def main():
    args = sys.argv[1:]
    if not args:
        usage()

    key_path = args[0]
    rest = args[1:]

    parse_json = False
    if "--json" in rest:
        parse_json = True
        rest.remove("--json")

    if not rest:
        value = getpass.getpass(f"value for {key_path} (no echo): ")
        if not value:
            sys.stderr.write("empty value, aborting\n")
            sys.exit(1)
    elif rest[0] == "--from-stdin":
        if len(rest) != 1:
            usage()
        value = sys.stdin.read().rstrip("\n")
    elif rest[0] == "--from-env":
        if len(rest) != 2:
            usage()
        if rest[1] not in os.environ:
            sys.stderr.write(f"env var {rest[1]} not set\n")
            sys.exit(1)
        value = os.environ[rest[1]]
    elif rest[0] == "--value":
        if len(rest) != 2:
            usage()
        value = rest[1]
    else:
        usage()

    if parse_json:
        try:
            value = json.loads(value)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"--json: failed to parse value: {e}\n")
            sys.exit(1)

    parts = key_path.split(".")
    if not all(parts):
        sys.stderr.write(f"invalid key path: {key_path}\n")
        sys.exit(1)

    path, entry = find_file_for_top_key(parts[0])
    flat = entry.setdefault("flat", {})

    cursor = flat
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    leaf = parts[-1]
    existed = leaf in cursor
    cursor[leaf] = value

    tz = timezone(timedelta(hours=7))
    entry["last_rotated"] = datetime.now(tz).isoformat()
    if entry.get("added") is None:
        entry["added"] = datetime.now(tz).date().isoformat()

    write_entry(path, entry)
    subprocess.run([sys.executable, str(HERE / "compile.py")], check=False)

    verb = "updated" if existed else "added"
    rel = path.relative_to(CREDENTIALS_DIR) if str(path).startswith(str(CREDENTIALS_DIR)) else path
    sys.stderr.write(f"{verb} {key_path} in {rel}, recompiled flat config\n")


if __name__ == "__main__":
    main()
