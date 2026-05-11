#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("OMELET_CONFIG", str(Path.home() / ".omelet.json")))


def usage():
    sys.stderr.write("usage: get_credential.py [--export VAR_NAME] <key.path>\n")
    sys.exit(2)


def main():
    args = sys.argv[1:]
    export_var = None

    if not args:
        usage()

    if args[0] == "--export":
        if len(args) != 3:
            usage()
        export_var = args[1]
        key_path = args[2]
    elif len(args) == 1:
        key_path = args[0]
    else:
        usage()

    if not CONFIG_PATH.exists():
        sys.stderr.write(f"config not found: {CONFIG_PATH}\n")
        sys.exit(1)

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"invalid JSON in {CONFIG_PATH}: {e}\n")
        sys.exit(1)

    cursor = data
    for part in key_path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            sys.stderr.write(f"key not found: {key_path} (failed at '{part}')\n")
            sys.exit(1)
        cursor = cursor[part]

    if isinstance(cursor, (dict, list)):
        sys.stdout.write(json.dumps(cursor, ensure_ascii=False))
        sys.stdout.write("\n")
        return

    value = str(cursor)

    if export_var is not None:
        escaped = value.replace("'", "'\\''")
        sys.stdout.write(f"export {export_var}='{escaped}'\n")
        return

    sys.stdout.write(value)
    if sys.stdout.isatty():
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
