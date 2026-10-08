"""Store the full job description for a candidate role (enrichment step).

The JD is fetched by Cowork at runtime by opening the job page for EVERY found row (CV-Library, Reed, Indeed and LinkedIn alike, all read from their websites). This script writes that text into
jobs.description and can update salary from the enriched figures. Use --requeue to send the row
back to status found so job-match-score re-scores it against the full JD.
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
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--file")
    ap.add_argument("--text")
    ap.add_argument("--salary-min", type=float)
    ap.add_argument("--salary-max", type=float)
    ap.add_argument("--salary-period")
    ap.add_argument("--requeue", action="store_true")
    ap.add_argument("--closing-date", help="YYYY-MM-DD closing date stated in the advert")
    a = ap.parse_args()
    desc = open(a.file, encoding="utf-8").read() if a.file else (a.text or "")
    con = jobdb.init_db()
    fields = {}
    if a.salary_min is not None:
        fields["salary_min"] = a.salary_min
    if a.salary_max is not None:
        fields["salary_max"] = a.salary_max
        fields["salary_unknown"] = 0
    if a.salary_period:
        fields["salary_period"] = a.salary_period
    if a.closing_date:
        fields["closing_date"] = a.closing_date[:10]
    jobdb.set_description(con, a.id, desc, **fields)
    # A very short advert, or one that ends in a "show more" stub, was probably cut off by the
    # board (guest pages often are): flag it so the employer's own page is read before scoring.
    tail = desc.strip()[-60:].lower()
    truncated = len(desc.strip()) < 600 or any(s in tail for s in ("show more", "see more", "…", "...", "mehr anzeigen"))
    if truncated:
        row = con.execute("SELECT notes FROM jobs WHERE id=?", (a.id,)).fetchone()
        old = (row["notes"] if row else "") or ""
        if "advert_maybe_truncated" not in old:
            con.execute("UPDATE jobs SET notes=? WHERE id=?", ((old + " | " if old else "") + "advert_maybe_truncated", a.id))
            con.commit()
    if a.requeue:
        row = con.execute("SELECT notes FROM jobs WHERE id=?", (a.id,)).fetchone()
        old = (row["notes"] if row else "") or ""
        jobdb.update_status(con, a.id, "found", notes=(old + " | " if old else "") + "enriched_full_jd")
    print(json.dumps({"id": a.id, "desc_chars": len(desc), "salary_updated": bool(fields), "requeued": a.requeue,
                      "closing_date": a.closing_date, "maybe_truncated": truncated}))


if __name__ == "__main__":
    main()
