"""Emit job_ids already tracked, so a scrape can skip roles it has already ingested.

Every board embeds the role id in its URL (CV-Library /job/{id},
Reed /jobs/.../{id}); that id is stored as jobs.job_id. Feeding this list into the browser
(sessionStorage['__known']) lets the extractors skip known ids, so no role is re-scraped or its
JD re-read. Final dedup is still enforced by the UNIQUE index in lib/jobdb; this just saves work.

Usage: known_ids.py [--source reed]  ->  JSON array of job_id strings.
"""
import sys
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    a = ap.parse_args()
    con = jobdb.connect()
    if a.source:
        rows = con.execute("SELECT job_id FROM jobs WHERE source=? AND job_id IS NOT NULL", (a.source,)).fetchall()
    else:
        rows = con.execute("SELECT job_id FROM jobs WHERE job_id IS NOT NULL").fetchall()
    print(json.dumps([str(r[0]) for r in rows]))


if __name__ == "__main__":
    main()
