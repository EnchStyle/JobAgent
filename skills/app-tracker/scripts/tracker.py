#!/usr/bin/env python3
"""tracker.py : the JobAgent bookkeeping CLI over lib/jobdb.

Reads and updates existing rows through the shared library (inserts belong to job-ingest).
Every command prints JSON.

  counts                                        counts by status plus total
  find TEXT [--status S] [--limit N]            rows whose company, title, location, url, job_id
                                                or stored advert contain TEXT (compact rows)
  list --status S [--limit N] [--brief]         rows at a status (--brief: compact, no adverts)
  show --id ID                                  one full row, advert included
  set-status --id ID --status S [--note T] [--date YYYY-MM-DD] [--replace-notes]
                                                validated status change; the note is appended
                                                with today's date; status 'applied' also fills
                                                date_applied (today, or --date) when empty
  note --id ID --text T                         append a dated note, status unchanged
  set-field --id ID --field F --value V         correct company, title, location, work_mode,
                                                url or job_id
  mark-blocked --id ID [--note T]               status blocked_login (login, sign-up or CAPTCHA wall)
  attach-gmail --id ID --thread TH              set gmail_thread_id, status unchanged
  add --title T --company C [--url U] [--location L] [--source S] [--description-file F]
      [--closing-date D]                         add a role found outside the boards (email
                                                alert, careers page, a role the user names)
  applied-to TEXT                               earlier applications to this employer, and
                                                rows that look like the same role (repeat guard)
  handoff [--status blocked_login] [--path P]   write a hand-off sheet (Markdown) for roles the
                                                user must finish: link, files, closing date, notes
  set-status ... [--cv-sent PATH] [--confirmation page|email|board|none]
                                                on applied: which CV went, how it was confirmed
  export-csv [--path P]                         legacy CSV dump; the workbook is the real report

Each command body is a cmd_* function taking an open connection, so tests can call it directly.
No LLM call, no network.
"""
import re
import sys
import csv
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, paths  # noqa: E402

DEFAULT_CSV = str(paths.OUTPUT / "jobs_export.csv")
BRIEF = ["id", "status", "match_score", "title", "company", "location", "work_mode", "source",
         "job_id", "date_found", "date_applied", "cv_file", "cover_letter_file", "notes"]
EDITABLE = {"company", "title", "location", "work_mode", "url", "job_id"}


def _row_to_dict(row, brief=False):
    if row is None:
        return None
    keys = BRIEF if brief else row.keys()
    d = {k: row[k] for k in keys}
    if brief and d.get("notes") and len(d["notes"]) > 160:
        d["notes"] = d["notes"][:157] + "..."
    return d


def _require(con, job_id):
    row = jobdb.get_by_id(con, job_id)
    if row is None:
        raise SystemExit(f"No job with id {job_id}")
    return row


def _append(existing, text):
    text = (text or "").strip()
    # The date is added here; drop one the caller already typed, so it is not doubled.
    text = re.sub(r"^\d{4}-\d{2}-\d{2}[:\s-]*", "", text).strip()
    if not text:
        return existing
    line = f"{datetime.date.today().isoformat()} {text}"
    return (existing.rstrip() + " | " + line) if existing and existing.strip() else line


def cmd_counts(con):
    return {"counts": jobdb.counts(con), "total": jobdb.total(con)}


FIND_FIELDS = ("company", "title", "location", "url", "job_id", "description")


def cmd_find(con, text, status=None, limit=50):
    """Rows mentioning TEXT in company, title, location, url, job_id or the stored advert."""
    like = f"%{text.lower()}%"
    cond = " OR ".join(f"lower(coalesce({f},'')) LIKE ?" for f in FIND_FIELDS)
    sql = f"SELECT * FROM jobs WHERE ({cond})"
    args = [like] * len(FIND_FIELDS)
    if status:
        sql += " AND status=?"
        args.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(int(limit))
    out = []
    for r in con.execute(sql, args).fetchall():
        d = _row_to_dict(r, brief=True)
        d["matched_in"] = [f for f in FIND_FIELDS if text.lower() in str(r[f] or "").lower()]
        out.append(d)
    return out


def cmd_list(con, status, limit=None, brief=False):
    rows = [_row_to_dict(r, brief=brief) for r in jobdb.get_by_status(con, status)]
    if limit is not None:
        rows = rows[: max(0, int(limit))]
    return rows


def cmd_show(con, job_id):
    return _row_to_dict(_require(con, job_id))


def cmd_set_status(con, job_id, status, note=None, date=None, replace_notes=False,
                   cv_sent=None, confirmation=None, unverified_reason=None):
    if status not in jobdb.STATUSES:
        raise SystemExit(f"invalid status {status!r}; valid: {', '.join(jobdb.STATUSES)}")
    row = _require(con, job_id)
    # Gate: a CV is sent only after the independent cv-verify pass. A role reaches
    # applied from verified (or from blocked_login after a hand-off); anything else needs an
    # explicit, recorded reason.
    if status == "applied" and row["status"] not in ("verified", "blocked_login", "applied"):
        if not (unverified_reason or "").strip():
            raise SystemExit(f"job {job_id} is at {row['status']!r}, not 'verified': run cv-verify "
                             "first, or pass --unverified-reason if the user approved sending it")
        note = _append(note, f"applied without cv-verify: {unverified_reason.strip()}") if note else \
            f"applied without cv-verify: {unverified_reason.strip()}"
    if status == "rejected" and not (note or "").strip() and not row["score_breakdown"]:
        raise SystemExit("set-status rejected needs --note with the reason (this role has no "
                         "full-read score)")
    fields = {}
    if note is not None:
        fields["notes"] = note if replace_notes else _append(row["notes"], note)
    if status == "applied" and not row["date_applied"]:
        fields["date_applied"] = date or datetime.date.today().isoformat()
    if cv_sent:
        fields["cv_sent"] = paths.to_relative(cv_sent)
    if confirmation:
        fields["confirmation"] = confirmation
    jobdb.update_status(con, job_id, status, **fields)
    out = {"id": int(job_id), "status": status}
    if "date_applied" in fields:
        out["date_applied"] = fields["date_applied"]
    return out


def cmd_add(con, title, company, url=None, location=None, source="manual", description_file=None,
            closing_date=None):
    """Insert a role found outside the boards. Duplicate check by employer and title first."""
    dups = jobdb.possible_duplicates(con, company, title)
    desc = Path(description_file).read_text(encoding="utf-8") if description_file else None
    job = {"source": source or "manual", "title": title, "company": company, "url": url,
           "location": location, "description": desc,
           "notes": ("possible_duplicate_of:" + ",".join(str(d["id"]) for d in dups)) if dups else None}
    inserted = jobdb.insert_job(con, job)
    row = con.execute("SELECT id FROM jobs WHERE dedupe_key=?",
                      (jobdb.dedupe_key(job["source"], None, company, title, location),)).fetchone()
    if row and closing_date:
        jobdb.update_status(con, row["id"], "found", closing_date=closing_date[:10])
    return {"id": row["id"] if row else None, "inserted": bool(inserted), "possible_duplicates": dups}


def cmd_applied_to(con, text):
    """Repeat-application guard: earlier applications to the employer named in TEXT."""
    return {"earlier_applications": jobdb.applied_to_employer(con, text)}


def cmd_handoff(con, status="blocked_login", path=None):
    """Markdown sheet of the roles the user has to finish by hand."""
    rows = jobdb.get_by_status(con, status)
    rows = sorted(rows, key=lambda r: ((r["closing_date"] or "9999"), r["id"]))
    lines = [f"# Hand-off: roles at {status} ({datetime.date.today().isoformat()})", "",
             "| id | Role | Employer | Closes | Link | CV | Letter | Why it stopped |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        why = (r["notes"] or "").split(" | ")[-1].replace("|", "/")[:160]
        lines.append(f"| {r['id']} | {r['title']} | {r['company']} | {r['closing_date'] or ''} | {r['url'] or ''} | "
                     f"{r['cv_file'] or ''} | {r['cover_letter_file'] or ''} | {why} |")
    paths.ensure_dirs()
    out = Path(path) if path else paths.OUTPUT / f"handoff_{datetime.date.today().isoformat()}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"rows": len(rows), "path": str(out)}


def cmd_note(con, job_id, text):
    row = _require(con, job_id)
    jobdb.update_status(con, job_id, row["status"], notes=_append(row["notes"], text))
    return {"id": int(job_id), "status": row["status"], "note_added": text}


def cmd_set_field(con, job_id, field, value):
    if field not in EDITABLE:
        raise SystemExit(f"field must be one of: {', '.join(sorted(EDITABLE))}")
    row = _require(con, job_id)
    jobdb.update_status(con, job_id, row["status"], **{field: value})
    return {"id": int(job_id), field: value, "previous": row[field]}


def cmd_mark_blocked(con, job_id, note=None):
    return cmd_set_status(con, job_id, "blocked_login", note=note)


def cmd_attach_gmail(con, job_id, thread):
    row = _require(con, job_id)
    jobdb.update_status(con, job_id, row["status"], gmail_thread_id=thread)
    return {"id": int(job_id), "status": row["status"], "gmail_thread_id": thread}


def cmd_export_csv(con, path=DEFAULT_CSV):
    cur = con.execute("SELECT * FROM jobs ORDER BY id")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    return {"path": str(out), "rows": len(rows)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="JobAgent bookkeeping CLI over jobs.db.")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("counts")
    p = sub.add_parser("find")
    p.add_argument("text")
    p.add_argument("--status", default=None)
    p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("list")
    p.add_argument("--status", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--brief", action="store_true")
    p = sub.add_parser("show")
    p.add_argument("--id", type=int, required=True)
    p = sub.add_parser("set-status")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--note", "--notes", dest="note", default=None)
    p.add_argument("--date", default=None, help="date_applied for status applied (default today)")
    p.add_argument("--replace-notes", action="store_true", help="overwrite notes instead of appending")
    p.add_argument("--cv-sent", default=None, help="the CV file actually sent (applied)")
    p.add_argument("--confirmation", default=None, choices=["page", "email", "board", "none"],
                   help="how the application was confirmed")
    p.add_argument("--unverified-reason", default=None,
                   help="required to mark applied a role that has not passed cv-verify")
    p = sub.add_parser("note")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--text", required=True)
    p = sub.add_parser("set-field")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--field", required=True)
    p.add_argument("--value", required=True)
    p = sub.add_parser("mark-blocked")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--note", "--notes", dest="note", default=None)
    p = sub.add_parser("attach-gmail")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--thread", required=True)
    p = sub.add_parser("add")
    p.add_argument("--title", required=True)
    p.add_argument("--company", required=True)
    p.add_argument("--url", default=None)
    p.add_argument("--location", default=None)
    p.add_argument("--source", default="manual")
    p.add_argument("--description-file", default=None)
    p.add_argument("--closing-date", default=None)
    p = sub.add_parser("applied-to")
    p.add_argument("text")
    p = sub.add_parser("handoff")
    p.add_argument("--status", default="blocked_login")
    p.add_argument("--path", default=None)
    p = sub.add_parser("export-csv")
    p.add_argument("--path", default=DEFAULT_CSV)
    a = ap.parse_args(argv)

    con = jobdb.connect()
    try:
        if a.command == "counts":
            out = cmd_counts(con)
        elif a.command == "find":
            out = cmd_find(con, a.text, a.status, a.limit)
        elif a.command == "list":
            out = cmd_list(con, a.status, a.limit, a.brief)
        elif a.command == "show":
            out = cmd_show(con, a.id)
        elif a.command == "set-status":
            out = cmd_set_status(con, a.id, a.status, a.note, a.date, a.replace_notes,
                                 a.cv_sent, a.confirmation, a.unverified_reason)
        elif a.command == "note":
            out = cmd_note(con, a.id, a.text)
        elif a.command == "set-field":
            out = cmd_set_field(con, a.id, a.field, a.value)
        elif a.command == "mark-blocked":
            out = cmd_mark_blocked(con, a.id, a.note)
        elif a.command == "add":
            out = cmd_add(con, a.title, a.company, a.url, a.location, a.source, a.description_file,
                          a.closing_date)
        elif a.command == "applied-to":
            out = cmd_applied_to(con, a.text)
        elif a.command == "handoff":
            out = cmd_handoff(con, a.status, a.path)
        elif a.command == "attach-gmail":
            out = cmd_attach_gmail(con, a.id, a.thread)
        else:
            out = cmd_export_csv(con, a.path)
    finally:
        con.close()
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
