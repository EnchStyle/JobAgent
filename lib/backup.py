#!/usr/bin/env python3
"""backup.py : snapshot jobs.db before a big run, keeping only the newest N snapshots.

Usage (from the project folder):
  python3 lib/backup.py --label preapply            # writes backups/jobs_<date>_<label>.db
  python3 lib/backup.py --label preapply --keep 3   # also removes older snapshots beyond 3
  python3 lib/backup.py --list

Uses SQLite's own backup API, so the copy is consistent even if the database is in use. Snapshots
live in backups/ inside the data folder (JOBAGENT_DATA_DIR, the project folder by default).
"""
import sys
import json
import sqlite3
import argparse
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import paths, jobdb  # noqa: E402

BACKUPS = paths.DATA / "backups"


def snapshots():
    return sorted(BACKUPS.glob("jobs_*.db")) if BACKUPS.is_dir() else []


def make(label="manual"):
    BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BACKUPS / f"jobs_{ts}_{label}.db"
    src = jobdb.connect()
    dst = sqlite3.connect(str(out))
    src.backup(dst)
    dst.close()
    src.close()
    return out


def prune(keep):
    removed = []
    for f in snapshots()[:-keep] if keep > 0 else []:
        try:
            f.unlink()
            removed.append(f.name)
        except OSError as exc:  # a folder that does not allow deletion: report, do not fail
            removed.append(f"{f.name} (not removed: {exc.strerror})")
    return removed


def main():
    ap = argparse.ArgumentParser(description="Snapshot jobs.db and keep the newest N snapshots.")
    ap.add_argument("--label", default="manual")
    ap.add_argument("--keep", type=int, default=0, help="keep this many snapshots (0 = keep all)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print(json.dumps([f.name for f in snapshots()], indent=2))
        return
    out = make(a.label)
    print(json.dumps({"snapshot": str(out), "removed": prune(a.keep)}, indent=2))


if __name__ == "__main__":
    main()
