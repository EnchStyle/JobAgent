#!/usr/bin/env python3
"""runlock.py : one pipeline run at a time.

A scheduled run and a manual run on the same folder would scrape the same searches twice and
write to jobs.db at the same time. Take the lock at the start of a run and release it at the end.

  python3 lib/runlock.py acquire --label scheduled   # exit 1 if another run holds the lock
  python3 lib/runlock.py release
  python3 lib/runlock.py status

A lock older than --stale-hours (default 6) is treated as left over from a run that stopped
without releasing it, and is taken over (the report says so).
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import paths  # noqa: E402

LOCK = paths.LOGS / "run.lock"


def _read():
    try:
        return json.loads(LOCK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def acquire(label="run", stale_hours=6):
    now = datetime.datetime.now()
    cur = _read()
    if cur:
        age = (now - datetime.datetime.fromisoformat(cur["since"])).total_seconds() / 3600
        if age < stale_hours:
            return {"acquired": False, "held_by": cur, "age_hours": round(age, 1)}
    paths.ensure_dirs()
    LOCK.write_text(json.dumps({"label": label, "since": now.isoformat(timespec="seconds")}), encoding="utf-8")
    return {"acquired": True, "took_over_stale": cur}


def release():
    cur = _read()
    if cur:
        try:
            LOCK.unlink()
        except OSError:  # a folder that refuses deletion: empty the file instead
            LOCK.write_text("", encoding="utf-8")
    return {"released": bool(cur)}


def main():
    ap = argparse.ArgumentParser(description="One pipeline run at a time.")
    ap.add_argument("action", choices=["acquire", "release", "status"])
    ap.add_argument("--label", default="run")
    ap.add_argument("--stale-hours", type=float, default=6)
    a = ap.parse_args()
    if a.action == "acquire":
        out = acquire(a.label, a.stale_hours)
        print(json.dumps(out))
        sys.exit(0 if out["acquired"] else 1)
    print(json.dumps(release() if a.action == "release" else {"lock": _read()}))


if __name__ == "__main__":
    main()
