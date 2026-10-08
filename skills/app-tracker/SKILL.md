---
name: app-tracker
description: Bookkeeping for the JobAgent tracker (jobs.db). Finds rows, records status changes and outcomes (applied, interview, closed, blocked), appends notes, corrects fields, reconciles application-confirmation emails from Gmail, and exports the colour-coded scan workbook split by market. Use whenever asked to update, find, correct or report on tracked jobs and applications, record an interview or a rejection, reconcile confirmation emails, or refresh the scan report.
---

# app-tracker

One CLI and one status vocabulary for jobs.db, so every session records things the same way.
Run commands from the project root (see job-pipeline). Scripts go through lib/jobdb.py; do not
open the SQLite file with other tools, because the folder needs its TRUNCATE journal mode and
every write should keep the notes history intact.

## Statuses
`found -> scored -> cv_generated -> verified -> applied -> interview`, plus:
- `rejected`: dropped by the pipeline before applying (low fit, location, sales, expired
  advert, duplicate, or the user's decision); the reason is in the breakdown band or the notes.
- `closed`: an outcome after applying (unsuccessful, withdrawn, role pulled).
- `blocked_login`: an application stopped at a login, sign-up or CAPTCHA wall; the user finishes it.
references/db_contract.md has the columns, bands and dedupe rule.

## Commands (`python3 skills/app-tracker/scripts/tracker.py ...`, all print JSON)
- `find "acme"` : search company, title, location, url, job id and the stored advert
  (compact rows, with the fields that matched). Use this to turn "the Acme role" into an id;
  `show --id N` for the full row and advert.
- `counts`, `list --status S --brief`.
- `set-status --id N --status S --note "..."` : the note is appended with today's date, never
  replacing the history. Setting `applied` fills date_applied (today, or `--date YYYY-MM-DD`).
  Examples: an interview invitation -> `interview`; "unsuccessful" -> `closed`; the user drops a
  role -> `rejected` with the reason.
- `note --id N --text "..."` : add a dated note without changing status.
- `set-field --id N --field company --value "Acme Ltd"` : correct company, title, location,
  work_mode, url or job_id (a blank company stops Gmail replies matching the row).
- `mark-blocked --id N --note "..."`, `attach-gmail --id N --thread <thread id>`.
- `add --title T --company C [--url U] [--closing-date D]` : a role found outside the boards.
- `applied-to "<employer>"` : earlier applications to that employer (repeat guard).
- `handoff` : output/handoff_<date>.md for every blocked_login role (link, files, closing date).
- `set-status ... --cv-sent <file> --confirmation page|email|board|none` when recording applied.

Board confirmation with a job reference: `python3 skills/app-tracker/scripts/reconcile_apply.py
--ref <board ref> [--date YYYY-MM-DD]`.

## Gmail confirmations
Optional: needs a Gmail connector in the Claude app. Read the confirmation emails, write one JSON
record per application to a
scratch file, and run `python3 skills/app-tracker/scripts/reconcile_gmail.py --file <file>`
(`--dry-run` first if unsure). It matches by id, board reference, url, then company and title;
moves matched rows forward to applied (rows already at applied, interview or closed keep their
status); inserts an applied row for an application the pipeline never saw; and leaves ambiguous
ones under needs_review instead of guessing. It is idempotent. Record format and matching rules:
references/gmail_reconcile.md.

## The scan report
`python3 skills/app-tracker/scripts/export_workbook.py` writes
output/jobs_overview.xlsx: a Summary tab, then one tab per configured market, then
Other for rows with no market or a place abroad. Colours: blue applied, purple interview, grey closed, green in
progress (scored 60+, cv_generated, verified), yellow review band or on hold, orange blocked, red
rejected, amber not yet scored. Regenerate it after any batch of changes. After a scrape,
`export_scraping_tab.py` can add a "Scraping <date>" sheet showing that day's gates.

## Report to the user
What changed (id, role, old status to new status), anything you could not match, and the report
file if you regenerated it.
