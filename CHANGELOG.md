# Changelog

## Unreleased
- Documentation: docs/FILE_STRUCTURE.md (annotated tree of every file) and a folder tree in the README.
- AGENTS.md rule 2 now matches job-apply "Scripted help": page scripts may attach the approved file, set a
  configured answer or open a hidden control; no CAPTCHA or bot-detection bypass, no honeypot fields, no forcing
  past validation.
- Example settings focus on the UK (London and Manchester), with a commented second-market example.
- The sample CV in uk-cv-writer passes the bullet-length rule, so the dry run shows no failed check.
- job-ingest: `audit_reject_titles.py` (read-only evidence check of the reject-title list: collisions with roles
  scored 50+ or applied, substring entries that fire inside longer words, what each entry dropped from the
  archived cards, and candidate words backed by full reads) and `reapply_title_list.py` (applies the list to
  rows still at `found`, reason in the notes; dry run by default). Evidence rule documented in job-ingest
  SKILL.md, AGENTS.md and filters.example.md. Tests added.
- job-match-score: the pay check names the per-place `office_floor` (London onsite or hybrid roles) as well as the market floor. No code change: the gate already supported it.
- job-ingest: `reed_fetch.js` bulk Reed scraper; CV-Library extractor reads relative dates ('2 days ago', 'yesterday') and mileage locations; docs note the page_number parameter.
- Salary rule is set per market: `salary_range_rule` (`top` default, or `bottom`: the lowest pay offered must
  reach the floor) and an optional per-market `board_salary_factor` that beats the plan-wide one, so a market
  that uses `bottom` can search boards at exactly its floor. The single global factor is now only a default.

## 1.5.0
- `any_role` families: no keywords, every role in their places (board `city_any` templates), for
  small local markets where any working pattern is acceptable.
- Board salary filter factor documented at 0.75 in the example, so wide ranges that reach the
  floor are not hidden.
- Scheduled runs have no caps of their own (progress is saved as they go); only LinkedIn and
  Indeed keep a few searches per run.
- job-apply: batch approval (one yes for a listed set of roles; anything not shown stops that
  role), and portals already signed in in the browser are used.
- job-match-score checks the pay stated in the advert against the floor (cards often show none).
- persist_enriched.py stores a closing_date per record, so deadlines reach the status report.
- Employer-site sources: a company's own vacancy page as a `fixed_urls` board in the search plan, read by an
  async extractor (closing dates such as "Sunday 18 January 2026" are parsed).
- Ingest: `closing_date` is stored at insert when the card has one, and a card whose closing date has passed is
  dropped (reason `expired`); `undergraduate placement` and `placement year` titles are dropped.
- job-apply: an earlier application to the same employer no longer stops a role; the batch list is
  ordered by closing date, then score.
- Reed links are stored as `/jobs/job/<id>`: the bare `/jobs/<id>` form answers 404 even for
  live adverts, which would have made a liveness check or an apply step report a false closure
  (test added; existing rows rewritten).
- Liveness check documented in job-apply: LinkedIn guest endpoint, Reed `/jobs/job/<id>`;
  a dead, never-applied advert is rejected with an `expired:` note.
- One reading per advert: the second reading is dropped (tested: it cost a full extra read and a
  stricter method did not reduce reader disagreement).

## 1.4.0
- One place decides what is searched: `search_plan` in config/sources.md (job families with
  keywords, places, URL templates per board). `skills/job-ingest/scripts/search_plan.py` builds
  each run's searches: standing families on a normal or scheduled run, only the requested
  family or keywords on a request (config unchanged), rotation with per-run and per-board caps,
  a paging window per search, and board salary filters set just below the floor.
- Unattended (scheduled) runs defined in job-pipeline: standing scope, limits per run, never
  submits, signs in or solves a CAPTCHA, `pipeline_status.py --check` must pass.
- `lib/runlock.py`: one pipeline run at a time.
- scrape_ingest.py moves each ingested file to inbox/_archive_<YYYYMM>/ (`--keep-inbox` to
  leave it); housekeeping now only reports files that were never ingested.
- Batches commit in a finally block, and a new connection never inherits an open batch.
- Possible-duplicate check also matches a title with an added suffix ("Senior Product Owner"
  and "Senior Product Owner (Payments)").
- `tracker.py set-status rejected` needs --note when the role has no full-read score.
- Second readings narrowed to scores 55 to 65 and 47 to 53.

## 1.3.0
- Bulk writes commit once: `jobdb.begin_batch` / `end_batch`, used by persist_enriched.py and
  scrape_ingest.py (34 scores in under 1 second instead of about 6).
- `lib/housekeeping.py`: archives processed inbox files, keeps the newest 3 tracker snapshots,
  removes unfinished downloads and LibreOffice export leftovers; run at the end of every pipeline run.
- `pipeline_status.py` adds `scored_without_mapping` and `scored_older_than_21_days`; with
  `rejected_unread` all three must be 0 before a run is reported complete.
- job-match-score: every score from 45 to 65 gets a second reading, blind where possible, and the
  average is recorded with both readings.
- Scoring rubric points to filters.md for location rules instead of restating them.
- uk-cv-writer has its own README for use outside the pipeline.

## 1.2.0
- Unread roles can no longer be rejected: `jobdb.update_status` refuses a rejection of an unread
  row without a stated reason, `jobdb.unread_rejections` finds rows dropped by a keyword screen
  or ranking cut-off, and `pipeline_status.py` reports `rejected_unread`, which must be 0.
- job-ingest, job-pipeline and job-match-score state that a keyword score may only order the
  reading queue, and that a role is never capped because AI (or any keyword) is not its core.
- Test for the guard and the audit.

## 1.1.0
- New job-apply skill with a portal guide: repeat-application guard, route check before typing,
  attachment confirmation, answers only from configured form_answers, hand-off sheet for
  account walls, record of the CV sent and how the application was confirmed.
- Tracker: closing dates (queues sort by them, status flags roles closing within 3 days),
  re-score kept separately (a re-score below the threshold returns the role to review),
  possible-duplicate flag at ingest, `add`, `applied-to` and `handoff` commands.
- lib/backup.py snapshots the tracker and keeps the newest N.
- Adverts that look truncated are flagged for a full read; no keyword screen before reading.
- Onsite roles abroad rejected; place names match at word starts; salaries in other currencies
  flagged separately; multi-currency and multi-language extractors.
- Dry run and tests isolated from personal settings (JOBAGENT_CONFIG_DIR).

## 1.0.0 (first public release)
- Pipeline skills: job-pipeline, job-ingest, job-match-score, cv-tailor, cover-letter, cv-verify,
  app-tracker, with the bundled uk-cv-writer skill (1.1.0).
- Markets (countries) configurable in config/filters.md: currency, salary floor and period,
  place names, onsite rule; remote roles abroad flagged for a right-to-work check.
- Locale-aware salary parsing for boards outside the UK.
- Contact details per market; candidate name drives CV and letter file names.
- Personal settings shipped as .example.md files and kept out of git.
- Fictional sample candidate and data in examples/, with examples/dry_run.sh running every stage
  in a throwaway data folder (JOBAGENT_DATA_DIR).
- Core tests in tests/, run on every push by GitHub Actions.
