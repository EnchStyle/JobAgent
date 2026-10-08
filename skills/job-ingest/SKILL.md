---
name: job-ingest
description: First stage of the JobAgent pipeline. Scrapes the job boards configured in config/sources.md through Claude in Chrome, saves the cards, runs the hard filters and dedupe (scrape_ingest.py) to add new roles to jobs.db at status found, then reads and stores the full advert for every found role so it can be scored. Use for "scan for new jobs", "scrape the boards", "ingest these scrape files", or "read the adverts for the new roles".
---

# job-ingest

Collect broadly, let the code apply the hard gates, then store each advert so the scorer works
from the real text. The title filter removes only clear mismatches (titles you will never apply
for); every other role has its full advert read before anything is decided. Never reject a role
by a keyword screen of the title, a snippet or the advert before its advert is read by you.
A keyword score or ranking may only decide the ORDER in which adverts are read; rows you have
not read yet stay at `found`, never `rejected`, however many there are. If there are too many
to read in one run, say so in the report and carry them over. (A keyword ranking can
reject many good roles unread; many of them score well on a full read.) If the candidate's career spans several fields, cast the net wide and let
scoring decide: it is far better to read a few extra adverts than
to lose a good role to a narrow search (a category filter that is too narrow can hide a
well-fitting role filed under another category).

Run every command from the project root (see job-pipeline, "Where things run").

## What you need
- config/sources.md (or sources.example.md until you create your own) : the `search_plan`
  (job families, places, URL templates), the enabled boards with their extractors, and the
  per-board method notes (pagination, LinkedIn guest endpoints, the Reed remote filter).
- config/filters.md : salary floors, the location rule, the freshness window, the reject-title
  list. The code reads these; you do not re-apply them by hand.

## 1. Scrape (Claude in Chrome, the user's signed-in browser)
Get this run's searches from the plan; never make up a search list:
- a normal or scheduled run: `python3 skills/job-ingest/scripts/search_plan.py`
- a specific request: `... search_plan.py --family <family>` or
  `... search_plan.py --keywords "<kw>,<kw>" [--places london,uk_remote]`. A request changes
  nothing in config; add or change a family in config/sources.md only when the user says so.
State the scope in the report ("standing" or the request). For each search in the plan:
1. Load the ids already tracked, so the extractor skips them:
   `python3 skills/job-ingest/scripts/known_ids.py --source <source>`, then set
   `sessionStorage['__known']` to that JSON array in the board's tab. (LinkedIn's guest pages
   ignore this list; duplicates there are removed at ingest.)
2. Open the search URL (tabs_create_mcp, navigate) sorted newest first where the board allows.
3. Inject `skills/job-ingest/scrapers/<source>.js` with javascript_tool. It stores the page's
   cards in `window.__jobs` (LinkedIn and Indeed: `window.__acc`) and returns a count.
4. Page back until the newest card on a page is older than the search's `stop_after_days`
   (never beyond config/filters.md max_days_old). Accumulate as you go: CV-Library is a single-page app, so a
   window variable survives its page clicks; LinkedIn pages with `&start=0,10,20`.
5. Read the cards back once, at the end, without hitting the javascript_tool output limit:
   ```js
   const s = JSON.stringify(window.__jobs); const p = document.createElement('pre');
   p.textContent = s; document.body.innerHTML = ''; document.body.appendChild(p); s.length
   ```
   (LinkedIn and Indeed: `window.__acc`), then call get_page_text. This replaces the page, which is why it
   comes last.
6. Save them as `inbox/scrape_<search>_<source>_<yyyymmdd>.json` (any name that starts with
   `scrape_` and ends with the date works; the source is read from inside the file) in the form
   `{"source": "<source>", "cards": [...]}`. Add `"remote": "remote"` at the top level when the
   plan marks the search `remote_filtered`, so those rows are not flagged for a remote check.
   LinkedIn arrays can be saved as they are.
7. Record it: `python3 skills/job-ingest/scripts/search_plan.py --done <search id>` (several ids
   at once is fine). A search that was blocked or failed is not recorded, so it stays due.
Employer sites: a company's own vacancy page, one fixed URL each, no
paging and no keywords (a `fixed_urls` board in the search plan). Their extractors are async: run them with
`await`, for example `await (async () => { <file contents> })()`, then dump and save as in steps 5 to 7.
- `reed_fetch.js` is the bulk method for Reed: it fetches the search pages with fetch + DOMParser (no page
  rendering, no iframes, so the tab stays responsive) and walks up to 14 pages of every search in the plan in a few
  minutes. Set `window.__RURLS` (search paths), optionally `window.__SUB` (title reject regex) and `window.__KNOWN`
  (tracked ids), run `window.__go(0, n)`, poll `window.__prog`. Use it instead of `reed_web.js` for a full sweep.
- CV-Library pages: add `&page_number=N` (the site ignores `page`) and `&posted=3` for the last three days; cards show
  'Posted 2 days ago by ...', which `normalize` converts to a date.
- An employer-site extractor that reads each vacancy page as well as the list page fills pay, place and
  `closing_date` on the card, so the pay floor and the closed-date gate apply before anything is read; skip
  vacancies already tracked through `__known`. When a list shows no pay, level or posted date, internships,
  evergreen requisitions ("no position is available at the moment") and sales roles can reach the reading
  step: reject them there after reading (evergreen: reason expired; internship: other; sales: sales).
- Applying through an employer site needs the user's own account, signed in already (no account is created;
  hand-off otherwise).
javascript_tool refuses output that looks like a query string or cookie data (key=value pairs, or a page
URL with a query string); return plain sentences or JSON, and use the dump and get_page_text route for cards.
Pause for any login or CAPTCHA and ask the user. LinkedIn: only the guest endpoints in
sources.md, a few searches, no rapid paging; the signed-in LinkedIn app risks the user's account.

## 2. Ingest
`python3 skills/job-ingest/scripts/scrape_ingest.py --pattern "scrape_*_<yyyymmdd>.json"`
It normalises each card (salary, work mode, posted date), applies the hard filters, dedupes by
the board's job id, inserts survivors as `found` with any flags (salary_unknown,
verify_location), writes logs/scrape_ingest_<timestamp>.log and prints a JSON report. Ingested
files move to inbox/_archive_<YYYYMM>/; an unreadable file stays in inbox/ and is reported.
If the files were scraped on an earlier day, add `--as-of <scrape date>`: relative dates ("3 days
ago") and the freshness window are then counted from the scrape, not from today.

## 3. Reading adverts (every `found` row, before scoring)
For each row (`python3 skills/job-match-score/scripts/list_unscored.py` lists them, with has_jd):
1. Open its url and get_page_text.
2. If the text is only the site shell, the advert is elsewhere:
   - Some boards embed the employer's ATS in a cross-origin iframe (common with
     large banks, consultancies and retailers). Get the src with
     `[...document.querySelectorAll('iframe')].map(x=>x.src).find(s=>s && !/youtube/.test(s))`,
     open it, and read the text there.
   - No iframe and no text: the advert is an image. Take a screenshot and transcribe it.
   - LinkedIn: read `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<job_id>`.
3. Save the advert: write the text to a scratch file and run
   `python3 skills/job-ingest/scripts/save_description.py --id N --file <scratch file>`
   (add --salary-min/--salary-max/--salary-period when the advert states pay the card lacked,
   and --closing-date YYYY-MM-DD when it states a closing date).
4. If the script reports `maybe_truncated` (very short text, or a "show more" stub, common on
   board guest pages), open the employer's own page for the role and store the full text.
5. Boards refresh posted dates: when the employer's page shows an older posting date than the
   card, note it (`tracker.py note`), and treat an old posting as possibly closed.

What to store: the advert as published, in its original language, from the job title to the end
of the requirements and application details. Keep the closing date, salary, location and working
pattern sentences exactly as written. Leave out site navigation, cookie banners and generic
company boilerplate. Do not summarise, translate or paraphrase: the CV stage mirrors the advert's
own wording for ATS keywords and chooses the CV language from it, and a paraphrase quietly
breaks both. If an advert is very long, cut whole boilerplate sections, not sentences.

If the advert is gone or has closed, record it instead of guessing:
`python3 skills/app-tracker/scripts/tracker.py set-status --id N --status rejected --note "expired: advert no longer online"`.
If two rows are the same role on two boards, keep the fuller one and reject the other with
`--note "duplicate of <id>"`.

Roles found outside the boards (an alert email, a career site listed under career_sites in
config/sources.md, a role the user names) are added with `python3 skills/app-tracker/scripts/tracker.py add --title ... --company ...
--url ... [--closing-date ...]`; it warns about a possible duplicate.

## Maintaining the reject-title list
The list in config/filters.md drops a role on its title alone, before anyone reads it, so every
entry needs evidence from the tracker, not a hunch. Before adding or removing an entry, run
`python3 skills/job-ingest/scripts/audit_reject_titles.py` (read-only; `--json <file>` keeps the
full result). It reports:
- collisions: entries that would hide a role scored 50 or more, or applied to;
- substring entries that fire inside a longer word (move an English word to
  `reject_title_word_boundary`; stems in inflected languages are meant to match longer words);
- what each entry dropped from the archived cards, and which of those were target titles
  (`relevance.title_any`);
- candidates: title words and phrases found in at least 8 adverts read and scored, none of which
  scored 50 or more or was applied to.
A candidate is evidence, not a decision. Add it only when it names work the user does not do (a job
family, or a non-job such as an internship or a paid course), never a field, technology, employer,
place or contract word, and when its best score is 40 or lower; the full rule is in the
"Reject-title pre-filter" section of config/filters.md. Narrow or remove an entry that collides,
unless the user has kept it on purpose. Employer rejections are not evidence for this list: those
roles were judged a fit before applying. Record the evidence in a dated comment beside the entries.
After the list changes, snapshot the tracker (`python3 lib/backup.py --label pretitlelist`), then
`python3 skills/job-ingest/scripts/reapply_title_list.py` (dry run) and `--apply`: it drops only
rows still at `found` and writes the matching entry into each row's notes. A role that has been
read is never rejected on its title.

## Report
List every source that was blocked (a bot check, a login wall) or returned nothing, so gaps in
coverage are visible; never try to get round a bot check.
Counts by source (cards, inserted, duplicates, dropped by reason; the script's JSON has them per
source), anything unusual (a source that returned nothing, a login wall, a page that would not
load), the scope (standing or the request) and how many due searches were left for the next run,
and what is waiting: the number of `found` rows whose adverts still need reading. Do not score or
rank from titles here.
