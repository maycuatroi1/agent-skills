#!/usr/bin/env python3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry import CREDENTIALS_DIR, dig, load_entries

SOON = timedelta(minutes=10)


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


def find_expiry(entry):
    oauth = entry.get("oauth")
    if oauth:
        flat = entry.get("flat", {})
        val = dig(flat, oauth["container"] + [oauth["expiry_field"]])
        if val:
            return val
    return entry.get("expiry")


def first_secret_preview(entry):
    flat = entry.get("flat", {})
    for v in flat.values():
        if isinstance(v, str):
            s = v
        elif isinstance(v, dict):
            inner = next((x for x in v.values() if isinstance(x, str)), None)
            if inner is None:
                continue
            s = inner
        else:
            continue
        if len(s) <= 12:
            return "***"
        return f"{s[:4]}...{s[-4:]}"
    return "-"


def main():
    if not CREDENTIALS_DIR.exists():
        sys.stderr.write(f"credentials folder not found: {CREDENTIALS_DIR}\n")
        sys.stderr.write("run migrate_to_folder.py first.\n")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    rows = []
    expired = 0
    for path, entry in load_entries():
        rel = str(path.relative_to(CREDENTIALS_DIR))
        status = entry.get("status", "active")
        expiry = find_expiry(entry)
        dt = parse_iso(expiry)
        health = "ok"
        if status == "deprecated":
            health = "deprecated"
        elif dt is not None:
            if dt < now:
                health = "EXPIRED"
                expired += 1
            elif dt - now < SOON:
                health = "expiring"
        rows.append(
            {
                "file": rel,
                "service": entry.get("service", entry.get("id", "?")),
                "type": entry.get("type", "?"),
                "health": health,
                "expiry": expiry or "-",
                "secret": first_secret_preview(entry),
            }
        )

    rows.sort(key=lambda r: (r["health"] != "EXPIRED", r["file"]))

    fw = max((len(r["file"]) for r in rows), default=4)
    sw = max((len(r["service"]) for r in rows), default=7)
    tw = max((len(r["type"]) for r in rows), default=4)

    header = f"{'FILE'.ljust(fw)}  {'SERVICE'.ljust(sw)}  {'TYPE'.ljust(tw)}  {'HEALTH'.ljust(10)}  {'SECRET'.ljust(13)}  EXPIRY"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['file'].ljust(fw)}  {r['service'].ljust(sw)}  {r['type'].ljust(tw)}  "
            f"{r['health'].ljust(10)}  {r['secret'].ljust(13)}  {r['expiry']}"
        )

    print(f"\n{len(rows)} entries in {CREDENTIALS_DIR}")
    if expired:
        print(f"{expired} EXPIRED - run: python3 refresh_google_oauth.py --all")
        sys.exit(1)


if __name__ == "__main__":
    main()
