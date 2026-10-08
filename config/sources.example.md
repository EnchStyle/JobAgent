# sources.example.md : WHERE and WHAT to search

Copy this file to `config/sources.md` (ignored by git), replace the example families with your
own and set `enabled: true` for the boards you use. Every board ships disabled, so nothing is
scraped until you have chosen your own searches.

Sourcing is web scraping through Claude in Chrome (your signed-in browser). The `search_plan`
block is the one place that decides what is searched: job families (keyword lists), places, and
a URL template per board. `skills/job-ingest/scripts/search_plan.py` turns it into the list of
searches for a run; the extractor for each board is a small JavaScript file under
skills/job-ingest/scrapers/.

## Scope of a run
- A normal run (scheduled, or "run the pipeline") searches every family marked `standing: true`.
- A request for something specific ("look for product roles in London") runs only that family or
  those keywords, for that run (`search_plan.py --family ...` or `--keywords ... --places ...`).
  It never changes this file; you decide what becomes standing.
- Rotation: a standing search is due again `cycle_days` after it last ran; a run takes the due
  searches, oldest first, up to `max_searches_per_run`. A run that is cut short is caught up next
  time. `python3 skills/job-ingest/scripts/search_plan.py --list` shows the size of a normal run.

## How scraping works (full steps in skills/job-ingest/SKILL.md)
For each search in the plan: open the URL sorted newest first, inject the board's extractor,
page back until cards are older than the search's `stop_after_days`, read the cards back in one
go (write them into the page, then get_page_text; the JavaScript tool returns only about 1,000
characters), save them to inbox/, and record the search with `search_plan.py --done <id>`.
`scrape_ingest.py` then filters, dedupes and inserts the survivors. Every kept row has its full
advert read before it is scored. Pause on any login or CAPTCHA and hand over to the user.

## Building your families
- A few keywords per family; the scorer reads every advert, so slightly broad beats narrow.
- Give each family the places where you would work: a remote search, plus a city search for
  each place listed in config/filters.md location_allow (remote searches hide onsite roles).
- `board_salary_factor` puts a salary filter below your floor into board URLs, so a range that
  reaches your floor (for example 32k to 45k against a 40k floor) is not hidden by a board that
  filters on the bottom of the range; the code applies the real floor the way the market's
  `salary_range_rule` says (top by default). A market can set its own `board_salary_factor` in
  config/filters.md (use 1.0 with `salary_range_rule: bottom`).
- A family with `any_role: true` has no keywords and lists every role in its places: useful for
  a small local market where you would take any office pattern. Avoid it for a big city.
- Keep the pace low, and read each board's terms of use before enabling it.

```yaml
search_plan:
  cycle_days: 3
  max_searches_per_run: 40
  board_salary_factor: 0.75    # board filter = floor x 0.75, so a range that reaches the floor is not hidden
  places:
    uk_remote: {market: uk, remote: true}
    london:    {market: uk, city: London, location: "London, England, United Kingdom"}
    manchester: {market: uk, city: Manchester, location: "Manchester, England, United Kingdom"}
  families:                     # priority order
    local_any_role:             # every role in a place where any working pattern suits you
      standing: false           # set true to use it; the board needs a `city_any` template
      any_role: true
      places: [london]
    product:
      standing: true
      places: [uk_remote, london, manchester]
      keywords: [product manager, product owner]
    data:
      standing: true
      places: [uk_remote, manchester]
      keywords: [data analyst]
    delivery:
      standing: false           # on request only: search_plan.py --family delivery
      places: [uk_remote]
      keywords: [project manager]
  boards:   # {slug} keyword-with-hyphens, {q} / {q_plus} encoded keyword, {city_slug}, {location_q}, {floor}
    cv_library:
      remote: "https://www.cv-library.co.uk/{slug}-jobs?salarymin={floor}"   # national search
      remote_is_filtered: false
      city: "https://www.cv-library.co.uk/{slug}-jobs-in-{city_slug}?salarymin={floor}"
      skip_cities: [London]     # the national search already lists London roles
    reed:
      remote: "https://www.reed.co.uk/jobs/remote-{slug}-jobs?salaryFrom={floor}"
      city: "https://www.reed.co.uk/jobs/{slug}-jobs-in-{city_slug}?salaryFrom={floor}"
      city_any: "https://www.reed.co.uk/jobs/jobs-in-{city_slug}?salaryFrom={floor}"
    linkedin:
      remote: "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={q}&location=United%20Kingdom&f_TPR=r1209600&f_WT=2&start=0"
      city: "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={q}&location={location_q}&f_TPR=r1209600&start=0"
      any_market: true
      max_searches: 10
    indeed:
      remote: "https://uk.indeed.com/jobs?q={q_plus}&l=United+Kingdom&fromage=14"
      remote_is_filtered: false
      max_searches: 4
    # employer_site:            # an employer's own vacancy page (no search): needs scrapers/<board>.js,
    #   fixed_label: all        # a normalize_<board>() and a scrape_sources entry (AGENTS.md section 6)
    #   fixed_urls:
    #     - "https://careers.example.com/vacancies"

scrape_sources:
  cv_library:
    enabled: false
    market: uk
    extractor: skills/job-ingest/scrapers/cv_library.js
    id_pattern: "/job/(\\d+)"
    salary: GBP per annum (or per day or hour), shown on the card
    pagination: numbered pages; the page state persists across page clicks

  reed:
    enabled: false
    market: uk
    method: browser_scrape
    extractor: skills/job-ingest/scrapers/reed_web.js
    id_pattern: "/jobs/.*?/(\\d{6,})"
    salary: GBP, on the card; the card also shows a remote badge ("Work from home" = remote, "Part Remote" = hybrid)
    note: Reed shows relative posted dates ("4 days ago"); reed_web.js converts them.

  linkedin:
    enabled: false
    market: uk          # default only: a LinkedIn card is assigned to the market its location names
    method: browser_scrape_guest_endpoint
    jd_url: "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<job_id>"
    extractor: skills/job-ingest/scrapers/linkedin.js
    id_pattern: "/jobs/view/(\\d+)"
    salary: rarely shown; most rows arrive salary_unknown and are kept for a manual check
    note: |
      Use ONLY the public guest endpoints above, at a slow pace, with few searches. Do not scrape
      the signed-in LinkedIn app: it renders only part of each list, blocks the extractor, and
      automated use can get the account restricted. The guest pages are server rendered and
      return the full advert. linkedin.js does not read the known-ids list; duplicates are
      removed at ingest instead.

  indeed:
    enabled: false
    market: uk
    extractor: skills/job-ingest/scrapers/indeed.js
    note: Read-only and low volume. The extractor accumulates cards in sessionStorage across pages and exposes them as window.__acc.

# Optional: employer career sites you check by hand (no extractor). Roles found there are added
# with `python3 skills/app-tracker/scripts/tracker.py add --title ... --company ... --url ...`.
career_sites: []
  # - {name: Example Employer, url: "https://careers.example.com"}

enrichment:
  when: every row at status found, before it is scored. The full advert is read first; a title is never scored.
  how: "save_description.py --id N --file jd.txt [--salary-min --salary-max --salary-period annual]"
  advert_formats: "an advert can arrive as page text, inside an applicant-tracking-system iframe from another domain, or as an image. If get_page_text returns only the site shell, open the iframe's src; if there is no iframe, take a screenshot and read the advert from it. Steps in skills/job-ingest/SKILL.md."

transfer:
  browser_output_char_cap: 1000                            # the JavaScript tool returns about this much
  retrieval_method: dump_cards_to_page_then_get_page_text  # reads a whole page in one call
```
