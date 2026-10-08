#!/usr/bin/env python3
"""cv-tailor: list jobs ready for a CV.

Ready = status 'scored', match_score >= threshold_apply (config/scoring_rubric.md, default 60),
and not held for the user (band 'hold'). Review-band rows (50 to 59) are not listed: they get a CV
only when the user names them. Prints a JSON array with id, title, company, location, url, notes,
match_score, band, has_jd (read the advert itself with tracker.py show --id N). A one-line summary
goes to stderr so stdout stays pure JSON. Read-only.
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, config_loader  # noqa: E402

FIELDS = ["id", "title", "company", "location", "url", "notes", "match_score"]


def _band(r):
    try:
        return (json.loads(r["score_breakdown"] or "{}") or {}).get("band")
    except Exception:
        return None


def eligible(con, threshold):
    out = []
    for r in jobdb.get_by_status(con, "scored"):
        score = r["match_score"]
        band = _band(r)
        if score is None or int(score) < threshold or band == "hold":
            continue
        d = {k: r[k] for k in FIELDS}
        d["band"] = band
        d["has_jd"] = 1 if (r["description"] or "").strip() else 0
        d["closing_date"] = r["closing_date"] if "closing_date" in r.keys() else None
        out.append(d)
    # Roles that close soonest first; roles with no stated closing date after them.
    out.sort(key=lambda d: (d["closing_date"] is None, d["closing_date"] or "", -(d.get("match_score") or 0)))
    return out


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return
    threshold = int(config_loader.scoring().get("threshold_apply", 60))
    con = jobdb.connect()
    try:
        jobs = eligible(con, threshold)
    finally:
        con.close()
    sys.stderr.write(f"{len(jobs)} job(s) ready for a CV (scored, >= {threshold}, not on hold)\n")
    print(json.dumps(jobs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
