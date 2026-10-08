#!/usr/bin/env python3
"""export_scraping_tab.py : append a report-only "Scraping <date>" snapshot tab.

job-ingest's filters.classify() checks reject-title FIRST, so a title-mismatched card is
dropped before salary/location/freshness are even evaluated, and scrape_ingest.py only ever
inserts a row into jobs.db once it has passed every gate, title included. A title-rejected
role has therefore never had a jobs.db row; it was only a count in the run's JSON report. This
script gives that visibility back for one day's run, split into three buckets, WITHOUT changing
jobs.db: title-rejects still are not persisted, so a role dropped on title today can resurface on
a later scan (report-only by design; persisting title-rejects as status=rejected would hide
them for good).

  1. All jobs extracted   = cards from today's raw scrape that pass the step-1 hard filters
                             (freshness, location/work-mode, salary), title ignored.
  2. Removed (title mismatch) = the above, further dropped by config/filters.md's
                             reject_title_contains list.
  3. Shortlisted for further marking = the above survivors: exactly what scrape_ingest.py
                             either inserted as a new status=found row, or matched to an
                             already-tracked row (dedupe) that is not re-marked.

The three buckets are re-derived directly from the day's raw inbox/scrape_<source>_*.json
cards, importing filters.py's own gate functions (freshness_gate, location_gate, salary_gate,
reject_title) rather than reimplementing them, so these counts can never drift from what
scrape_ingest.py actually decided for the same input. Shortlisted rows are then joined back to
jobs.db by dedupe_key to show each one's real, current status and score (found if new; whatever
the existing row already carries, applied included, if scrape_ingest.py matched a duplicate).

Adds (or replaces) one sheet named "Scraping <YYYY-MM-DD>" in the existing
output/jobs_overview.xlsx, alongside and without touching the standing
Summary and per-market tabs that export_workbook.py owns. Run export_workbook.py separately (either
order); this script only opens the workbook and writes its own sheet.

Usage:
  python3 export_scraping_tab.py --source reed --date 2026-01-15
  python3 export_scraping_tab.py --source reed --date 2026-01-15 --pattern "scrape_*reed*.json"
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "job-ingest" / "scripts"))
from lib import jobdb, paths, config_loader  # noqa: E402
import filters as filt  # noqa: E402
import normalize as norm  # noqa: E402

try:
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill, Font
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("openpyxl not installed: pip install -r requirements.txt")

HEAD_FILL = PatternFill("solid", fgColor="333333")
HEAD_FONT = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)
FILLS = {
    "removed": PatternFill("solid", fgColor="FFC7CE"),    # red, matches the standing reject colour
    "shortlisted_new": PatternFill("solid", fgColor="FFEB9C"),  # amber, matches found/not-yet-scored
    "shortlisted_scored_apply": PatternFill("solid", fgColor="C6EFCE"),  # green, matches scored>=threshold
    "shortlisted_applied": PatternFill("solid", fgColor="BDD7EE"),  # blue, matches applied
    "shortlisted_other": PatternFill("solid", fgColor="FFEB9C"),
}
HEADERS = ["Bucket", "Job ID", "Title", "Company", "Location", "Mode", "Salary", "Posted",
           "Reject reason", "DB status", "Score", "URL"]
WIDTHS = [24, 12, 46, 26, 22, 9, 16, 12, 22, 12, 7, 46]


def _salary_text(job):
    if job.get("salary_min") or job.get("salary_max"):
        cur = job.get("salary_currency") or ""
        lo = str(int(job["salary_min"])) if job.get("salary_min") is not None else ""
        hi = str(int(job["salary_max"])) if job.get("salary_max") is not None else ""
        rng = lo + ("-" + hi if hi else "")
        return f"{cur} {rng}".strip()
    return ""


def classify_for_report(job, cfg, today=None):
    """Re-derive step-1 (title ignored), then title, using filters.py's own gate functions.

    Returns one of: "stale", "location_reject", "salary_reject" (excluded from "extracted"),
    "removed:<keyword>" (extracted, then dropped on title), or "shortlisted" (survives both).
    Mirrors filters.classify()'s own gate outcomes exactly; only the ORDER differs (salary/
    location/freshness are checked before title here, so the snapshot shows what the title filter alone removed),
    which cannot change a role's final keep/reject outcome versus scrape_ingest.py, only which
    reason is reported first for a role that happens to fail more than one gate.
    """
    if not filt.freshness_gate(job, cfg, today):
        return "stale", None
    loc_dec, loc_reason = filt.location_gate(job, cfg)
    if loc_dec == "reject":
        return "location_reject", loc_reason
    sal_ok, sal_reason, _flag = filt.salary_gate(job, cfg)
    if not sal_ok:
        return "salary_reject", sal_reason
    rj, kw = filt.reject_title(job.get("title"), cfg)
    if rj:
        return "removed", kw
    return "shortlisted", None


def build_buckets(source, date_str, pattern, con, cfg):
    inbox_dir = Path(paths.INBOX)
    all_extracted, removed, shortlisted = [], [], []
    excluded_upstream = 0  # stale / location_reject / salary_reject: never part of "extracted"
    files_read = 0
    seen_keys = set()  # intra-batch dedupe: offset pagination on a live board can shift by a
    # few rows between page loads while a scan is in progress, so the same listing can be
    # captured twice across two page fetches. jobdb.insert_job already collapses this (INSERT
    # OR IGNORE) when the row lands in jobs.db; do the same here so a repeat card is not
    # counted twice as two different "extracted" jobs.
    for f in sorted(inbox_dir.glob(pattern)):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(d, dict) or d.get("source") != source:
            continue
        files_read += 1
        default_remote = d.get("remote")
        for c in d.get("cards") or []:
            if default_remote and isinstance(c, dict) and not c.get("remote"):
                c = dict(c, remote=default_remote)
            try:
                j = norm.normalize(source, c, today=datetime.date.fromisoformat(date_str))
            except ValueError:
                continue
            key = jobdb.dedupe_key(j.get("source"), j.get("job_id"), j.get("company"),
                                    j.get("title"), j.get("location"))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            bucket, reason = classify_for_report(j, cfg, datetime.date.fromisoformat(date_str))
            if bucket in ("stale", "location_reject", "salary_reject"):
                excluded_upstream += 1
                continue
            all_extracted.append(j)
            if bucket == "removed":
                j["_reject_reason"] = "reject_title:" + str(reason)
                removed.append(j)
            else:
                row = con.execute("SELECT * FROM jobs WHERE dedupe_key=?", (key,)).fetchone()
                j["_db_row"] = dict(row) if row is not None else None
                shortlisted.append(j)
    return {
        "files_read": files_read,
        "all_extracted": all_extracted,
        "removed": removed,
        "shortlisted": shortlisted,
        "excluded_upstream": excluded_upstream,
    }


def _fill_for_shortlisted(j):
    """Mirror export_workbook.py's fill_for() exactly, so the same row gets the same colour
    on this snapshot tab and on the standing per-market tab: BLUE applied, GREEN scored at
    or above threshold, RED rejected, AMBER everything else (found/not-yet-scored, and the
    50..threshold-1 review band, which export_workbook.py's own catch-all also leaves amber)."""
    row = j.get("_db_row")
    if not row:
        return FILLS["shortlisted_new"]
    st = row.get("status")
    if st == "applied":
        return FILLS["shortlisted_applied"]
    if st in ("scored", "cv_generated", "verified") and (row.get("match_score") or 0) >= _threshold():
        return FILLS["shortlisted_scored_apply"]
    if st == "rejected":
        return FILLS["removed"]
    return FILLS["shortlisted_other"]


_THRESH_CACHE = None


def _threshold():
    global _THRESH_CACHE
    if _THRESH_CACHE is None:
        try:
            _THRESH_CACHE = int(config_loader.scoring().get("threshold_apply", 60))
        except Exception:
            _THRESH_CACHE = 60
    return _THRESH_CACHE


def write_sheet(wb, date_str, buckets):
    name = f"Scraping {date_str}"
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(title=name)

    total = len(buckets["all_extracted"])
    removed_n = len(buckets["removed"])
    short_n = len(buckets["shortlisted"])
    # By the time this runs, scrape_ingest.py has usually already inserted today's survivors,
    # so "no _db_row" alone cannot distinguish new-today from pre-existing (both now have a
    # row). Use date_found instead: a row first found today is this run's insert; an earlier
    # date_found means scrape_ingest.py deduped it against an already-tracked role.
    new_n = sum(1 for j in buckets["shortlisted"]
                if not j.get("_db_row") or (j["_db_row"].get("date_found") == date_str))
    dup_n = short_n - new_n

    ws.append(["Scraping run", date_str])
    ws.append(["Files read (inbox/scrape_*.json)", buckets["files_read"]])
    ws.append(["Excluded upstream (stale / location / salary, never scored as 'extracted')",
               buckets["excluded_upstream"]])
    ws.append(["All jobs extracted (passed salary + city/remote + freshness; title ignored)", total])
    ws.append(["  Removed for title mismatch", removed_n])
    ws.append(["  Shortlisted for further marking against master profile", short_n])
    ws.append([f"    of which new rows written to jobs.db today (status found)", new_n])
    ws.append([f"    of which matched an already-tracked role (dedupe; not re-marked)", dup_n])
    for r in range(1, 9):
        ws.cell(row=r, column=1).font = BOLD
    ws.append([])
    header_row = ws.max_row + 1
    for i, h in enumerate(HEADERS, 1):
        c = ws.cell(row=header_row, column=i, value=h)
        c.fill = HEAD_FILL
        c.font = HEAD_FONT
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f"A{header_row + 1}"

    def _row(bucket_label, j, reason, db_row, fill, not_in_db_label=None):
        if not_in_db_label is not None:
            status = not_in_db_label
        else:
            status = db_row.get("status") if db_row else "found"
        score = db_row.get("match_score") if db_row else None
        ws.append([bucket_label, j.get("job_id"), j.get("title"), j.get("company"),
                   j.get("location"), j.get("work_mode") or "", _salary_text(j),
                   j.get("date_posted"), reason or "", status, score, j.get("url")])
        for c in range(1, len(HEADERS) + 1):
            ws.cell(row=ws.max_row, column=c).fill = fill

    for j in buckets["removed"]:
        _row("Removed (title mismatch)", j, j.get("_reject_reason"), None, FILLS["removed"],
             not_in_db_label="not in jobs.db (report-only)")
    for j in buckets["shortlisted"]:
        _row("Shortlisted", j, "", j.get("_db_row"), _fill_for_shortlisted(j))

    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(HEADERS))}{ws.max_row}"
    return {"sheet": name, "all_extracted": total, "removed": removed_n,
            "shortlisted": short_n, "shortlisted_new": new_n, "shortlisted_duplicate": dup_n,
            "excluded_upstream": buckets["excluded_upstream"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="board name, as in config/sources.md")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--pattern", default=None, help="defaults to scrape_*<source>*_<yyyymmdd>.json for --date")
    args = ap.parse_args()

    date_str = args.date or datetime.date.today().isoformat()
    pattern = args.pattern or f"scrape_*{args.source}*_{date_str.replace('-', '')}.json"

    cfg = config_loader.filters()
    con = jobdb.init_db()
    try:
        buckets = build_buckets(args.source, date_str, pattern, con, cfg)
        xlsx_path = paths.OUTPUT / "jobs_overview.xlsx"
        wb = load_workbook(xlsx_path)
        result = write_sheet(wb, date_str, buckets)
        wb.save(xlsx_path)
    finally:
        con.close()
    result["path"] = str(xlsx_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
