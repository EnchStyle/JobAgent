# JobAgent

> **No coding needed.** JobAgent runs inside Claude Cowork, in the Claude desktop app. You talk to
> Claude in plain English ("set me up", "run the job pipeline", "apply to roles 12 and 15") and it
> does the technical work, including the setup. You never write or run code yourself and never open a
> terminal; all you need is a Claude subscription and the Claude in Chrome extension.

A semi-autonomous job-application pipeline run by an AI assistant in Claude Cowork. On request it
collects fresh vacancies from job boards, applies hard filters (salary, location, freshness),
reads every advert in full, scores each role against your master profile, writes a tailored CV
(and a cover letter where one helps), checks every document independently, and records
everything in a local SQLite database. It never submits an application on its own: finished
applications wait for you, and applying happens only when you ask and approve each submission.

New here? Read docs/GETTING_STARTED.md. AI assistants working in this folder: read AGENTS.md first.

## How it works

The pipeline is a set of skills (folders with a `SKILL.md` and small Python helpers) that the
assistant follows step by step. The entry point is `skills/job-pipeline/SKILL.md`.

| Stage | Skill | What happens |
|---|---|---|
| 1. Collect | job-ingest | Claude in Chrome opens each search page, a small extractor reads the job cards, and `scrape_ingest.py` applies the hard filters and removes duplicates |
| 2. Read | job-ingest | The full advert is stored for every kept role; nothing is scored from a title |
| 3. Score | job-match-score | Each advert is mapped requirement by requirement to the master profile and scored 0 to 100 |
| 4. CV | cv-tailor | A fresh CV is written with the bundled uk-cv-writer skill and exported to PDF |
| 5. Letter | cover-letter | A letter is written only where it changes the outcome, then checked |
| 6. Verify | cv-verify | An independent check of structure, keywords, grounding in the profile and your own rules |
| 7. Track | app-tracker | Status, notes, closing dates and an Excel overview of every role |
| On request | job-apply | Applies to roles you approve, one at a time, with your go-ahead for each role or for a listed batch; roles behind an account wall go to a hand-off sheet for you |

Scores of 60 and above receive a CV automatically; 50 to 59 is a review band for you to decide.
Thresholds, filters, markets and what to search are plain Markdown files in `config/`, so
behaviour can be changed without touching code.

## What it searches, and running it on a schedule

What is searched is set in one place, the `search_plan` block of `config/sources.md`: job
families (a few keywords each), the places each family covers, and a URL template per board.
Families marked `standing` are searched on every normal run; the others only when you ask
("scan delivery roles"), and a request never changes your settings. Searches rotate, so each run
stays a manageable size and a missed run is caught up next time.

A scheduled run (a Cowork scheduled task with your computer on, the desktop app open and Chrome
signed in to the boards) searches, reads, scores, writes and checks CVs, and reports. It never
submits an application, signs in, creates an account or solves a CAPTCHA: those wait for you.

Boards with extractors: CV-Library, Reed and Indeed (United Kingdom),
and LinkedIn through its public guest pages only. All ship disabled until you add your own
searches.

## Included skills you can use on their own

`skills/uk-cv-writer` is a complete CV skill in its own right: it tailors a master profile to one
advert and checks layout, keywords and grounding. Copy that folder into your own Claude skills to
use it without the rest of the pipeline; see its README.

## Requirements

- The Claude desktop app with Cowork, this folder connected to a session, and the Claude in
  Chrome extension signed in to the job boards you use.
- Python 3.10 or later with the packages in `requirements.txt`
  (`pip install -r requirements.txt`). In Cowork the scripts run in the Cowork shell, which
  usually has them already; you do not need Python on your own computer. If you run the skills
  with Claude Code on your own machine instead, install them there.
- LibreOffice (`soffice`) for PDF export and page counts, and poppler-utils (`pdftotext`) for
  the CV checks.
- Optional: a Gmail connector in the Claude app (matching confirmation emails to the tracker),
  and the avoid-ai-writing skill (a plain-style pass on cover letters).

## Quick start

1. Download or clone this repository and connect the folder in a Cowork session.
2. Say: "Read AGENTS.md and help me set up JobAgent." The assistant walks you through:
   - `config/application_rules.md` (from the `.example.md`): your name, contact details, names
     that must never appear, standard form answers;
   - `profile/master_profile.md`: your full career record, the only source of facts;
   - `config/filters.md` and `config/sources.md` (from their `.example.md` files): markets,
     salary floors, acceptable office locations, rejected titles, and your job families and places.
3. Optional: `bash examples/dry_run.sh` runs every stage on a fictional sample candidate in a
   throwaway folder, so you can see the pipeline work before you scrape anything.
4. "Run the job pipeline."

Until you create your own copies, the scripts read the `.example.md` files and print a warning.
Your personal files (`application_rules.md`, `filters.md`, `sources.md`, `master_profile.md`,
`jobs.db`, `inbox/`, `output/`, `logs/`) are in `.gitignore` and stay on your computer.

## Countries and CV style

Markets (countries) are configured in `config/filters.md`: currency, salary floor and period,
place names, and how onsite roles elsewhere are treated. The examples are set up for the UK
(London and Manchester), with a commented example of a second market. A new country needs a market entry, a board extractor and normaliser (see AGENTS.md,
"Adding a board or a market"), and possibly a different CV style: the bundled uk-cv-writer
produces UK conventions (two pages, British spelling, no photo or date of birth), which suit the
UK and most of Europe but not, for example, a one-page US résumé or a German Lebenslauf.

## Folder map

```text
JobAgent/
├── README.md, AGENTS.md, CHANGELOG.md, LICENSE
├── docs/          GETTING_STARTED.md (setup guide), FILE_STRUCTURE.md (every file explained)
├── config/        example settings: markets and filters, sources, scoring, application rules
├── profile/       how to write your master profile
├── examples/      fictional candidate, advert and scraped cards for a dry run
├── lib/           shared helpers: database, config loader, markets, paths, backups
├── skills/        the pipeline, one folder per stage
│   ├── job-pipeline      entry point
│   ├── job-ingest        search plan, board extractors, hard filters
│   ├── job-match-score   reading and scoring
│   ├── cv-tailor         tailored CVs
│   ├── cover-letter      letters where they help
│   ├── cv-verify         independent checks
│   ├── job-apply         applying to approved roles
│   ├── app-tracker       tracker, Excel overview, Gmail matching
│   └── uk-cv-writer      bundled CV skill, usable on its own
└── tests/         core tests (`python3 -m pytest -q`), run on every push
```
Created on first use and never committed: your `config/*.md` files, `profile/master_profile.md`,
`jobs.db`, `inbox/`, `output/`, `logs/` and `backups/`. The full annotated tree is in
docs/FILE_STRUCTURE.md.

## Important limitations

- Job boards have terms of use, and some restrict automated access. You are responsible for how
  you use this tool. Keep the pace low, use only boards you are permitted to use, and read each
  board's terms. LinkedIn can restrict accounts that are automated; the pipeline uses only its
  public guest pages for that reason.
- Board extractors depend on each site's page layout and will need updating when a site changes.
- Nothing is submitted without your explicit approval. Logins, new accounts and CAPTCHAs are
  always left to you.
- The output is only as good as your master profile. The checks flag invented numbers and
  claims, but you remain responsible for what you send.

## About this project

JobAgent began as an experiment. Looking for a job now means reading hundreds of adverts and
rewriting the same CV again and again, and the question was how much of that routine an AI
assistant could take on while every decision stays with the person. It was inspired by
Santiago Fernández's [career-ops](https://github.com/santifer/career-ops) and aims to make the
same idea usable without writing code. It was designed and built with Claude, so expect
pragmatic code rather than a polished library. See CONTRIBUTING.md for how to help and
CHANGELOG.md for what changed.

## Licence

MIT, see `LICENSE`.
