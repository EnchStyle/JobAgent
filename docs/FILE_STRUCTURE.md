# File structure

Every file in the repository, with one line on what it does. Folders marked "created on first
use" hold your own data; they are excluded from git and are not in the repository.

```text
JobAgent/
├── README.md                     overview, requirements, quick start
├── AGENTS.md                     rules and map for the AI assistant (read first)
├── CLAUDE.md                     pointer to AGENTS.md for Claude
├── CHANGELOG.md                  what changed in each version
├── CONTRIBUTING.md               how to report problems and propose changes
├── LICENSE                       MIT licence
├── requirements.txt              Python packages
├── .gitignore                    keeps your personal files out of git
├── .github/
│   ├── ISSUE_TEMPLATE/extractor-broke.md   template for a board that stopped working
│   └── workflows/tests.yml                 runs the tests on every push
├── docs/
│   ├── GETTING_STARTED.md        setup guide for a new user
│   └── FILE_STRUCTURE.md         this file
├── config/                       settings, as yaml blocks inside Markdown
│   ├── application_rules.example.md    your name, contacts, form answers, never-mention list
│   ├── filters.example.md              markets, salary floors, office places, rejected titles
│   ├── sources.example.md              job families, places, boards and search URLs
│   ├── scoring_rubric.md               score bands (60+ CV, 50 to 59 review); shipped as is
│   └── scoring_calibration.example.md  worked scoring examples to copy and replace
├── profile/
│   └── master_profile.example.md how to write your master profile, the only source of facts
├── examples/                     fictional candidate for a dry run (no personal data)
│   ├── dry_run.sh                runs every stage in a throwaway folder
│   ├── master_profile.sample.md  filled-in sample profile (Jordan A. Bennett)
│   ├── advert_example.txt        sample advert
│   ├── keywords_example.json     sample keywords for the CV check
│   └── inbox/                    two sample scrape files (Reed, LinkedIn)
├── lib/                          shared Python helpers
│   ├── __init__.py               marks lib/ as a package
│   ├── jobdb.py                  database schema, statuses, duplicate checks
│   ├── config_loader.py          reads the yaml blocks in config/
│   ├── markets.py                countries, currencies, place matching
│   ├── paths.py                  data and config folder locations
│   ├── backup.py                 tracker snapshots
│   ├── housekeeping.py           end-of-run tidy
│   └── runlock.py                one run at a time
├── skills/                       the pipeline; each folder has a SKILL.md the assistant follows
│   ├── job-pipeline/             entry point: stage order and the run report
│   │   └── scripts/pipeline_status.py
│   ├── job-ingest/               collecting and filtering adverts
│   │   ├── scrapers/             one browser extractor per board
│   │   │   ├── cv_library.js, indeed.js, linkedin.js (public guest pages)
│   │   │   └── reed_web.js, reed_fetch.js (bulk)
│   │   └── scripts/
│   │       ├── search_plan.py    builds each run's searches from config/sources.md
│   │       ├── scrape_ingest.py  hard filters, dedupe, insert
│   │       ├── normalize.py      turns each board's cards into one format
│   │       ├── filters.py        salary, location, freshness and title gates
│   │       ├── save_description.py   stores the full advert
│   │       ├── known_ids.py      ids already tracked, so they are skipped
│   │       ├── audit_reject_titles.py  evidence check for the rejected-title list
│   │       └── reapply_title_list.py   applies that list to unread rows
│   ├── job-match-score/          reading each advert and scoring the fit
│   │   └── scripts/              save_score.py, persist_enriched.py, list_unscored.py
│   ├── cv-tailor/                tailored CV per role, file naming, PDF export
│   │   ├── references/tailoring.md
│   │   └── scripts/              cv_name.py, eligible.py, export_pdf.py, register_cv.py
│   ├── cover-letter/             letters only where they help
│   │   ├── references/warrant.md
│   │   └── scripts/              export_cover_files.py, register_cover.py
│   ├── cv-verify/                independent check of every document
│   │   ├── references/checks.md
│   │   └── scripts/              workflow_check.py, record_verdict.py
│   ├── job-apply/                applying to approved roles, hand-off sheet
│   │   └── references/portals.md known application-site quirks
│   ├── app-tracker/              tracker commands, Excel overview, optional Gmail matching
│   │   ├── references/           db_contract.md, gmail_reconcile.md
│   │   └── scripts/              tracker.py, export_workbook.py, export_shortlist.py,
│   │                             export_scraping_tab.py, reconcile_gmail.py, reconcile_apply.py
│   └── uk-cv-writer/             bundled CV skill, also usable on its own
│       ├── SKILL.md, README.md, CHANGELOG.md
│       ├── assets/               cv-content-schema.json, master-profile-template.md
│       ├── references/           UK standards, ATS formatting, bullets, tailoring, integrity
│       └── scripts/              build_cv.py, check_cv.py, check_grounding.py
├── tests/                        test_core.py, conftest.py, fixtures/cards.json
│
│   created on first use (your data, never committed):
├── config/*.md                   your own settings, copied from the .example.md files
├── profile/master_profile.md     your career record
├── jobs.db                       the tracker (SQLite)
├── inbox/                        scraped cards waiting for ingest, then archived
├── output/                       CVs, cover letters, jobs_overview.xlsx, hand-off sheets
├── logs/                         run logs
└── backups/                      tracker snapshots
```
