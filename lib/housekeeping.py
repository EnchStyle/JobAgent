#!/usr/bin/env python3
"""housekeeping.py : keep the working folders tidy at the end of every pipeline run.

What it does (all reported as JSON; nothing in the tracker is touched):
  1. Lists scrape files still in inbox/ after --inbox-days (default 2). scrape_ingest.py archives
     every file it ingests, so a file left behind was not ingested (unreadable or never run):
     re-scrape that search or ingest it. Nothing is moved.
  2. Keeps only the newest --keep (default 3) tracker snapshots in backups/.
  3. Deletes unfinished downloads and LibreOffice export leftovers (*.tmp, *.crdownload, *.part,
     and the .tmpexp, .tmpexport and _tmp folders) in output/, if untouched for an hour.
A folder that refuses deletion is reported, not worked around.

Usage (from the project folder):
  python3 lib/housekeeping.py              # do it
  python3 lib/housekeeping.py --dry-run    # only report what would happen
"""
import sys
import json
import time
import shutil
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import paths, backup  # noqa: E402

PARTIAL = ("*.tmp", "*.crdownload", "*.part")
TEMP_DIRS = (".tmpexp", ".tmpexport", "_tmp")


def run(inbox_days=2, keep=3, dry_run=False):
    rep = {"inbox_not_ingested": [], "backups_removed": [], "partial_downloads_removed": [], "dry_run": dry_run}
    inbox = Path(paths.INBOX)
    cutoff = time.time() - inbox_days * 86400
    if inbox.is_dir():
        for f in sorted(inbox.glob("scrape_*.json")):
            if f.stat().st_mtime < cutoff:
                rep["inbox_not_ingested"].append(f.name)
    if dry_run:
        rep["backups_removed"] = [s.name for s in backup.snapshots()[:-keep]] if keep > 0 else []
    else:
        rep["backups_removed"] = backup.prune(keep)
    out = Path(paths.DATA) / "output"
    hour_ago = time.time() - 3600
    if out.is_dir():
        found = set()
        for pat in PARTIAL:
            found.update(out.rglob(pat))
        for name in TEMP_DIRS:
            found.update(out.rglob(name))
        # remove outermost paths only; their contents go with them
        tops = [f for f in sorted(found) if not any(p in found for p in f.parents)]
        for f in tops:
            try:
                if f.stat().st_mtime > hour_ago:
                    continue
            except OSError:
                continue
            rep["partial_downloads_removed"].append(str(f.relative_to(out)))
            if dry_run:
                continue
            try:
                shutil.rmtree(f) if f.is_dir() else f.unlink()
            except OSError as exc:
                rep["partial_downloads_removed"][-1] += f" (not removed: {exc.strerror})"
    return rep


def main():
    ap = argparse.ArgumentParser(description="End-of-run tidy: inbox check, backups, partial downloads.")
    ap.add_argument("--inbox-days", type=int, default=2)
    ap.add_argument("--keep", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(a.inbox_days, a.keep, a.dry_run), indent=2))


if __name__ == "__main__":
    main()
