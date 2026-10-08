# tailoring.md : project conventions for cv-tailor

How to write and verify a CV is uk-cv-writer's job (skills/uk-cv-writer). This file holds what
that skill cannot know: how the user's roles are presented, which language to write in, and where
files go. Facts always come from profile/master_profile.md; standing rules from
config/application_rules.md.

## How your roles are presented
- Titles, employer names and locations come from profile/master_profile.md. If you have standing
  rules for how one of your roles must appear (for example a trading name versus the legal
  entity, or a title that only fits founder-level postings), write them in
  config/application_rules.md under `employer_rules`; workflow_check.py enforces them and the
  report says which presentation was used and why.
- Following those rules is the user's own presentation, not a relabel of a title.
- Dates: Month YYYY for every role, in reverse chronology; two current roles go by start date.
  Put start and end in their own fields and let the builder format the range. Education may use
  years only. A very short role may be shown or left out; leaving it out opens no gap if the
  profile says so.
- Filling two pages: give the other roles, education and any publications their due before
  adding bullets to one role; eight bullets is a sensible ceiling for any single role.

## Language
General rule for any market: write the CV in the advert's language, unless the employer clearly
works in English (an international company advertising in English, or an advert that asks for an
English CV). The master profile is in English, so any other language uses the two-pass method
below: ground the content in English first, then translate it faithfully. If unsure, use the
advert's language and say so in the report, so the user can switch it.

## Non-English CVs: two passes, so the grounding check still works
check_grounding.py compares the CV with the English master profile, so it cannot judge text in
another language directly.
1. Write the content in English as `output/_contentjson/<id>en.json`, build a draft
   (`output/_contentjson/<id>en_draft.docx`) and run check_grounding.py until no unsupported
   number or claim remains. This is where invention is caught.
2. Translate that content faithfully into `output/_contentjson/<id>.json`, adding nothing. Set
   `config.labels` to the standard section headings in that language, write dates the way that
   market writes them, and keep one fixed rendering per job title, reused across CVs.
3. Build the final file and run check_cv.py with a keywords.json in the advert's language. Where
   word endings change, use word stems of five or more letters; the checker matches them as word
   starts. The British-spelling check does not apply.
4. If you add content later (for example to fill page 2), add it to the English file first and
   re-run grounding, so the translation still adds nothing.
5. The grounding script can misread other number formats (a decimal comma, a space as the
   thousands separator), so check the numbers in the translated file against the English pass
   by hand.
Contact line: the phone for that market (contact.phones.<code>) and the email from
config/application_rules.md.

## Files
- CV: `output/cvs/<Name>-CV-<Brand>[-<Slug>]-<jobid>.docx`, exactly as cv_name.py
  prints it; register that same project-relative path.
- PDF twin: export_pdf.py writes `<Name>-CV-<Brand>[-<Slug>].pdf` (job id dropped) next
  to it. Only cv_name.py takes the role slug; export_pdf.py picks it up from the .docx name.
- A slug is needed when the brand already has CVs on file (cv_name.py lists them), for example
  three roles at one employer: -RoleA, -RoleB, -RoleC. Choose a word not
  already used.
- Content model and keywords: `output/_contentjson/<id>.json`, `<id>_keywords.json`.

## What not to do on a CV
- No second "de-slop" pass (avoid-ai-writing) on a CV: uk-cv-writer already writes plainly, and a
  generic pass strips the advert's keywords that ATS scoring needs. De-slopping is for letters.
- No reuse of an old CV as a shortcut: every CV is written fresh for its advert.
