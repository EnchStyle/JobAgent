#!/usr/bin/env python3
"""list_unscored.py : emit jobs awaiting a fit score as a JSON array (pipeline stage 2).

Deterministic glue for the job-match-score skill. Reads jobs.db and prints one JSON
object per role at status 'found' (the default), carrying only the fields the scorer
needs to judge fit: id, title, company, location, work_mode, url, notes, source,
salary_unknown. Salary and location were already hard-filtered upstream in job-ingest,
so they are not scoring inputs; salary_unknown rides along only as a later manual-check
flag. No scoring happens here (that is Claude reading this output plus the profile).
"""
import sys
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb  # noqa: E402

FIELDS = [
    "id", "title", "company", "location", "work_mode",
    "url", "notes", "source", "salary_unknown", "date_posted",
]


def list_unscored(status="found", limit=None, con=None, db_path=None):
    """Return a list of job dicts at the given status (default 'found').

    Pass an open `con` (tests) or a `db_path`; otherwise the default jobs.db is used.
    Only the fields in FIELDS are emitted, so the scorer sees just what it needs.
    """
    own = con is None
    if own:
        con = jobdb.connect(db_path)
    try:
        rows = jobdb.get_by_status(con, status)
    finally:
        if own:
            con.close()
    out = []
    for r in rows:
        d = {k: r[k] for k in FIELDS}
        d["has_jd"] = 1 if (r["description"] if "description" in r.keys() else None) else 0
        out.append(d)
    if limit is not None:
        out = out[: max(0, int(limit))]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Emit jobs awaiting a fit score as a JSON array (stage 2 input)."
    )
    ap.add_argument("--status", default="found", help="status to list (default: found)")
    ap.add_argument("--limit", type=int, default=None, help="cap the number of rows returned")
    args = ap.parse_args(argv)
    print(json.dumps(list_unscored(args.status, args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
