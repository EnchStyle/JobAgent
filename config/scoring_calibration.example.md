# scoring_calibration.example.md : calibration for job-match-score

Copy this file to `config/scoring_calibration.md` (ignored by git) and replace the examples with
two or three from your own scored roles. Your own examples describe your career, so they stay
out of version control.

Open this when you want to check that your numbers sit where the scale expects. The examples use
the fictional sample candidate in examples/ (Jordan A. Bennett: nine years in B2B SaaS and
fintech product marketing, go-to-market, positioning and demand generation; not a data
scientist or engineer). Replace them with two or three examples from your own profile once you
have scored a few roles.

## The scale
- 80 to 100, strong: the core of the role is squarely in the candidate's proven record; minor gaps only.
- 60 to 79, worth applying: a defensible fit with real but bridgeable gaps. Gets a CV.
- 50 to 59, review: borderline. Kept at scored for the user to decide; no automatic CV. The band
  means borderline roles are not lost at a hard cut-off.
- 0 to 49, skip: a must-have the profile plainly does not support, or only peripheral overlap.

Salary is never scored (it is a hard filter at ingest). Location, sales and expiry decide the
status but not the fit number, which is recorded for the history either way.

## Keeping scores stable
- Same yardstick every run: the current master profile. If it has not changed, the same advert
  should land within a few points of its earlier score.
- Map first, then score. The number follows the mapping; it should not lead it.
- Use the whole scale, but do not split hairs. Roughly strong, roughly worth applying,
  borderline or skip is the decision; the unit does not need defending.
- Optional extra signal: separate skills and experience scores, nothing finer.

## Example 1: strong match (80s)
Advert: Head of Product Marketing, B2B SaaS, London hybrid. Owns positioning and launches,
builds an account-based marketing programme, works with sales on enablement, reports pipeline.
Mapping: led go-to-market for 3 launches (GBP 4.2M first-year ARR); rebuilt the ABM programme
across 6 EMEA markets (+38% qualified pipeline); built the enablement library (19% shorter sales
cycle). Gaps: no formal people-management line in the profile; budget size not stated.
Score 84. Rationale: "Met: launches, ABM, enablement and pipeline reporting, all quantified.
Gaps: team management and budget ownership not evidenced."

## Example 2: clear skip (teens)
Advert: Senior Data Scientist. Builds and deploys production machine-learning models, Python
and statistics at depth, experimentation platform ownership.
Mapping: the profile shows SQL, Tableau and A/B testing as a marketer, not model building or
production code. The central must-have is absent; marketing analytics does not substitute.
Score 15, rejected. Gaps: production ML; Python at depth; statistical modelling.

## Example 3: good fit, wrong place
Advert: Product Marketing Manager, "office base Birmingham, three days a week".
Mapping: positioning and launch work is evidenced; fit about 70, but a fixed hybrid pattern in a
place not on location_allow fails the location rule:
`--reject-reason location --reason "hybrid, office base Birmingham"`.

## Example 4: sales in disguise
Advert: Business Development Manager. "Oversee the complete sales lifecycle", "generate a
pipeline", "predictable bookings". Whatever the title, the output is selling:
`--reject-reason sales`. Contrast a Head of Strategic Partnerships whose remit is partner strategy
with some new-business development and no quota: score it on fit and `--hold` it for the user.
