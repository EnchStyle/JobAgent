#!/usr/bin/env python3
"""Register a generated CV against a job.

Sets jobs.cv_file and advances status to 'cv_generated' (via jobdb.update_status).
Deterministic glue only: no LLM calls.

Every CV is generated fresh through the bundled uk-cv-writer skill,
so this no longer maintains a recycling index. --role-type/--keywords are accepted as
optional, informational labels only (echoed back, not persisted to any index).

Usage:
  register_cv.py --id 12 --cv-file output/cvs/Jordan-Bennett-CV-Acme-12.docx \
                 --role-type product --keywords "product,roadmap,analytics"
"""
import sys
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, paths


def main():
    ap = argparse.ArgumentParser(
        description="Set jobs.cv_file and advance status to cv_generated.")
    ap.add_argument("--id", type=int, required=True, help="jobs.id primary key")
    ap.add_argument("--cv-file", required=True, help="path to the saved .docx")
    ap.add_argument("--role-type", default="", help="informational label only (e.g. product, data)")
    ap.add_argument("--keywords", default="", help="informational label only; comma-separated")
    args = ap.parse_args()

    con = jobdb.connect()
    try:
        if jobdb.get_by_id(con, args.id) is None:
            raise SystemExit(f"No job with id {args.id}")
        args.cv_file = paths.to_relative(args.cv_file)
        jobdb.update_status(con, args.id, "cv_generated", cv_file=args.cv_file)
    finally:
        con.close()

    print(json.dumps({
        "id": args.id,
        "status": "cv_generated",
        "cv_file": args.cv_file,
        "role_type": args.role_type,
        "keywords": args.keywords,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
