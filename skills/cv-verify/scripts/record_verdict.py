#!/usr/bin/env python3
"""record_verdict.py : record the cv-verify verdict for one job in jobs.db.

Deterministic glue for the cv-verify skill. Claude runs the four checks and decides pass or
fail; this script only writes the outcome.

- pass : advance status to 'verified'. A re-score is stored in jobs.rescore (match_score keeps
         the original). If the re-score falls below threshold_apply, the row goes back to
         'scored' in the review band instead of 'verified', so the user decides. An optional
         note is appended too.
- fail : keep status at 'cv_generated' (so the CV can be fixed and re-verified) and append
         the specific fixes to jobs.notes, preserving any existing notes.

Prints JSON {id, status}. No LLM call, no network.
"""
import sys
import json
import datetime
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, config_loader  # noqa: E402


def _clamp(n):
    """Coerce to int and pin into the 0 to 100 band."""
    return max(0, min(100, int(n)))


def _append_notes(existing, addition):
    """Append a dated cv-verify line to any existing notes, keeping the old text."""
    stamp = datetime.date.today().isoformat()
    line = f"[cv-verify {stamp}] {(addition or '').strip()}"
    if existing and existing.strip():
        return existing.rstrip() + "\n" + line
    return line


def record_verdict(job_pk, result, notes=None, rescore=None, con=None, db_path=None):
    """Persist a pass/fail verdict for one job. Returns {"id", "status"}.

    Pass an open `con` (tests) or a `db_path`; otherwise the default jobs.db is used.
    """
    if result not in ("pass", "fail"):
        raise ValueError("result must be 'pass' or 'fail'")
    own = con is None
    if own:
        con = jobdb.connect(db_path)
    try:
        row = jobdb.get_by_id(con, job_pk)
        if row is None:
            raise SystemExit(f"No job with id {job_pk}")
        fields = {}
        if result == "pass":
            status = "verified"
            note = notes
            if rescore is not None:
                fields["rescore"] = _clamp(rescore)
                try:
                    thr = int(config_loader.scoring().get("threshold_apply", 60))
                except Exception:
                    thr = 60
                if fields["rescore"] < thr:
                    status = "scored"
                    bd = json.loads(row["score_breakdown"] or "{}") if row["score_breakdown"] else {}
                    bd["band"] = "review"
                    fields["score_breakdown"] = json.dumps(bd, ensure_ascii=False)
                    note = ((notes + "; ") if notes else "") + (
                        f"re-score {fields['rescore']} is below {thr}: moved to the review band")
            if note:
                fields["notes"] = _append_notes(row["notes"], note)
        else:
            status = "cv_generated"  # keep it here so it can be fixed and re-verified
            if notes:
                fields["notes"] = _append_notes(row["notes"], notes)
        jobdb.update_status(con, job_pk, status, **fields)
    finally:
        if own:
            con.close()
    return {"id": int(job_pk), "status": status}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Record the cv-verify pass/fail verdict for a job in jobs.db."
    )
    ap.add_argument("--id", type=int, required=True, help="job primary key (jobs.id)")
    ap.add_argument("--result", required=True, choices=["pass", "fail"],
                    help="pass advances to verified; fail keeps cv_generated and logs fixes")
    ap.add_argument("--notes", default=None,
                    help="the specific fixes (fail) or a note (pass), appended to jobs.notes")
    ap.add_argument("--rescore", type=int, default=None,
                    help="re-score 0 to 100, stored in jobs.rescore; below threshold_apply the row goes to review")
    args = ap.parse_args(argv)
    result = record_verdict(args.id, args.result, notes=args.notes, rescore=args.rescore)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
