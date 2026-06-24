#!/usr/bin/env python3
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry import (
    CONFIG_PATH,
    CREDENTIALS_DIR,
    GENERATED_NOTE,
    deep_merge,
    load_entries,
)


def main():
    include_legacy = "--include-legacy" in sys.argv

    if not CREDENTIALS_DIR.exists():
        sys.stderr.write(f"credentials folder not found: {CREDENTIALS_DIR}\n")
        sys.stderr.write("run migrate_to_folder.py first.\n")
        sys.exit(1)

    merged = {}
    count = 0
    skipped = []
    for path, entry in load_entries():
        flat = entry.get("flat")
        if not isinstance(flat, dict):
            continue
        if entry.get("status") == "deprecated" and not include_legacy:
            skipped.append(entry.get("id", path.name))
            continue
        deep_merge(merged, flat)
        count += 1

    out = {"_generated": GENERATED_NOTE}
    out.update(merged)

    tmp = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(CONFIG_PATH.parent), encoding="utf-8"
    )
    try:
        json.dump(out, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
        tmp.close()
        os.chmod(tmp.name, 0o600)
        os.replace(tmp.name, CONFIG_PATH)
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise

    msg = f"compiled {count} entries -> {CONFIG_PATH}"
    if skipped:
        msg += f" (skipped {len(skipped)} deprecated: {', '.join(skipped)})"
    sys.stderr.write(msg + "\n")


if __name__ == "__main__":
    main()
