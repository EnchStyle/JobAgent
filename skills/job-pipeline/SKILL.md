---
name: job-pipeline
description: Runs the JobAgent job-search pipeline end to end, or any part of it, from the connected JobAgent project folder. Scrapes the boards, reads every advert, scores fit, writes and verifies CVs and cover letters, updates the tracker and the scan workbook, and stops before anything is submitted unless the user asks. Use for "run the pipeline", "do the daily job run", "scan for new jobs and prepare applications", "process what's in the tracker", or applying to roles they have approved.
---

# job-pipeline

The entry point for a JobAgent run. It sequences the stage skills, keeps jobs.db and output/ in
a consistent state, and ends with a short report of what needs the user. Each stage skill owns its
own rules; this file only says what runs when, and what holds for every stage.

## Where things run
- The project root is the JobAgent folder the user connected to the Cowork session (in a
  Cowork session it is mounted at `$HOME/mnt/<folder name>` in the shell on the user's
  computer). jobs.db lives there, so run every script in that shell, from the root. Each shell
  call starts fresh: begin every command with `cd "$HOME/mnt/<folder name>" &&`.
- Browser work (scraping, reading adverts, applying) goes through Claude in Chrome in the user's
  signed-in browser. If the browser is not connected, do everything that does not need it and
  say what is waiting.
- The connected folder may refuse deletions and SQLite runs in TRUNCATE journal mode there;
  leave both as they are (the scripts report what they could not delete). Keep scratch files out
  of the project (use $HOME or /tmp in that shell).
- One run at a time: start with `python3 lib/runlock.py acquire --label <manual|scheduled>`
  (exit 1 means another run holds the folder: stop and say so) and end with
  `python3 lib/runlock.py release`, also after a failed run.

## Sources of truth (read these, not summaries of them)
- profile/master_profile.md : every fact about the candidate. Section 0 holds their CV output rules.
- config/application_rules.md : name and contact details, what never appears in an
  application, employer presentation rules, dashes, cover-letter gaps, and standard answers for
  forms.
- config/sources.md, config/filters.md, config/scoring_rubric.md : where to search, the hard
  gates, and how fit is scored. A personal config file the user has not created yet is read from
  its .example.md twin (the scripts print a warning); in that case say so in the report.
- jobs.db is the state. `python3 skills/job-pipeline/scripts/pipeline_status.py` shows what is
  waiting at each stage, so an interrupted run resumes from there.

## Stages
1. **Collect** (skills/job-ingest/SKILL.md): run the searches that
   `skills/job-ingest/scripts/search_plan.py` lists (the standing families, or only what the user
   asked for this time) and ingest the cards. If the user says the scraping is done, or asks to work from the tracker,
   skip this and start at stage 2 with whatever is at `found`.
2. **Read every advert** (job-ingest, "Reading adverts"): for each `found` row, open the advert
   and store its text. A score is only ever made from the advert, never from a title, because
   titles mislead (the same title can hide a role in a different field that excludes the
   candidate's background).
3. **Score** (skills/job-match-score/SKILL.md). Adverts close; score soon after reading, and
   treat a passed closing date as expired.
4. **CVs** (skills/cv-tailor/SKILL.md) for every row that `skills/cv-tailor/scripts/eligible.py`
   lists (scored 60 or more, not on hold). Review-band rows (50 to 59) and held rows wait for
   the user.
5. **Cover letters** (skills/cover-letter/SKILL.md) where the warrant test says one helps.
6. **Verify** (skills/cv-verify/SKILL.md) every CV at `cv_generated`. If you can hand this stage
   to a sub-agent, do: a reviewer that did not write the CV catches more. A failed CV goes back
   to stage 4 with the fixes; try at most twice, then leave it for the user.
Before a large batch (an ingest, a scoring sweep, an apply session), snapshot the tracker:
`python3 lib/backup.py --label <stage> --keep 3`.

7. **Report**: run `python3 skills/app-tracker/scripts/export_workbook.py`, then
   `python3 skills/job-pipeline/scripts/pipeline_status.py --log "<one-line summary>"` (this is
   the run log; write it at the end of every run, including partial runs and apply sessions),
   then send the user the report below. Mention anything in `closing_within_3_days`.
   Every count under `checks` must be 0 before a run is reported complete (`pipeline_status.py
   --check` exits 1 otherwise): `rejected_unread` (roles rejected without a full read: put them
   back to `found` and read them), `scored_without_mapping` (a number with no requirement
   mapping: re-score from the advert) and `scored_older_than_21_days` (close them with
   `tracker.py set-status --status closed --note "stale"`, which can be undone; list them in the
   report). Finally run `python3 lib/housekeeping.py`: it lists inbox files that were never
   ingested, keeps the newest 3 tracker snapshots and removes unfinished downloads.

Stay within what the stages' queues hold. Anything else you notice (review-band rows, a
verified row whose files are missing, old rows that look stale) goes in "Needs you" rather than
being reworked during the run; marking an obviously closed or duplicate advert is fine.

For a large batch, work in chunks of about 20 rows and write results to jobs.db as you go
(persist_enriched.py takes a whole chunk of scores in one call). The database then holds the
progress, your context stays small, and nothing is lost if the session stops.

## Unattended (scheduled) runs
A scheduled run is a normal run with nobody watching. It does stages 1 to 7 in full:
- Scope: the standing families only (`search_plan.py` with no options). It never edits config.
- No caps of its own: it runs every due search, reads and scores every new advert, and writes a
  CV for every eligible role. Progress is saved as it goes (searches recorded with --done, scores
  in batches, adverts left unread stay at `found`), so a run that is cut off is resumed by the
  next one. Only LinkedIn and Indeed take a few searches per run (`max_searches` in sources.md),
  to protect the account and avoid bot checks.
- It prepares applications but does not send them: with nobody to approve each submission, the
  run ends with the ready list (role, CV, letter, the answers that will be used) for the user to
  approve in one message (job-apply, "Batch approval").
- Snapshot first (`lib/backup.py --label scheduled --keep 3`) and take the run lock; finish with
  `pipeline_status.py --check --log "..."`, housekeeping and the lock release. If --check fails,
  the report says so at the top.
- The report is the run's final message: new roles by band, the ready list, roles closing within
  3 days, boards that were blocked, and anything under "Needs you".
Needs: the user's computer on, the Claude desktop app open, Chrome running with Claude in Chrome
and signed in to the boards and portals, and the JobAgent folder connected.

## Applying (only when the user asks)
A normal run stops at `verified`. When the user asks you to apply to specific roles, follow
skills/job-apply/SKILL.md: repeat guard, route check before any typing, attach and confirm the
tailored CV, answers only from config/application_rules.md, the user's go-ahead for every
submit (per role, or one yes for a listed batch), and a hand-off sheet (`tracker.py handoff`)
for roles that need a new account, a password, a one-time code or a CAPTCHA.

## Report to the user
Keep it short. A table of the roles that moved (id, role, employer, score, outcome), counts for
the rest, the files produced, and a numbered "Needs you" list (review-band roles, holds, blocked
applications, questions). Leave out command logs and anything the user did not ask about.
