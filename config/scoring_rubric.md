# scoring_rubric.md : how the fit score works

Fit only: skills and experience, judged holistically against the master profile. Salary and
location are NOT scored; they are hard filters in filters.md and are applied upstream, so a role
only reaches the scorer once it has already passed salary, location, and freshness.

The scorer reads the master profile and the job description and returns one fit score from 0 to
100, a short rationale (two or three lines), and the specific gaps (must-have JD requirements the
profile does not evidence). For stability run to run: reason before scoring, keep temperature
low, and score against the same master profile every time, using the fixed band anchors below.

Code reads only `threshold_apply` and `review_floor` from the block below; the other keys and
the prose guide the assistant when it scores.

Optional if you ever want more signal: also report a separate skills score and an experience
score. Nothing finer than those two.

```yaml
approach: holistic
scale: 0-100
threshold_apply: 60          # roles at or above this get a CV automatically
review_floor: 50             # 50 to 59 = REVIEW band: kept as 'scored' for a human decision, NOT auto-rejected
bands:
  strong: [80, 100]
  worth_applying: [60, 79]
  review: [50, 59]           # surfaced for human review; not auto-CV'd, not rejected
  skip: [0, 49]
consistency:
  reason_before_scoring: true
  low_temperature: true
  same_profile_every_run: true
output_fields:
  - fit_score
  - rationale                # 2 to 3 lines
  - gaps                     # must-have JD requirements the profile does not evidence
optional_split:
  - skills_score
  - experience_score
stored_in: jobs.score_breakdown
```

## The review band (50 to 59): surface, do not silently reject
A role scoring 50 to 59 is a borderline fit: not an automatic apply, but not a clear miss either.
These are kept at status `scored` (so they show in the shortlist) with `band: review` in the
score_breakdown, and are NOT auto-rejected and NOT auto-given a CV. The human scans them and
decides which to pursue; on request cv-tailor builds a CV for the chosen ones. Only scores BELOW
the review floor (under 50) are rejected. The band means borderline roles are not lost at a
hard cut-off.

Note on truthfulness: the scorer judges the profile as written. It must not credit the profile
for anything not stated in it. Fabrication is caught later by cv-verify, but the scorer should
already treat unevidenced JD requirements as gaps, not as met.

## The score MUST come from the job description, not the title (hard rule)

A title is not enough and is often misleading: two adverts with the same title can ask for
entirely different backgrounds, and some explicitly exclude the candidate's. So:

- Read the actual job ad (the full description) before assigning any score. The title is used
  only for the cheap reject-title drop, never for a trusted score.
- Cross-reference the ad's stated requirements against specific evidence in master_profile.md.
- The breakdown must list the job's key requirements and mark each as met (naming the profile
  evidence) or a gap. A bare number with no requirement mapping is not acceptable.
- If the ad explicitly excludes the candidate's background (for example "not suited to candidates from a
  software background"), score it low regardless of the title.

Practically this means: enrich first (fetch the description), then score. Do not present
title-only scores as if they were real; they are a triage signal at best.

## Location is a hard gate (config/filters.md, location_allow)
Onsite or hybrid is acceptable only in the places listed under location_allow in
config/filters.md. A role that the JD confirms is onsite or hybrid anywhere else is a location
reject regardless of the fit score. Keep the fit score in the breakdown for the record, but the
row is rejected on location.

## Sales roles are a hard reject (default; delete this section if you want sales roles)
After reading the JD, reject the role regardless of fit score when its core output is selling:
revenue or quota targets, commission or OTE, outbound prospecting, booking demos, owning a sales
pipeline and closing deals, pre-sales support to a sales team, or a "first commercial hire" whose
job is to sell the product. A title that hides this (for example "Consultative Business
Developer", "Pre-Sales Consultant", "Account Manager" with new-business targets) is still a sales
role. Record `band: sales_reject` and the reason in the breakdown, set the row to rejected, and
never generate a CV for it. Partnership, alliances and fundraising roles are not sales by
default, but flag any with revenue targets or co-selling duties for the user instead of applying.
