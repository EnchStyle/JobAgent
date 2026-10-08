---
name: cover-letter
description: Writes a cover letter for a JobAgent role when one will help (senior or leadership roles, applications that ask for one, or a fit the CV cannot explain alone), in the user's voice and only from their master profile, then de-slops it with avoid-ai-writing, checks it, registers it on the job and exports upload-ready PDF and Word files. Use for "write the cover letters", "add a letter for job N", or the cover-letter stage of the pipeline.
---

# cover-letter

A letter is worth writing only when it changes the outcome, and then it has to read as written by
the candidate for this employer. Run commands from the project root (see job-pipeline). This skill never
changes a job's status.

## Which jobs
Rows at `cv_generated` or `verified` whose cv_file is set, which have no cover_letter_file and
no "no cover letter needed" note (`python3 skills/app-tracker/scripts/tracker.py list --status
cv_generated --brief`, and the same for verified), plus any job the user names. A row at
cv_generated with no CV on file is a gap to report, not a reason to write a letter. Apply the
warrant test in references/warrant.md to each;
when it says no, record it with
`python3 skills/app-tracker/scripts/tracker.py note --id N --text "no cover letter needed: <why>"`
(so later runs skip it), report it, and create nothing else.

## Writing
Sources: profile/master_profile.md for every claim, the stored advert
(`tracker.py show --id N`) for what the employer wants, config/application_rules.md for what
never appears (the never_mention list, pipeline notes) and how gaps are handled.
references/warrant.md has the structure and the user's voice. If application_rules lists a
portfolio, reference the one case that fits this advert, or none; the master profile's
evidence bank, if present, supplies the stories.

Write each letter fresh from its own advert. Do not open earlier letters in output/cover_letters
to borrow their sentences or paragraph plan: letters built from one template repeat the same
phrases, and an agency that receives two of them will notice. Vary
the opening and the close with the employer, and keep anything from the pipeline's own
bookkeeping (scores, flags, what the advert does not say) out of the letter.

Gaps: mention one only when it helps the case, in at most one sentence tied to this advert and
framed around what the user brings. Everything else belongs in your report to the user.

Then:
1. Path: `python3 skills/cover-letter/scripts/register_cover.py --id N --print-name` prints the
   absolute path to use; write the
   letter there as plain text: each paragraph on a single line with a blank line between
   paragraphs (the export turns a line break inside a paragraph into a forced break), the
   salutation first, and "Kind regards," with the candidate's name on the next line as the last block. No
   markdown and no contact block; the export adds the header. For a role whose CV is not in English, write the
   letter in the CV's language: draft and check it in English, then translate it faithfully.
2. De-slop with the avoid-ai-writing skill in rewrite mode if it is installed (otherwise edit by
   hand for plain, specific sentences), keeping the candidate's voice. Its advice on
   spaced en dashes does not apply here: no dashes at all in letters.
3. Check:
   - `python3 skills/cv-verify/scripts/workflow_check.py <letter.md> --kind letter --market <market>`
     shows no FAIL;
   - `python3 skills/uk-cv-writer/scripts/check_grounding.py <letter.md> profile/master_profile.md`
     flags no number that is not in the profile. Figures quoted from the advert itself, such as
     the employer's headcount, show up as unsupported and are fine.
4. Register: `python3 skills/cover-letter/scripts/register_cover.py --id N --file <path>`.
5. Export: `python3 skills/cover-letter/scripts/export_cover_files.py --md <path>
   --out-base <Name>-CoverLetter-<Brand> --market <market>` writes A4 PDF and DOCX files
   with the user's contact header (email and the market's phone from config/application_rules.md).
   For <Brand> use the employer's short name, normally the CV's brand (shortened if that carries
   a tagline, "Acme" rather than "AcmeAnalyticsPlatform"), and add `--role-slug <Word>` when the
   employer has more than one letter.

## Report to the user
Per job: letter written or not needed (with the reason), the PDF name, the word count, and the
one or two points each letter leads with. No full letter text unless the user asks.
