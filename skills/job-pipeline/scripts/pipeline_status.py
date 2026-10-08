#!/usr/bin/env python3
"""pipeline_status.py : where the pipeline stands, from jobs.db (the single source of state).

Prints counts by status and what is waiting at each stage. Thresholds come from
config/scoring_rubric.md. With --log "summary text" it also writes the snapshot plus the summary
to logs/pipeline_<timestamp>.json, which is the run log for a pipeline run.

The `checks` block holds counts that must be 0 at the end of a run. --check exits with status 1
when any is above 0, so a scheduled run cannot report success over a broken state.

Usage:
  python3 skills/job-pipeline/scripts/pipeline_status.py
  python3 skills/job-pipeline/scripts/pipeline_status.py --log "scored 42, 3 CVs, 1 needs the user"
  python3 skills/job-pipeline/scripts/pipeline_status.py --check
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, config_loader, paths  # noqa: E402


def _band(r):
    try:
        return (json.loads(r["score_breakdown"] or "{}") or {}).get("band")
    except Exception:
        return None


def snapshot():
    cfg = config_loader.scoring() or {}
    thr = int(cfg.get("threshold_apply", 60))
    rfloor = int(cfg.get("review_floor", 50))
    con = jobdb.init_db()
    c = jobdb.counts(con)
    scored = con.execute("SELECT * FROM jobs WHERE status='scored'").fetchall()
    found = con.execute("SELECT description FROM jobs WHERE status='found'").fetchall()
    ready = sum(1 for r in scored if (r["match_score"] or 0) >= thr and _band(r) != "hold")
    hold = sum(1 for r in scored if _band(r) == "hold")
    review = sum(1 for r in scored if rfloor <= (r["match_score"] or 0) < thr and _band(r) != "hold")
    no_jd = sum(1 for r in found if not (r["description"] or "").strip())
    soon = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    today = datetime.date.today().isoformat()
    closing = [{"id": r["id"], "title": r["title"], "company": r["company"], "status": r["status"],
                "closing_date": r["closing_date"]}
               for r in con.execute("SELECT * FROM jobs WHERE closing_date IS NOT NULL AND closing_date BETWEEN ? AND ? "
                                    "AND status IN ('found','scored','cv_generated','verified','blocked_login') "
                                    "ORDER BY closing_date", (today, soon))]
    out = {
        "total": jobdb.total(con),
        "by_status": c,
        "waiting": {
            f"found, advert not read yet": no_jd,
            f"found, advert read, not scored": c.get("found", 0) - no_jd,
            f"scored {thr}+ and ready for a CV": ready,
            f"review band {rfloor}-{thr - 1} (the user decides)": review,
            "on hold for the user": hold,
            "cv_generated (awaiting cv-verify)": c.get("cv_generated", 0),
            "verified (ready for the user to apply)": c.get("verified", 0),
            "blocked_login (the user to finish)": c.get("blocked_login", 0),
        },
        "closing_within_3_days": closing,
        "checks": {
            # Rows rejected without being read (a keyword screen or a ranking cut-off): back to found.
            "rejected_unread": len(jobdb.unread_rejections(con)),
            # A number with no requirement mapping is not comparable with a full-read score.
            "scored_without_mapping": con.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='scored' AND (score_breakdown IS NULL OR score_breakdown='')").fetchone()[0],
            # Review-queue roles posted over 21 days ago: close them (reversible) unless still open.
            "scored_older_than_21_days": con.execute(
                "SELECT COUNT(*) FROM jobs WHERE status='scored' AND COALESCE(date_posted, date_found) < date('now','-21 day')").fetchone()[0],
        },
        # For information: scored before adverts were always stored; cv-tailor re-reads the advert.
        "scored_without_stored_advert": con.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='scored' AND (description IS NULL OR TRIM(description)='')").fetchone()[0],
    }
    con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None, help="write this summary plus the snapshot to logs/")
    ap.add_argument("--check", action="store_true", help="exit 1 if any count under checks is above 0")
    a = ap.parse_args()
    snap = snapshot()
    if a.log is not None:
        paths.ensure_dirs()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        f = paths.LOGS / f"pipeline_{ts}.json"
        f.write_text(json.dumps({"summary": a.log, **snap}, indent=2, ensure_ascii=False), encoding="utf-8")
        snap["log_file"] = f"logs/{f.name}"
    print(json.dumps(snap, indent=2, ensure_ascii=False))
    if a.check and any(v for v in snap["checks"].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
