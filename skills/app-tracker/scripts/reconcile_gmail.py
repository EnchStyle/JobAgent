"""reconcile_gmail.py : reconcile a batch of Gmail application confirmations to jobs.db.

Anticipates BOTH ways an application happens, because a confirmation email is the ground
truth either way:

  - AUTO (pipeline applied it): the row is already `applied`; we just attach the thread and
    move on. Idempotent, so re-running never double-writes.
  - MANUAL onto a tracked row: a human applied to a role the pipeline had at ANY status,
    including one it had `rejected`. The confirmation flips it to `applied`.
  - MANUAL, off-pipeline: an application to a role never scraped (no row). We insert a new
    `applied` row through the sanctioned lib.jobdb insert path.

The model side (a Claude session, interactive or scheduled) does the untrusted part: search
Gmail for confirmations and hand this script a clean JSON list. This script is deterministic:
no network, no LLM. It matches, writes through lib.jobdb, and is idempotent via the
processed_emails ledger, so it is safe to run on every sweep.

Matching order per record (first hit wins):
  1. board reference  -> jobs.job_id == ref, or url LIKE %ref%   (clean auto/board path)
  2. url              -> exact, then LIKE
  3. company (+title) -> normalized company match among rows; if a title is given, the best
                         token-overlap row; if not, the single appliable candidate. If the
                         company matches more than one plausible row and nothing disambiguates,
                         the record is left for review rather than guessed.

A matched row only ever moves FORWARD to applied (rows already at applied, interview or closed
keep their status); date_applied is filled only if empty (the
email's date never overwrites a date already recorded); gmail_thread_id is filled only if empty.

Input : JSON list on stdin, or --file PATH. Each record:
  { "thread_id": str,            # required: Gmail thread, stored as gmail_thread_id
    "msg_id": str | null,        # idempotency key; defaults to thread_id. Give the per-message
                                 #   id when one thread carries two applications (e.g. an ATS
                                 #   that confirms two roles in the same thread).
    "date": "YYYY-MM-DD",        # required: date_applied when the row has none
    "id": int | null,            # explicit jobs.id when the model already resolved the row
                                 #   (e.g. an alias the fuzzy path cannot see: Example Careers =
                                 #   Example Group). Honored before every other matcher.
    "company": str,              # required for the fuzzy path; always recommended
    "title": str | null,         # optional
    "ref": str | null,           # board Job Reference if the email carried one
    "url": str | null,           # listing url if known
    "source": str | null }       # cv_library | reed | linkedin | teamtailor | ...

Matcher precedence: explicit id  >  board ref  >  url  >  company (+title).

Output: one JSON report to stdout: reconciled / inserted / needs_review / skipped, with a
per-record reason, plus before/after status counts. Nothing is printed to stderr on success.

Usage:
  python3 skills/app-tracker/scripts/reconcile_gmail.py --file inbox/confirmations.json
  cat confirmations.json | python3 skills/app-tracker/scripts/reconcile_gmail.py
  ... --dry-run      # match and report, write nothing
  ... --force        # ignore the processed_emails ledger (re-process threads)
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb  # noqa: E402

# Rows still moving through the pipeline: a strong manual-apply target.
FORWARD = {"found", "scored", "cv_generated", "verified", "blocked_login"}


def _ensure_ledger(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS processed_emails "
        "(message_id TEXT PRIMARY KEY, source TEXT, processed_at TEXT)"
    )
    con.commit()


def _seen(con, thread_id):
    return con.execute(
        "SELECT 1 FROM processed_emails WHERE message_id=?", (thread_id,)
    ).fetchone() is not None


def _mark_seen(con, thread_id, source):
    con.execute(
        "INSERT OR REPLACE INTO processed_emails(message_id, source, processed_at) VALUES (?,?,?)",
        (thread_id, source, datetime.datetime.now().isoformat(timespec="seconds")),
    )
    con.commit()


def _tokens(s):
    return set(jobdb._norm(s).split())


# Rows already past the application step keep their status (an interview or an outcome must
# never be reset to applied by a late or duplicate confirmation email).
PAST_APPLIED = {"applied", "interview", "closed"}


def _apply_to_row(con, row, rec, dry):
    """Move a matched row forward to applied without clobbering existing facts."""
    prior = row["status"]
    fields = {}
    if not row["date_applied"]:
        fields["date_applied"] = rec["date"]
    if not row["gmail_thread_id"]:
        fields["gmail_thread_id"] = rec["thread_id"]
    new_status = prior if prior in PAST_APPLIED else "applied"
    if not dry:
        jobdb.update_status(con, row["id"], new_status, **fields)
    return {"id": row["id"], "company": row["company"], "title": row["title"],
            "prior_status": prior, "date_applied": row["date_applied"] or rec["date"],
            "thread": row["gmail_thread_id"] or rec["thread_id"]}


def _find_row(con, rec):
    """Return ('match', row) | ('none', None) | ('ambiguous', [rows]) for one record."""
    if rec.get("id") is not None:
        r = con.execute("SELECT * FROM jobs WHERE id=?", (int(rec["id"]),)).fetchone()
        if r:
            return "match", r

    ref = (rec.get("ref") or "").strip()
    if ref:
        r = con.execute(
            "SELECT * FROM jobs WHERE job_id=? OR url LIKE ? ORDER BY id LIMIT 1",
            (ref, f"%{ref}%"),
        ).fetchone()
        if r:
            return "match", r

    url = (rec.get("url") or "").strip()
    if url and url not in ("https://www.reed.co.uk/", "https://www.linkedin.com/"):
        r = con.execute(
            "SELECT * FROM jobs WHERE url=? OR url LIKE ? ORDER BY id LIMIT 1",
            (url, f"%{url}%"),
        ).fetchone()
        if r:
            return "match", r

    company = rec.get("company") or ""
    cnorm = jobdb._norm(company)
    if not cnorm:
        return "none", None
    # Company match: exact-normalized or one contained in the other (handles "Example,
    # Ltd" vs "Example", and acronym rows).
    cands = [
        row for row in con.execute("SELECT * FROM jobs")
        if (cn := jobdb._norm(row["company"] or "")) and (cn == cnorm or cn in cnorm or cnorm in cn)
    ]
    if not cands:
        return "none", None
    if len(cands) == 1:
        return "match", cands[0]

    # Multiple rows for this company. Disambiguate by title token overlap when we have a title.
    title = rec.get("title")
    if title:
        want = _tokens(title)
        scored = sorted(
            ((len(want & _tokens(row["title"] or "")), row) for row in cands),
            key=lambda t: t[0], reverse=True,
        )
        top, second = scored[0], (scored[1] if len(scored) > 1 else (0, None))
        if top[0] >= 1 and top[0] > second[0]:
            return "match", top[1]
        if top[0] == 0:
            # The title matches none of this company's rows: do not guess among unrelated roles.
            return "ambiguous", cands
        # A tie on title overlap: only the tied rows stay in the running (never an unrelated
        # role at the same employer that happens to be further along the pipeline).
        cands = [row for n, row in scored if n == top[0]]

    # No title, or a title tie. Resolve by how live each candidate is. A row still moving through
    # the pipeline (forward) is a much stronger manual-apply target than one the pipeline culled,
    # so a single forward row wins outright; a lone rejected row is taken only if nothing forward
    # competes; otherwise (two live rows, or two culled rows) we refuse to guess.
    forward = [r for r in cands if r["status"] in FORWARD]
    if len(forward) == 1:
        return "match", forward[0]
    if not forward:
        rejected = [r for r in cands if r["status"] == "rejected"]
        if len(rejected) == 1:
            return "match", rejected[0]
        already = [r for r in cands if r["status"] in ("applied", "interview", "closed")]
        if not rejected and len(already) == 1:
            return "match", already[0]  # the one application on record: idempotent
    return "ambiguous", cands


def _insert_offpipeline(con, rec, dry):
    """Insert a brand-new applied row for an off-pipeline confirmation, via lib.jobdb."""
    job = {
        "source": rec.get("source") or "manual",
        "job_id": rec.get("ref") or None,
        "title": rec.get("title") or "(from application confirmation)",
        "company": rec.get("company"),
        "location": rec.get("location") or "",
        "url": rec.get("url") or "",
        "status": "applied",
        "gmail_thread_id": rec["thread_id"],
        "salary_unknown": 1,
        "notes": f"Off-pipeline: applied outside the scraper, reconciled from Gmail "
                 f"confirmation on {rec['date']}.",
    }
    key = jobdb.dedupe_key(job["source"], job["job_id"], job["company"], job["title"], job["location"])
    if dry:
        return {"company": job["company"], "title": job["title"], "date_applied": rec["date"],
                "inserted": True}
    jobdb.insert_job(con, {**job, "dedupe_key": key})
    row = con.execute("SELECT * FROM jobs WHERE dedupe_key=?", (key,)).fetchone()
    jobdb.update_status(con, row["id"], "applied",
                        date_applied=rec["date"], gmail_thread_id=rec["thread_id"],
                        notes=job["notes"])
    return {"id": row["id"], "company": row["company"], "title": row["title"],
            "date_applied": rec["date"], "inserted": True}


def reconcile(con, records, dry=False, force=False):
    _ensure_ledger(con)
    report = {"reconciled": [], "inserted": [], "needs_review": [], "skipped": []}
    before = jobdb.counts(con)
    for rec in records:
        tid = rec.get("thread_id")
        idem = rec.get("msg_id") or tid
        if not tid or not rec.get("date"):
            report["skipped"].append({"record": rec, "reason": "missing thread_id or date"})
            continue
        if not force and _seen(con, idem):
            report["skipped"].append({"msg": idem, "reason": "already processed"})
            continue
        kind, found = _find_row(con, rec)
        if kind == "match":
            res = _apply_to_row(con, found, rec, dry)
            res["reason"] = ("explicit-id" if rec.get("id") is not None else
                             "board-ref" if rec.get("ref") else
                             "url" if rec.get("url") else "company/title")
            report["reconciled"].append(res)
            if not dry:
                _mark_seen(con, idem, rec.get("source") or found["source"])
        elif kind == "none":
            res = _insert_offpipeline(con, rec, dry)
            report["inserted"].append(res)
            if not dry:
                _mark_seen(con, idem, rec.get("source") or "manual")
        else:  # ambiguous: do NOT guess, do NOT mark processed, so it can be retried
            report["needs_review"].append({
                "thread": tid, "company": rec.get("company"), "title": rec.get("title"),
                "candidates": [{"id": r["id"], "title": r["title"], "status": r["status"]} for r in found],
                "reason": "multiple rows match this company; disambiguate the title or apply by id",
            })
    after = jobdb.counts(con)
    report["counts"] = {"before": before, "after": after,
                        "reconciled": len(report["reconciled"]),
                        "inserted": len(report["inserted"]),
                        "needs_review": len(report["needs_review"]),
                        "skipped": len(report["skipped"]),
                        "dry_run": dry}
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="JSON file of confirmation records (default: stdin)")
    ap.add_argument("--dry-run", action="store_true", help="match and report, write nothing")
    ap.add_argument("--force", action="store_true", help="ignore the processed_emails ledger")
    a = ap.parse_args(argv)
    raw = Path(a.file).read_text(encoding="utf-8") if a.file else sys.stdin.read()
    records = json.loads(raw)
    if isinstance(records, dict):
        records = records.get("confirmations", [records])
    con = jobdb.init_db()
    report = reconcile(con, records, dry=a.dry_run, force=a.force)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
