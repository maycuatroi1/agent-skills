#!/usr/bin/env python3
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("OMELET_CONFIG", str(Path.home() / ".omelet.json")))


def usage():
    sys.stderr.write(
        "usage: add_credential.py <key.path> [source] [--json]\n"
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

    value = None
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
        env_name = rest[1]
        if env_name not in os.environ:
            sys.stderr.write(f"env var {env_name} not set\n")
            sys.exit(1)
        value = os.environ[env_name]
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

    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            sys.stderr.write(f"invalid JSON in {CONFIG_PATH}: {e}\n")
            sys.exit(1)
    else:
        data = {}

    parts = key_path.split(".")
    if not all(parts):
        sys.stderr.write(f"invalid key path: {key_path}\n")
        sys.exit(1)

    cursor = data
    for part in parts[:-1]:
        if part not in cursor:
            cursor[part] = {}
        elif not isinstance(cursor[part], dict):
            sys.stderr.write(
                f"cannot descend into '{part}': existing value is {type(cursor[part]).__name__}\n"
            )
            sys.exit(1)
        cursor = cursor[part]

    leaf = parts[-1]
    existed = leaf in cursor
    cursor[leaf] = value

    tmp = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(CONFIG_PATH.parent), encoding="utf-8"
    )
    try:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
        tmp.close()
        os.chmod(tmp.name, 0o600)
        os.replace(tmp.name, CONFIG_PATH)
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise

    verb = "updated" if existed else "added"
    sys.stderr.write(f"{verb} {key_path} in {CONFIG_PATH}\n")


if __name__ == "__main__":
    main()
