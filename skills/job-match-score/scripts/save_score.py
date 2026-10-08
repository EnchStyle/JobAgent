#!/usr/bin/env python3
"""save_score.py : persist one fit score plus breakdown to jobs.db (job-match-score).

Claude does the reading and judging; this script only records the result. It clamps the score to
0..100, builds the score_breakdown JSON, reads the thresholds from config/scoring_rubric.md and
sets the status:

  band apply   score >= threshold_apply (60)        -> scored   (cv-tailor picks it up)
  band review  review_floor (50) <= score < 60       -> scored   (the user decides; no automatic CV)
  band skip    score < review_floor                  -> rejected

Two flags override the band while keeping the fit score on record:
  --reject-reason location|sales|expired|duplicate|other   -> rejected, band <reason>_reject
        (expired -> band expired). Pass --reason with the specific cause, e.g. "hybrid, Birmingham".
  --hold "why"   -> stays scored with band hold, so cv-tailor skips it until the user decides
        (for example a partnerships role with some new-business work).

Notes are appended as a dated line, never replaced. The script refuses to score a row with no
stored advert unless --allow-no-jd is given. No LLM call, no network.
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, config_loader  # noqa: E402

DEFAULT_THRESHOLD = 60
DEFAULT_REVIEW_FLOOR = 50
REJECT_REASONS = ("location", "sales", "expired", "duplicate", "other")


def _clamp(n):
    return max(0, min(100, int(n)))


def threshold_apply():
    try:
        return int(config_loader.scoring().get("threshold_apply", DEFAULT_THRESHOLD))
    except Exception:
        return DEFAULT_THRESHOLD


def review_floor():
    try:
        return int(config_loader.scoring().get("review_floor", DEFAULT_REVIEW_FLOOR))
    except Exception:
        return DEFAULT_REVIEW_FLOOR


def band_for(score, threshold=None, rfloor=None):
    threshold = threshold_apply() if threshold is None else threshold
    rfloor = review_floor() if rfloor is None else rfloor
    return "apply" if score >= threshold else "review" if score >= rfloor else "skip"


def append_note(existing, text):
    """Append a dated line to the notes field, keeping everything already there."""
    text = (text or "").strip()
    if not text:
        return existing
    line = f"{datetime.date.today().isoformat()} {text}"
    return (existing.rstrip() + " | " + line) if existing and existing.strip() else line


def build_breakdown(score, rationale, gaps=None, skills_score=None, experience_score=None):
    breakdown = {
        "fit_score": _clamp(score),
        "rationale": (rationale or "").strip(),
        "gaps": list(gaps or []),
    }
    if skills_score is not None:
        breakdown["skills_score"] = _clamp(skills_score)
    if experience_score is not None:
        breakdown["experience_score"] = _clamp(experience_score)
    return breakdown


def save_score(job_pk, score, rationale, gaps=None, skills_score=None, experience_score=None,
               con=None, db_path=None, threshold=None, require_jd=True,
               reject_reason=None, reason=None, hold=None, note=None):
    """Persist a fit score for one job. Returns {"id", "score", "band", "status"}."""
    score = _clamp(score)
    if reject_reason and reject_reason not in REJECT_REASONS:
        raise ValueError(f"reject_reason must be one of {REJECT_REASONS}")
    if reject_reason and hold:
        raise ValueError("use either reject_reason or hold, not both")
    breakdown = build_breakdown(score, rationale, gaps, skills_score, experience_score)
    band = band_for(score, threshold)
    status = "scored" if band in ("apply", "review") else "rejected"
    extra_note = note
    if reject_reason:
        band = "expired" if reject_reason == "expired" else f"{reject_reason}_reject"
        status = "rejected"
        breakdown["reject_reason"] = (reason or reject_reason).strip()
        extra_note = f"{band}: {reason or reject_reason}" + (f"; {note}" if note else "")
    elif hold:
        band = "hold"
        status = "scored"
        breakdown["hold"] = hold.strip()
        extra_note = f"hold for the user: {hold}" + (f"; {note}" if note else "")
    breakdown["band"] = band

    own = con is None
    if own:
        con = jobdb.connect(db_path)
    try:
        row = jobdb.get_by_id(con, job_pk)
        if row is None:
            raise ValueError(f"No job with id {job_pk}")
        if require_jd:
            desc = row["description"] if "description" in row.keys() else None
            if not (desc and str(desc).strip()):
                raise ValueError(
                    f"Refusing to score job {job_pk}: no advert stored. Read the advert first "
                    "(job-ingest, save_description.py), then score it.")
        jobdb.set_score(con, job_pk, score, breakdown, status=status)
        if extra_note:
            jobdb.update_status(con, job_pk, status, notes=append_note(row["notes"], extra_note))
    finally:
        if own:
            con.close()
    return {"id": int(job_pk), "score": score, "band": band, "status": status}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Persist a job fit score and breakdown to jobs.db.")
    ap.add_argument("--id", type=int, required=True, help="jobs.id")
    ap.add_argument("--score", type=int, required=True, help="fit score 0..100 (clamped)")
    ap.add_argument("--rationale", required=True,
                    help="requirement mapping: 'Met: ... Gaps: ...' (two to four lines)")
    ap.add_argument("--gaps", default="[]", help="JSON list of must-have requirements not evidenced")
    ap.add_argument("--skills-score", type=int, default=None)
    ap.add_argument("--experience-score", type=int, default=None)
    ap.add_argument("--reject-reason", choices=REJECT_REASONS, default=None,
                    help="reject regardless of fit; the fit score stays on record")
    ap.add_argument("--reason", default=None, help="the specific cause, e.g. 'hybrid, Birmingham'")
    ap.add_argument("--hold", default=None, help="keep for the user's decision; cv-tailor skips it")
    ap.add_argument("--note", default=None, help="extra note, appended with today's date")
    ap.add_argument("--allow-no-jd", action="store_true",
                    help="score without a stored advert (only if the user explicitly asks)")
    args = ap.parse_args(argv)
    try:
        gaps = json.loads(args.gaps)
    except json.JSONDecodeError as exc:
        ap.error("--gaps must be a JSON list: %s" % exc)
    if not isinstance(gaps, list):
        ap.error("--gaps must be a JSON list")
    try:
        result = save_score(
            args.id, args.score, args.rationale, gaps,
            skills_score=args.skills_score, experience_score=args.experience_score,
            require_jd=not args.allow_no_jd, reject_reason=args.reject_reason,
            reason=args.reason, hold=args.hold, note=args.note)
    except ValueError as exc:
        print(json.dumps({"id": args.id, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
