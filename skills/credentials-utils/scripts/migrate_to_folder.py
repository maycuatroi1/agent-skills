#!/usr/bin/env python3
import json
import os
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry import (
    CONFIG_PATH,
    CREDENTIALS_DIR,
    META_FIELDS,
    SPECS,
    dig,
)

HERE = Path(__file__).resolve().parent


def usage(exit_code=2):
    out = sys.stdout if exit_code == 0 else sys.stderr
    out.write(
        "usage: migrate_to_folder.py [--source PATH] [--dry-run] [--merge] [--strict] [--force]\n"
        "  Split an old flat omelet.json into the per-service credentials/ folder.\n"
        "  --source PATH   flat file to migrate (default $OMELET_CONFIG / ~/.omelet.json)\n"
        "  --dry-run       show the plan, write nothing\n"
        "  --merge         migrate INTO an existing folder, adding only keys not already present\n"
        "  --strict        abort on keys not mapped in _registry.SPECS (default: route to misc/)\n"
        "  --force         overwrite an existing non-empty folder (default: refuse unless --merge)\n"
    )
    sys.exit(exit_code)


def parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        s = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def misc_spec(key):
    return {
        "path": f"misc/{key}.json",
        "id": key,
        "service": key,
        "category": "misc",
        "type": "unknown",
        "lifetime": "unknown",
        "description": "(auto-migrated, unmapped key - review category/type)",
        "rotate": "",
        "keys": [key],
    }


def build_entry(spec, source, today):
    present = [k for k in spec["keys"] if k in source]
    flat = {k: source[k] for k in present}

    entry = {
        "id": spec["id"],
        "service": spec["service"],
        "category": spec["category"],
        "description": spec.get("description", ""),
        "type": spec.get("type", "api_key"),
        "lifetime": spec.get("lifetime", "stable"),
        "status": spec.get("status", "active"),
        "rotate": spec.get("rotate", ""),
        "added": today,
        "last_rotated": None,
        "expiry": None,
    }

    oauth = spec.get("oauth")
    if oauth:
        entry["oauth"] = oauth
        expiry = dig(flat, oauth["container"] + [oauth["expiry_field"]])
        entry["expiry"] = expiry
        dt = parse_iso(expiry)
        if dt is not None and dt < datetime.now(timezone.utc):
            entry["status"] = "expired"

    entry["flat"] = flat
    return entry, present


def write_entry(dest, entry):
    dest.parent.mkdir(parents=True, exist_ok=True)
    ordered = {k: entry[k] for k in META_FIELDS if k in entry}
    ordered["flat"] = entry["flat"]
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, dest)


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        usage(0)
    dry_run = "--dry-run" in args
    merge = "--merge" in args
    strict = "--strict" in args
    force = "--force" in args

    source_path = CONFIG_PATH
    source_value = None
    if "--source" in args:
        i = args.index("--source")
        if i + 1 >= len(args):
            usage()
        source_value = args[i + 1]
        source_path = Path(os.path.expanduser(source_value))

    known_flags = {"--dry-run", "--merge", "--strict", "--force", "--source"}
    for a in args:
        if a == source_value:
            continue
        if a.startswith("--") and a not in known_flags:
            sys.stderr.write(f"unknown option: {a}\n")
            usage()

    if not source_path.exists():
        sys.stderr.write(f"source config not found: {source_path}\n")
        sys.exit(1)

    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"invalid JSON in {source_path}: {e}\n")
        sys.exit(1)
    source = {k: v for k, v in source.items() if not k.startswith("_")}

    today = date.today().isoformat()

    covered = set()
    planned = []
    for spec in SPECS:
        entry, present = build_entry(spec, source, today)
        if present:
            covered.update(present)
            planned.append((spec["path"], entry, present, False))

    unmapped = sorted(set(source.keys()) - covered)
    if unmapped:
        if strict:
            sys.stderr.write(
                "ERROR (--strict): keys not mapped in _registry.SPECS:\n  "
                + ", ".join(unmapped)
                + "\nAdd them to a spec, or drop --strict to route them to misc/.\n"
            )
            sys.exit(1)
        for key in unmapped:
            entry, present = build_entry(misc_spec(key), source, today)
            planned.append((entry["category"] + "/" + key + ".json", entry, present, True))

    folder_has_files = CREDENTIALS_DIR.exists() and any(CREDENTIALS_DIR.rglob("*.json"))

    print(f"source: {source_path} ({len(source)} top-level keys)")
    print(f"target: {CREDENTIALS_DIR}{'  [MERGE]' if merge else ''}\n")

    to_write = []
    for path, entry, present, is_misc in planned:
        dest = CREDENTIALS_DIR / path
        action = "create"
        new_keys = present
        if merge and dest.exists():
            try:
                existing = json.loads(dest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {"flat": {}}
            existing_flat = existing.get("flat", {})
            new_keys = [k for k in present if k not in existing_flat]
            if not new_keys:
                continue
            for k in new_keys:
                existing_flat[k] = source[k]
            existing["flat"] = existing_flat
            existing["last_rotated"] = datetime.now(timezone.utc).isoformat()
            entry = existing
            action = "update"
        misc_flag = " [unmapped->misc]" if is_misc else ""
        dep_flag = " [DEPRECATED]" if entry.get("status") == "deprecated" else ""
        exp = f" expiry={entry['expiry']}" if entry.get("expiry") else ""
        print(f"  {action:6s} {path:40s} <- {', '.join(new_keys)}{misc_flag}{dep_flag}{exp}")
        to_write.append((dest, entry))

    if unmapped and not strict:
        print(f"\nnote: {len(unmapped)} unmapped key(s) routed to misc/ - review later: {', '.join(unmapped)}")

    if dry_run:
        print(f"\ndry-run: would write {len(to_write)} file(s)")
        return

    if not to_write:
        print("\nnothing to do (folder already up to date)")
        return

    if folder_has_files and not (merge or force):
        sys.stderr.write(
            f"\nrefusing: {CREDENTIALS_DIR} already has files.\n"
            "Use --merge (add missing keys) or --force (overwrite), or clear OMELET_DIR.\n"
        )
        sys.exit(1)

    backup = Path(str(source_path) + ".bak." + datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(source_path, backup)
    print(f"\nbacked up source -> {backup}")

    for dest, entry in to_write:
        write_entry(dest, entry)

    try:
        os.chmod(CREDENTIALS_DIR, 0o700)
        os.chmod(CREDENTIALS_DIR.parent, 0o700)
    except OSError:
        pass

    print(f"wrote {len(to_write)} file(s) to {CREDENTIALS_DIR}")
    print("next: python3 compile.py  (regenerate flat ~/.omelet.json), then doctor.py")


if __name__ == "__main__":
    main()
