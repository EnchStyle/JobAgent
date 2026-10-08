#!/usr/bin/env python3
"""reapply_title_list.py : apply the current reject-title list to roles still at `found`.

Ingest applies the list in config/filters.md only to new cards. After the list changes (check it
first with audit_reject_titles.py and the evidence rule in config/filters.md), run this to drop
the unread roles whose title now matches an entry. Only rows at status `found` (advert not read)
are touched: a role that has been read is never rejected on its title. Each dropped row keeps the
matching entry in its notes, so the reason is on record.

  python3 skills/job-ingest/scripts/reapply_title_list.py           # dry run: counts per entry
  python3 skills/job-ingest/scripts/reapply_title_list.py --apply   # write; snapshot jobs.db first
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import config_loader, jobdb  # noqa: E402
import filters  # noqa: E402


def plan(con, cfg):
    """(id, title, entry, notes) for every unread row whose title matches the list."""
    out = []
    for r in con.execute("SELECT id, title, notes FROM jobs WHERE status='found' ORDER BY id"):
        rj, kw = filters.reject_title(r["title"], cfg)
        if rj:
            out.append((r["id"], r["title"], kw, r["notes"] or ""))
    return out


def apply(con, rows, today=None):
    today = today or datetime.date.today().isoformat()
    with jobdb.batch(con):
        for pk, _title, kw, notes in rows:
            note = (f"{today} reject-title list: title matches '{kw}' "
                    "(dropped before reading under config/filters.md)")
            jobdb.update_status(con, pk, "rejected", notes=(notes + " | " if notes else "") + note)
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="Apply the reject-title list to roles still at found.")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    ap.add_argument("--db", help="database path (default: the project's jobs.db)")
    a = ap.parse_args()
    con = jobdb.connect(a.db)
    rows = plan(con, config_loader.filters())
    by_entry = {}
    for _pk, _t, kw, _n in rows:
        by_entry[kw] = by_entry.get(kw, 0) + 1
    res = {"found_rows_matching": len(rows),
           "by_entry": dict(sorted(by_entry.items(), key=lambda x: (-x[1], x[0])))}
    if a.apply:
        res["rejected"] = apply(con, rows)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
