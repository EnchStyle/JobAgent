# db_contract.md : the jobs.db contract app-tracker owns

Loaded on demand. The authoritative schema lives in `lib/jobdb.py`; this file is the plain
language contract so callers know the columns, the status enum, the transitions, and the
dedupe rule. No em dashes anywhere in what you write.

## The jobs table (one row per role)
| Column | Notes |
|---|---|
| id | Integer primary key (autoincrement). The handle every command uses. |
| dedupe_key | UNIQUE, NOT NULL. The dedupe identity (see below). Set by the library. |
| job_id | Source native id / board Job Reference. Same number shown in application-confirmation emails, so a confirmation reconciles to its row by matching it (see scripts/reconcile_apply.py). |
| source | cv_library, reed, linkedin, indeed; manual or another label for rows added by hand or by the Gmail reconciler. |
| title | Role title. |
| company | Employer. |
| location | As listed. |
| work_mode | onsite, hybrid, remote. |
| salary_min, salary_max | Parsed numbers (may be null). |
| salary_currency, salary_period | e.g. GBP / annual, EUR / month (hour, day, week, month, annual). |
| salary_unknown | 1 when salary was hidden or estimated and kept for a manual check. |
| url | Link to the listing. |
| date_found | Date ingested. |
| date_posted | From the listing. |
| match_score | 0 to 100 fit score (job-match-score; cv-verify may re-store on pass). |
| score_breakdown | JSON: fit_score, rationale, gaps, band (apply, review, skip, hold, location_reject, sales_reject, expired, duplicate_reject, other_reject), reject_reason or hold text, optional sub-scores. |
| cv_file | Path in output/cvs (cv-tailor). |
| cover_letter_file | Path in output/cover_letters (cover-letter). |
| status | See the enum below. NOT NULL, defaults to found. |
| date_applied | Set when the role is applied to. |
| gmail_thread_id | Gmail thread for tracking replies (attach-gmail). |
| closing_date | YYYY-MM-DD from the advert (save_description.py --closing-date); queues sort by it. |
| rescore | cv-verify's independent re-score; match_score keeps the original score. |
| cv_sent | The CV file that actually went with the application (set-status --cv-sent). |
| confirmation | How the application was confirmed: page, email, board or none. |
| notes | Free text history: ingest flags, then dated entries joined by " \| " (reasons, cv-verify fixes, what the user decided). Always appended, never overwritten. |
| description | The full job description, read during enrichment before scoring. |
| created_at, updated_at | ISO timestamps, maintained by the library. |

A second table, `processed_emails` (message_id, source, processed_at), is created by
scripts/reconcile_gmail.py on first use. It records every confirmation email already reconciled,
so re-running the reconciler never applies the same email twice.

## Status enum and transitions
Statuses (from `lib.jobdb.STATUSES`):
`found`, `scored`, `cv_generated`, `verified`, `applied`, `blocked_login`, `rejected`,
`interview`, `closed`.

Normal path (one stage per skill):
```
found  ->  scored  ->  cv_generated  ->  verified  ->  applied  ->  interview
```
- found: written by job-ingest after the hard filters and the reject-title drop.
- scored: job-match-score scored it 50 or more. Band apply (60+) goes to cv-tailor; band review
  (50 to 59) and band hold wait for the user.
- cv_generated: cv-tailor produced and registered a CV. A failed cv-verify leaves it here with
  the fixes in notes.
- verified: cv-verify passed the CV.
- applied: submitted; date_applied is set (tracker set-status fills it).
- interview: invited to interview.

Branches:
- rejected: either dropped before applying (below 50, location, sales, expired advert, duplicate,
  the reject-title list applied to an unread row by `reapply_title_list.py`, or the user's
  decision), or turned down by the employer after applying (date_applied is set and the notes
  carry a dated "Gmail cross-check" entry). The band or notes say which.
- closed: an outcome after applying (unsuccessful, withdrawn, role pulled). Older rows also use
  closed for adverts that expired before any application; date_applied tells the two apart.
- blocked_login: an application stopped at a login, registration or CAPTCHA wall; the user finishes
  it (`mark-blocked`).

The enum is validated on every change; the order is not enforced, so choose a sensible
transition.

## Dedupe rule (do not reimplement)
The library builds the dedupe_key and enforces it with a UNIQUE index, so a re-run cannot
create a second row for a role already tracked in ANY status:
- Prefer the source native job_id: `id:<source>:<job_id>`.
- Otherwise a normalized fallback: `k:` plus lower-cased, punctuation-stripped
  company + title + location.
Inserts go through `lib.jobdb.insert_job` (job-ingest), which returns 1 for a new row or 0 for
a duplicate. app-tracker never inserts; it reads and updates existing rows.
