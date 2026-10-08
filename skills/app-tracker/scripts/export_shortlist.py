"""Export a clean, ranked shortlist of the roles worth pursuing.

Only includes the active pipeline (scored at or above threshold and beyond); the rejected
outsiders and not-yet-scored rows are left out. Score and rationale come first so the table is
readable in Excel. The `reference` column is the board's job reference (jobs.job_id), which is
what appears in application-confirmation emails, so applications can be reconciled by it. The
cv_file / cover_letter_file columns map each role to its generated documents in output/.
Written as UTF-8 with BOM so Excel shows accented titles correctly.
"""
import sys
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, paths

ACTIVE = ("found", "scored", "cv_generated", "verified", "applied", "interview")


def fmt_salary(r):
    if r["salary_unknown"] or (r["salary_min"] is None and r["salary_max"] is None):
        return "not stated"
    def n(x):
        return str(int(x)) if x is not None else ""
    rng = n(r["salary_min"]) + (" to " + n(r["salary_max"]) if r["salary_max"] else "")
    cur = r["salary_currency"] or ""
    per = "/" + r["salary_period"] if r["salary_period"] else ""
    return f"{cur} {rng}{per}".strip()


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return
    con = jobdb.init_db()
    q = "SELECT * FROM jobs WHERE status IN (%s) ORDER BY (match_score IS NULL), match_score DESC, source, id" % ",".join("?" * len(ACTIVE))
    rows = con.execute(q, ACTIVE).fetchall()
    out = paths.OUTPUT / "shortlist.csv"
    cols = ["rank", "score", "title", "company", "source", "reference", "location", "work_mode",
            "salary", "status", "date_applied", "cv_file", "cover_letter_file",
            "rationale", "gaps", "flags", "url"]
    bn = lambda p: (p or "").replace("\\", "/").split("/")[-1]
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i, r in enumerate(rows, 1):
            try:
                bd = json.loads(r["score_breakdown"] or "{}")
            except Exception:
                bd = {}
            w.writerow([i, (r["match_score"] if r["match_score"] is not None else "not scored (read JD)"),
                        r["title"], r["company"], r["source"], r["job_id"] or "", r["location"],
                        r["work_mode"] or "", fmt_salary(r), r["status"], r["date_applied"] or "",
                        bn(r["cv_file"]), bn(r["cover_letter_file"]),
                        bd.get("rationale", ""), "; ".join(bd.get("gaps", []) or []),
                        r["notes"] or "", r["url"]])
    print("wrote", out, "| shortlisted rows:", len(rows))


if __name__ == "__main__":
    main()
