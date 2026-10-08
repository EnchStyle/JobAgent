#!/usr/bin/env python3
"""Register a cover letter on a job WITHOUT changing its status.

Sets jobs.cover_letter_file only. Status transitions are owned by cv-verify, so this
reads the job's current status and re-applies it (via jobdb.update_status) while setting
the cover_letter_file field. Deterministic glue only: no LLM calls.

Filename convention: output/cover_letters/<company>_<role>_<jobid>.md (ascii-sanitised).

Usage:
  register_cover.py --id 12 --print-name        # print canonical path, touch nothing
  register_cover.py --id 12 --file <path>        # set cover_letter_file, keep status
  register_cover.py --id 12                       # derive canonical path, set it, keep status
"""
import re
import sys
import json
import argparse
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, paths


def _slug(s, maxlen=40):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return (s[:maxlen].strip("-")) or "na"


def cover_filename(company, role, job_id):
    return f"{_slug(company)}_{_slug(role)}_{job_id}.md"


def canonical_path(row):
    """Project-relative path, the same form every other row stores."""
    return "output/cover_letters/" + cover_filename(row["company"], row["title"], row["id"])


def main():
    ap = argparse.ArgumentParser(
        description="Set jobs.cover_letter_file without changing status.")
    ap.add_argument("--id", type=int, required=True, help="jobs.id primary key")
    ap.add_argument("--file", help="path to the saved cover letter .md (derived if omitted)")
    ap.add_argument("--print-name", action="store_true",
                    help="print the absolute path to write the letter to, and exit without touching the DB")
    args = ap.parse_args()

    con = jobdb.connect()
    try:
        row = jobdb.get_by_id(con, args.id)
        if row is None:
            raise SystemExit(f"No job with id {args.id}")
        path = args.file or canonical_path(row)
        if args.print_name:
            print(paths.data_path(path))  # absolute path to write the letter to
            return
        path = paths.to_relative(path)
        current_status = row["status"]
        jobdb.update_status(con, args.id, current_status, cover_letter_file=path)
    finally:
        con.close()

    print(json.dumps({
        "id": args.id,
        "status": current_status,
        "cover_letter_file": path,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
