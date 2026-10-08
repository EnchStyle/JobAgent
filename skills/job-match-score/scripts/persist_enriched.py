#!/usr/bin/env python3
"""persist_enriched.py : store a batch of adverts and scores in one call (job-match-score).

Use this instead of dozens of save_score.py calls when scoring a large batch. Input is a JSON list
of records; every field except id is optional unless noted:

  {"id": 12,
   "jd_text": "...advert text...",          # stored only when present (never blanks a stored advert)
   "salary_min": 40000, "salary_max": 50000, "salary_period": "annual",
   "closing_date": "2026-01-31",            # from the advert, so queues and reports sort by it
   "score": 64,                              # required unless the record only stores an advert
   "rationale": "Met: ... Gaps: ...",
   "gaps": ["..."],
   "skills_score": 70, "experience_score": 60,
   "reject_reason": "location|sales|expired|duplicate|other", "reason": "hybrid, Birmingham",
   "hold": "why the user should decide",
   "note": "anything else worth keeping"}

Each record goes through save_score.save_score, so bands, statuses and appended notes behave
exactly as they do for a single call. Prints a JSON report with counts and any per-record errors.
Usage: python3 skills/job-match-score/scripts/persist_enriched.py <records.json>
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import jobdb  # noqa: E402
import save_score as ss  # noqa: E402


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return
    if len(sys.argv) != 2:
        raise SystemExit("usage: persist_enriched.py <records.json>")
    recs = json.load(open(sys.argv[1], encoding="utf-8"))
    con = jobdb.init_db()
    jobdb.begin_batch(con)  # one commit for the whole file
    try:
        rep = {"records": 0, "adverts_stored": 0, "by_band": {}, "by_status": {}, "errors": []}
        for r in recs:
            rep["records"] += 1
            try:
                pk = int(r["id"])
                fields = {}
                if r.get("salary_min") is not None:
                    fields["salary_min"] = float(r["salary_min"])
                if r.get("salary_max") is not None:
                    fields["salary_max"] = float(r["salary_max"])
                    fields["salary_unknown"] = 0
                if r.get("salary_period"):
                    fields["salary_period"] = r["salary_period"]
                if r.get("closing_date"):
                    fields["closing_date"] = str(r["closing_date"])[:10]  # YYYY-MM-DD from the advert
                if r.get("jd_text"):
                    jobdb.set_description(con, pk, r["jd_text"], **fields)
                    rep["adverts_stored"] += 1
                elif fields:
                    jobdb.update_status(con, pk, jobdb.get_by_id(con, pk)["status"], **fields)
                if r.get("score") is None:
                    continue
                res = ss.save_score(pk, int(r["score"]), r.get("rationale", ""), gaps=r.get("gaps") or [],
                                    skills_score=r.get("skills_score"),
                                    experience_score=r.get("experience_score"), con=con,
                                    reject_reason=r.get("reject_reason"), reason=r.get("reason"),
                                    hold=r.get("hold"), note=r.get("note"))
                rep["by_band"][res["band"]] = rep["by_band"].get(res["band"], 0) + 1
                rep["by_status"][res["status"]] = rep["by_status"].get(res["status"], 0) + 1
            except Exception as e:  # report and carry on with the rest of the batch
                rep["errors"].append({"id": r.get("id"), "error": str(e)})
    finally:
        jobdb.end_batch(con)  # commit what was written, also after an error
    con.close()
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
