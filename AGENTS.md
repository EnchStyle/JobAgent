# AGENTS.md : guidance for AI assistants working in a JobAgent fork

Read this file before you change anything or run the pipeline for someone. It is written for
Claude (Cowork or Claude Code) and applies equally to any other coding or agent assistant.
Human-facing setup instructions are in docs/GETTING_STARTED.md.

## 1. What this project is
JobAgent is a job-application pipeline driven by an AI assistant. The assistant follows the
SKILL.md files in skills/, uses a browser extension to read job boards, and calls small Python
scripts that keep all state in a local SQLite database (jobs.db). The skills are plain folders,
not installed skills: they run only when you open and follow them. The entry point is
skills/job-pipeline/SKILL.md.

## 2. Rules that are never relaxed
1. Never submit an application, send a message or accept terms on the user's behalf without
   their explicit approval for that specific submission (one message may approve a listed batch:
   job-apply, "Batch approval"). A normal or scheduled run stops at status `verified`.
2. Never create accounts, enter passwords or one-time codes, or solve or bypass a CAPTCHA or any
   other bot detection; mark such a row `blocked_login` and put it on the hand-off sheet
   (`tracker.py handoff`). Page scripts on an application form are allowed only as
   skills/job-apply/SKILL.md ("Scripted help") describes: to attach the approved file, set a
   configured answer or open a hidden control, with the same answers as by hand. Never fill a
   hidden honeypot field and never force past a validation error by script.
3. Facts come only from profile/master_profile.md. Never invent a metric, duty, title, date,
   employer or skill, and never "improve" a fact. A requirement the profile does not evidence is
   a gap, reported as a gap.
4. Score from the full advert, never from the title. Before a role is read, only the reject-title
   list (clear mismatches) and the hard gates in filters.py may drop it; a keyword screen or a
   ranking may only order the reading queue, and unread rows stay at `found`. Never set
   `rejected` with raw SQL: `jobdb.update_status` refuses an unread rejection without a stated
   reason, and `pipeline_status.py` reports `rejected_unread`, which must be 0.
   The reject-title list itself changes only on evidence from
   `skills/job-ingest/scripts/audit_reject_titles.py` (rule: job-ingest SKILL.md, "Maintaining the
   reject-title list"); `reapply_title_list.py` then drops matching rows still at `found`.
5. Personal files never enter version control or a public place: config/application_rules.md,
   config/filters.md, config/sources.md, config/scoring_calibration.md, profile/master_profile.md,
   jobs.db and its backups, inbox/, output/, logs/. Check
   `git status` before any commit and refuse to commit these even if asked casually; explain why.
6. Respect each job board's terms. Keep the pace low, use LinkedIn only through its public guest
   pages, and stop if a site shows a block or warning.
7. Follow the user's writing rules from config/application_rules.md (by default British English
   and no em dashes in anything an employer sees).

## 3. Map of the repository
| Path | Role |
|---|---|
| skills/job-pipeline | Orchestrator; stage order, where commands run, report format |
| skills/job-ingest | Search list (scripts/search_plan.py, from config/sources.md search_plan), scraping (scrapers/*.js), normalising (scripts/normalize.py), hard filters (scripts/filters.py), storing adverts |
| skills/job-match-score | Fit scoring and status bands (scripts/save_score.py, persist_enriched.py) |
| skills/cv-tailor | CV writing via the bundled uk-cv-writer skill, naming, PDF export |
| skills/cover-letter | Letters, warrant test, PDF and Word export |
| skills/cv-verify | Independent checks, including workflow_check.py for the user's own rules |
| skills/job-apply | Applying to approved roles: repeat guard, route check, attachment check, go-ahead, hand-off (references/portals.md) |
| skills/app-tracker | Database bookkeeping CLI (scripts/tracker.py: also add, applied-to, handoff), exports, optional Gmail reconciliation |
| skills/uk-cv-writer | Bundled CV engine: UK conventions, ATS checks, grounding check against the profile |
| lib/ | jobdb.py (schema, statuses, connection, duplicate checks), config_loader.py (reads yaml blocks from config/*.md), markets.py (countries from config), paths.py, backup.py (tracker snapshots), housekeeping.py (end-of-run tidy: inbox check, newest 3 snapshots, partial downloads), runlock.py (one run at a time) |
| config/ | Behaviour, as yaml blocks inside Markdown files (.example.md files are the shipped templates) |
| profile/ | The master profile (fact base) |
| examples/ | Fictional sample candidate, advert, cards and keywords for a dry run |
| tests/ | Core tests for filters, parsing, markets and the database |

Status flow: found -> scored -> cv_generated -> verified -> applied -> interview / closed.
Side exits: rejected (with a reason in the score breakdown), blocked_login. Score bands:
60 and above get a CV; 50 to 59 is the review band (the user decides); a hold keeps a row at
scored until the user decides. Details: skills/app-tracker/references/db_contract.md.

## 4. Which configuration the code reads
Everything else in config/ is guidance that you, the assistant, read and apply.
| File (personal copy, from its .example.md) | Keys read by code |
|---|---|
| config/filters.md | default_market, markets, location_allow, foreign_location_hints, remote_hints, relevance, freshness, reject_title_contains, reject_title_word_boundary |
| config/scoring_rubric.md (shipped as is) | threshold_apply, review_floor |
| config/scoring_calibration.md | nothing (read by the assistant when scoring) |
| config/sources.md | scrape_sources.<board>.market, scrape_sources.<board>.url_base (optional listing URL prefix, e.g. another Indeed country) |
| config/application_rules.md | candidate, contact (email, phones per market, linkedin, website), never_mention, employer_rules; form_answers, on_account_wall, general_cv and portfolio are read by the assistant |
When a personal file is missing, config_loader.py reads its .example.md twin and prints a
warning. Never treat example values as the user's data; tell the user which files still need
creating. PyYAML is required; config_loader exits with an install hint if it is missing.

## 5. Helping someone set up a fork (onboarding script)
Work through this with the user, one step at a time, and confirm each before moving on.
1. Environment: confirm the folder is connected, then check `python3 -c "import yaml, docx, openpyxl"`
   and `which soffice pdftotext`. Install what is missing (`pip install -r requirements.txt`,
   LibreOffice, poppler-utils) only with the user's agreement.
2. Optional dry run with the fictional candidate: `bash examples/dry_run.sh`. It uses a
   throwaway data folder (JOBAGENT_DATA_DIR) and a config folder holding only the shipped
   examples (JOBAGENT_CONFIG_DIR), so it never touches the user's tracker or settings, and it
   prints the expected result of each step.
3. Identity and rules: interview the user (name for file names, email, one phone per market,
   LinkedIn, names that must never appear, presentation rules for past employers, standard form
   answers) and write config/application_rules.md from the example. Ask; never guess.
4. Master profile: copy skills/uk-cv-writer/assets/master-profile-template.md to
   profile/master_profile.md and fill it in with the user, section 0 first
   (profile/master_profile.example.md explains section 0; examples/master_profile.sample.md
   shows a filled one). Take facts only from what they tell you or documents they give you, and
   keep their numbers exactly. Section 0 records their presentation rules and an honest
   description of the kind of practitioner they are.
5. Filters: write config/filters.md from the example: the markets they search, salary floors,
   the places where onsite or hybrid work is acceptable, the freshness window, and a short list
   of titles they will never apply for.
6. Sources: write config/sources.md from the example: job families (a few keywords each, marked
   standing or on request), the places each family is searched in, and enable only the boards
   that cover their country. `python3 skills/job-ingest/scripts/search_plan.py --list` shows the
   size of a normal run.
7. Scoring: write config/scoring_calibration.md from its example with two or three examples from
   their own profile (that file is git-ignored because it describes their career), and confirm whether sales roles stay
   excluded (config/scoring_rubric.md).
8. First real run: one board, one search, then `python3 skills/job-pipeline/scripts/pipeline_status.py`.
   Review the ingest report (reject_reasons) and the scored roles with the user before writing
   any CV.

## 6. Adding a board or a market
- An employer site with no search (one page lists every vacancy): a board with `fixed_urls` in the search plan, an async extractor (it reads the one listing page, and each vacancy page when pay or the closing date appear only there) and a `normalize_<board>()`.
- A board: write `skills/job-ingest/scrapers/<board>.js` (store cards in `window.__jobs`, or
  `window.__acc` for accumulate-across-pages boards), add `normalize_<board>()` to
  `skills/job-ingest/scripts/normalize.py` and register it in `NORMALIZERS` and `URL_BASE`, and
  add a block with `market:` under scrape_sources in config/sources.md and its URL templates
  (`remote`, `city`) under search_plan.boards. Use `parse_salary_any()` unless the board has
  quirks of its own. Cards from a board with no normaliser are reported as
  `no_normalizer:<board>` in the ingest report and a warning is printed.
- A market: add an entry under `markets` in config/filters.md (label, currency, salary_floor,
  floor_period, default_salary_period, location_hints, unlisted_onsite, optionally
  generic_location_terms), places under `location_allow`, the language's words for remote work
  under `remote_hints` (for example "homeoffice"), its places under search_plan.places in
  config/sources.md, a phone under contact.phones in
  config/application_rules.md, and remove that country from foreign_location_hints.
- Place hints match at the start of a word ("manch" matches "Manchester"); write "re:<pattern>"
  for an exact rule, such as "re:\\buk\\b" so that "uk" never matches "Ukraine". Onsite or hybrid
  roles in a place listed under foreign_location_hints are rejected (onsite_abroad); remote
  roles there are kept and flagged verify_right_to_work.
- CV conventions: uk-cv-writer produces UK-style CVs (two pages, British spelling, no photo or
  date of birth) and its check_cv.py enforces them. For a US résumé or a German Lebenslauf, say
  so plainly and agree an approach with the user (a variant skill, or adjusted checks) before
  writing CVs; never silence a failing check.
- Extractors depend on each site's page structure and break when a site changes. Fix the
  selector in the .js file, re-test on one page, and compare the ingest counts with an earlier run.
- Optional pieces: Gmail reconciliation (skills/app-tracker) needs a Gmail connector; the
  cover-letter plain-style pass uses the avoid-ai-writing skill if installed.

## 7. Environment notes
- In Claude Cowork the scripts run in the Cowork shell, where the folder is mounted at
  `$HOME/mnt/<folder name>`; every command starts with `cd` into it. That mount cannot delete
  files and cannot host SQLite WAL files, which is why jobdb.py uses TRUNCATE journaling. These
  limits do not apply to a local clone run with Claude Code; the code works in both.
- The database schema is created automatically on first use (`python3 lib/jobdb.py` also does it).
- Working data (jobs.db, inbox/, output/, logs/) lives in the project folder unless the
  environment variable JOBAGENT_DATA_DIR points elsewhere. File paths stored in jobs.db are
  relative to that data folder; cv_name.py and register_cover.py --print-name print absolute
  paths to write to, and the register scripts convert them back. JOBAGENT_CONFIG_DIR likewise
  points the scripts at another config folder.
- Keep scratch files outside the project folder.
- The browser tool returns only about 1,000 characters from a JavaScript call, so extractors keep
  cards in the page and the assistant reads them back with get_page_text (job-ingest SKILL.md).

## 8. Before you change code
- Keep behaviour configurable in config/ rather than hard-coded.
- Run `python3 -m pytest -q` after changes. After any change to filters.py or normalize.py, also
  re-run ingest on a saved inbox file and compare kept and rejected counts with the previous run.
- Never weaken a check in cv-verify or uk-cv-writer to make a document pass; fix the document.
- Before changing reject_title_contains or reject_title_word_boundary, run
  audit_reject_titles.py and keep the collisions at zero, or record why an entry stays.
- Never add real personal data to examples, comments or tests.
