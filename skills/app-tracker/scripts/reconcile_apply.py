"""reconcile_apply.py : mark a role applied by its board job reference.

An application-confirmation email carries the board's "Job Reference" (for example CV-Library
"Job Reference: 123456789"). That number is stored in jobs.job_id, so this reconciles the
confirmation to its row by matching on it, and sets status applied with the date.

Usage:
  python3 skills/app-tracker/scripts/reconcile_apply.py --ref 123456789 [--date 2026-01-15] \
    [--status applied] [--note "..."]
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="board job reference (matches jobs.job_id)")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="date_applied (ISO)")
    ap.add_argument("--status", default="applied", help="status to set (default applied)")
    ap.add_argument("--note", default=None, help="note appended with today's date; defaults to a stamp with the ref")
    a = ap.parse_args(argv)
    con = jobdb.init_db()
    row = con.execute(
        "SELECT id, title, company, status FROM jobs WHERE job_id=? OR url LIKE ?",
        (a.ref, f"%{a.ref}%"),
    ).fetchone()
    if not row:
        print(json.dumps({"ref": a.ref, "matched": False,
                          "hint": "no row with that job_id; scrape it first or check the reference"}))
        return
    note = a.note or f"applied via board, ref {a.ref}, on {a.date}"
    full = con.execute("SELECT notes, date_applied FROM jobs WHERE id=?", (row["id"],)).fetchone()
    stamp = f"{datetime.date.today().isoformat()} {note}"
    notes = (full["notes"].rstrip() + " | " + stamp) if full["notes"] and full["notes"].strip() else stamp
    fields = {"notes": notes}
    if not full["date_applied"]:
        fields["date_applied"] = a.date
    jobdb.update_status(con, row["id"], a.status, **fields)
    print(json.dumps({"ref": a.ref, "matched": True, "id": row["id"], "company": row["company"],
                      "title": row["title"], "status": a.status, "date": a.date}, ensure_ascii=False))


if __name__ == "__main__":
    main()
