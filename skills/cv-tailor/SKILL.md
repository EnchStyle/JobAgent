---
name: cv-tailor
description: Writes a tailored, ATS-safe CV for each JobAgent role that is ready for one (or that the user names), by running the uk-cv-writer skill vendored in the project folder against the stored advert and their master profile, applying their standing application rules, then registering the CV in jobs.db and exporting the send-ready PDF. Use for "make the CVs", "write the CV for job N", "tailor my CV to this role", or the CV stage of the pipeline.
---

# cv-tailor

One CV per job, written fresh from the master profile and that job's advert. How a CV is written
and checked belongs to uk-cv-writer; this skill picks the jobs, supplies the user's project rules,
and files the result. Run commands from the project root (see job-pipeline).

## Which jobs
- `python3 skills/cv-tailor/scripts/eligible.py` lists the rows ready for a CV (scored 60 or
  more, not on hold) with has_jd. Nothing listed means nothing to do.
- A job the user names explicitly gets a CV whatever its band; record that the user asked with
  `python3 skills/app-tracker/scripts/tracker.py note --id N --text "CV requested by the user"`
  (the date is added for you).
- A passed closing date stops the CV even for a named job: tell the user the date and write it only
  if the user says the role is still open. In a pipeline run, mark it
  `save_score.py ... --reject-reason expired` and move on.
- Before writing, look for an earlier application to the same employer or agency
  (`tracker.py find "<employer>"`). If the tracker shows an application to what looks like the
  same role, ask the user before writing (in a pipeline run, skip it and list it under "Needs you"):
  a second CV for the same job to the same recruiter looks careless. A weaker link, such as the
  same agency for a different role, is a line in the report, not a reason to stop.

## Writing the CV
Use the copy of uk-cv-writer in this project, `skills/uk-cv-writer/`: read its SKILL.md and the
reference files it points to at each step, and run its scripts from there. Do not use the
separately installed uk-cv-writer skill for pipeline CVs; the bundled copy carries fixes the pipeline
relies on (accented capitalisation, whole-word keyword matching).

Give it:
- the facts: profile/master_profile.md (section 0 holds the user's CV output rules);
- the advert: `python3 skills/app-tracker/scripts/tracker.py show --id N`, field description;
- The user's project rules from config/application_rules.md: contact details (email, the phone for
  the role's market), what never appears (the never_mention list), the employer_rules for how past
  employers are shown, and no em dashes. These are the user's own instructions about how their
  roles are presented, so following them is not relabelling a title.

In a pipeline run nobody is there to answer uk-cv-writer's gap questions: take its no-questions
path (answer from the profile only, leave real gaps as gaps) and put the questions in your report.
When the user is working through a single CV with you, its one batched round of questions is fine.

Language: the advert's language decides, unless the employer clearly works in English
(references/tailoring.md has the rule). Any non-English CV is
grounded in English first and then translated.
references/tailoring.md has the language rule, the two-pass method, how roles are presented,
and the file conventions.

## Files and checks
1. Name: `python3 skills/cv-tailor/scripts/cv_name.py --job-id N`. If the brand comes out long
   or odd (a tagline or "via agency" in the company field), rerun with `--company "<short name>"`.
   If it reports other CVs for the same brand, add `--role-slug <Word>` so the PDFs stay
   distinct. Write the CV to the absolute path it prints (suggested_cv_file, inside the data
   folder) and use that path in every later command; register_cv.py stores it relative.
2. Keep the content model at `output/_contentjson/<id>.json` and the keywords at
   `output/_contentjson/<id>_keywords.json` (a non-English CV: also `<id>en.json` for the English pass).
3. Build with `skills/uk-cv-writer/scripts/build_cv.py`, then check, fix and rebuild until clean:
   - `check_cv.py <docx> <keywords.json>` shows no FAIL;
   - `check_grounding.py <docx> profile/master_profile.md` shows no unsupported numbers, and every
     REVIEW line is a fair restatement of the profile (it over-flags by design; fix what is not).
     For a non-English CV, judge the wording on the English draft and only the numbers on the
     translated file;
   - `python3 skills/cv-verify/scripts/workflow_check.py <docx> --market <market>` shows no FAIL, and
     each CHECK item is right for this role.
4. Register: `python3 skills/cv-tailor/scripts/register_cv.py --id N --cv-file <path>`
   (status becomes cv_generated).
5. PDF: `python3 skills/cv-tailor/scripts/export_pdf.py --docx <path>` writes
   `<Name>-CV-<Brand>[-<Slug>].pdf` beside it. The PDF is what goes to direct employers
   and to markets where a Word file is unusual (for example much of continental Europe); the .docx is for
   agencies and Word-only forms.

cv-verify reviews the CV next and moves it to verified. Cover letters are a separate stage.

## Report to the user
Per job: the PDF name, pages, Tier 1 keyword coverage, any employer rule applied, and the
honest gaps (requirements the profile does not evidence). Then any questions whose answers
would strengthen the CV. Keep it short.
