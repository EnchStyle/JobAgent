---
name: job-match-score
description: Scores the user's found jobs in jobs.db for fit against their master profile, from the stored advert, on skills and experience only. Records a 0 to 100 score with the requirement mapping and gaps, and sets each row to scored (apply or review band), held for the user, or rejected (low fit, location, sales, expired, duplicate). Use after adverts are read, or whenever asked to score, rank, triage or judge roles in the tracker.
---

# job-match-score

Turn each stored advert into one honest, explainable fit score, so CVs are only written for
roles worth the user's time. Run commands from the project root (see job-pipeline).

## Inputs
- `python3 skills/job-match-score/scripts/list_unscored.py` : the `found` rows, each with
  has_jd (1 = advert stored) and date_posted. Rows with has_jd 0 are not scored: leave them at
  `found` and list them as "advert not read yet" (job-ingest reads them).
- The advert: `python3 skills/app-tracker/scripts/tracker.py show --id N` (field description).
- profile/master_profile.md : the only evidence you may credit. Read it once per run.
- config/scoring_rubric.md : threshold (60), review floor (50), the location and sales rules.
  config/scoring_calibration.md (or its .example.md until you create it) has calibration
  examples if you want them.

## How to judge a row
Work through these in order; the first that applies decides the outcome, and the fit score is
recorded either way so the history stays useful.
1. **Expired or duplicate.** The advert's closing date has passed, or it says applications are
   closed: reject with `--reject-reason expired`, since no CV should be spent on it. The same
   role is already tracked (same employer and title, often through another board or agency):
   `--reject-reason duplicate --reason "same role as <id>"`. An advert over about four weeks old
   with no closing date may have closed too: score it, and mention its age in the report.
2. **Location.** Onsite or hybrid is fine only in the places listed under `location_allow` in
   config/filters.md; anywhere else the role must be fully remote. A fixed weekly office pattern
   elsewhere (for example two days a week in Birmingham, when Birmingham is not listed) is a
   location reject, however good the fit. Occasional visits (team days, client
   travel) still count as remote; mention them in the rationale. If the advert does not state
   the working pattern for a role outside those places, score it normally and, unless
   it is rejected on other grounds, add `--note "confirm working pattern"` rather than rejecting
   on a guess.
3. **Salary.** Ingest only sees the pay on the listing card, and many cards show none. If the
   advert states pay whose top is below the floor for its market in config/filters.md (`markets`,
   per year or per month as set there; a day rate is compared on about 220 working days; an onsite or
   hybrid role in a place with an `office_floor` under `location_allow`, such as London, uses that higher
   floor instead, a remote role keeps the market floor), reject
   with `--reject-reason other --reason "pay <range>, below the floor"` and store the figures
   (`save_description.py --salary-min --salary-max --salary-period`). Pay not stated is fine.
4. **Sales.** Sales roles are rejected by default (config/scoring_rubric.md; delete that rule if
   you want them): quota or revenue targets, commission or OTE,
   prospecting, booking demos, owning a sales pipeline, pre-sales support, or a "first commercial
   hire" whose job is to sell. A disguised title is still sales. Reject with
   `--reject-reason sales`. A partnerships, alliances or fundraising role that includes some
   new-business work is not automatically sales: keep its score and use `--hold "<why>"` so
   the user decides before a CV is written.
5. **Fit.** Map the advert's requirements, one by one, to evidence in the master profile. Credit
   only what the profile states; a requirement it does not evidence is a gap, however plausible.
   Write the mapping first, then pick the number, anchoring to the bands:
   80 to 100 the core of the role is squarely in the candidate's track record; 60 to 79 a solid fit with
   bridgeable gaps; 50 to 59 borderline, the user decides; below 50 skip. An advert that explicitly
   excludes the candidate's background scores low whatever the title says.

One careful reading per advert; there is no second reading. A second reading was found to
cost a full extra read for little gain, and a borderline miss is not lost: roles at 50 to 59 go
to the user's review list. The same role found on two boards gets one reconciled
score (ingest flags these as possible_duplicate_of). Every scored row keeps its stored advert;
do not use --allow-no-jd in bulk.

A role is never capped or skipped because AI is not its core, its title lacks a keyword, or a
keyword screen ranked it low: score the fit the advert describes.

## Recording
One row:
```bash
python3 skills/job-match-score/scripts/save_score.py --id N --score 64 \
  --rationale "Met: ... Gaps: ..." --gaps '["...", "..."]' \
  [--reject-reason location|sales|expired|duplicate|other --reason "hybrid, Birmingham"] \
  [--hold "partnerships role with some new-business work"] [--note "confirm working pattern"]
```
A batch (quicker for more than a handful): write the records to a scratch JSON file and run
`python3 skills/job-match-score/scripts/persist_enriched.py <file>` (record format in the script
header). Either way the status follows from the score and flags: 60+ scored (band apply),
50 to 59 scored (band review), below 50 rejected, `--reject-reason` rejected, `--hold` scored but
skipped by cv-tailor. Notes are appended, never overwritten. The script refuses a row with no
stored advert.

Keep the rationale to two or three lines in the form "Met: ... Gaps: ...", naming the profile
evidence (for example "led go-to-market for 3 launches, GBP 4.2M first-year ARR"); the gaps list
carries the detail. No em dashes.

To change the outcome of a row that is already scored (the user decides on a hold, or a
review-band advert turns out to have closed or to be a duplicate), run save_score.py again with
its stored score, rationale and gaps plus the new flag (`--reject-reason ...`, or nothing to
release a hold); the band and status follow, and a note records the change.

## Report to the user
A table sorted by score: id, role, employer, score, outcome, one-line reason. Then a short
"Needs you" list: review-band rows, holds, working patterns to confirm, adverts not yet read.
