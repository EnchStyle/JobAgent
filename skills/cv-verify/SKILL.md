---
name: cv-verify
description: Independent QA of every CV waiting at cv_generated in the JobAgent tracker before it is used. Runs uk-cv-writer's own checks (structure, pages, keywords, grounding in the master profile), then the user's workflow rules (contact details, names that must never appear, employer presentation rules, dashes) and a fresh fit re-score, and records pass (verified) or fail with specific fixes. Use to verify, QA, check, approve or sanity-check CVs, or as the verify stage of the pipeline.
---

# cv-verify

A second pair of eyes that did not write the CV. Re-derive the verdict from the sources (the
stored advert and profile/master_profile.md) and the checks below; do not take the drafter's
report on trust, and do not edit the CV yourself: a failed CV goes back to cv-tailor with notes
precise enough to act on. Run commands from the project root (see job-pipeline).

## What to verify
`python3 skills/app-tracker/scripts/tracker.py list --status cv_generated --brief` gives the rows
and their cv_file. The advert is in `tracker.py show --id N` (field description). Work out the
market (a code from config/filters.md, such as uk or ie) from the source and location
(`python3 -c "from lib import markets; print(markets.market_for('<source>', '<location>'))"`).

## Gate A: uk-cv-writer's checks (skills/uk-cv-writer/scripts)
1. Write a keywords file for the advert's must-haves in its own phrasing, as
   `{"tier1": [...], "tier2": [...]}`, in a scratch folder outside the project (for example
   /tmp/kw_<id>.json). One Tier 1 term per must-have requirement; for "X or Y" use the option the
   profile supports; put the items of a long list in Tier 2. Avoid bare two-letter terms.
2. `python3 skills/uk-cv-writer/scripts/check_cv.py <cv_file> /tmp/kw_<id>.json`: any FAIL fails
   the CV (structure, headings, page count and balance, widow lines, timeline, personal data,
   interests section, Tier 1 coverage under 75%). Review each WARN.
3. `python3 skills/uk-cv-writer/scripts/check_grounding.py <cv_file> profile/master_profile.md`:
   an unsupported number is a fabricated metric and fails the CV. Read each flagged line: a fair
   restatement of the profile is fine; a claim the profile does not make (a role, a duty, a
   result) fails it. For a non-English CV, whose words cannot match the English profile, judge
   the numbers on the translated file and ground the wording against its English source
   (output/_contentjson/<id>en.json or <id>en_draft.docx); if that is missing, say so.

## Gate B: the user's workflow rules
`python3 skills/cv-verify/scripts/workflow_check.py <cv_file> --market <market>`
- FAIL items fail the CV: an em dash; a term from the never_mention list in
  config/application_rules.md (for example a past employer left out on purpose, named people,
  "References available on request"); a contact email other than the configured one or a phone
  from the wrong market; a line that breaks one of the employer_rules.
- CHECK items need your judgement:
  - a founder or CEO title next to an employer in employer_rules passes only for a founder or
    C-level posting;
  - a listed name inside a publication citation is fine as a co-author.
- WARN items are notes for the report, not fails, such as a dash used as punctuation.

- Portfolio (if application_rules lists one): the website link in the CV header is always fine.
  A letter that cites a case where the advert gives no reason for it is a CHECK, and so is one
  that omits the case where one clearly fits the advert. Follow the lead-case mapping and the
  wording rules in application_rules (for example, a case is never called a "client project").

references/checks.md has worked examples of these judgement calls, and application_rules may
add the user's own.

## Re-score
Score the CV against the advert from scratch, 0 to 100, the way job-match-score does, counting
only what the profile supports. Close to the stored match_score is normal. A drop of more than
about ten points means the CV buried the relevant evidence: name what to bring forward. That is
a fail only when the core evidence for the role is missing from the CV.

## Record the verdict
- Pass (Gate A clean, no Gate B FAIL, every CHECK judged fine):
  `python3 skills/cv-verify/scripts/record_verdict.py --id N --result pass --rescore <n>`
  (status verified; the re-score is stored in jobs.rescore and match_score keeps the original;
  a re-score below the apply threshold sends the row back to the review band for the user).
- Fail: `python3 skills/cv-verify/scripts/record_verdict.py --id N --result fail --notes "<fixes>"`
  (status stays cv_generated). List every problem found in one go, each with where it is and
  what to change, so cv-tailor can fix everything in a single pass, and put the re-score at the
  start of the notes.
Whether the user should apply at all (office days, a possible repeat application) is not this
skill's verdict: pass or fail the CV, and raise those points in the report.
Keep the scratch keyword files outside the project; the folder cannot delete files.

## Report to the user
A table: id, role, verdict, Gate A (pages, Tier 1 coverage, grounding), Gate B findings,
re-score against stored score. Then the fixes for any failed CV, one line each.
