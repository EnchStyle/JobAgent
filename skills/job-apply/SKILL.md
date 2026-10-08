---
name: job-apply
description: Applies to verified JobAgent roles the user has approved, through Claude in Chrome, one role at a time: checks for a repeat application and an account wall, attaches the tailored CV and confirms it is attached, answers forms only from config/application_rules.md, submits with the user's go-ahead (per role, or one approval for a listed batch), and records what was sent and how it was confirmed. Portals already signed in in the browser are used; roles that need a new account, a password, a one-time code or a CAPTCHA go to a hand-off sheet for the user. Use for "apply to roles 12 and 15", "send the verified applications", or the apply step of job-pipeline.
---

# job-apply

Applying is where most things go wrong (forms that drop answers, uploads that silently fail,
portals that demand an account), so it runs one role at a time with checks at each step.
references/portals.md lists what is known about each kind of application site; read the entry
for the site before you start. Run commands from the project root (see job-pipeline).

## Rules that are never relaxed
- Apply only to roles the user named or approved in this conversation, and only at `verified`.
  A role still at `cv_generated` goes through cv-verify first, run by a separate agent that did
  not write the CV; tracker.py refuses `applied` from any other status unless
  `--unverified-reason` records the user's explicit approval.
- Use the sessions already signed in in the user's browser (boards, LinkedIn, ATS portals): if a
  portal opens signed in, carry on. Claude does not type passwords or one-time codes, create
  accounts or answer CAPTCHAs; a role that needs one of those goes to the hand-off sheet, and
  signing in once to that portal in Chrome usually clears it for every later application there.
  Scripted help: when the normal click-and-type route fails, use page
  scripts to get the job done: attach the approved CV or letter (temporary file input plus
  DataTransfer, or capturing the site's own file input), set a configured answer, tick a box the
  rules allow, open a collapsed or shadow-DOM control. Same answers and consents as by hand; check
  on screen afterwards that every value and file shows, and note each use in the tracker and the
  report. Limits that stay: no CAPTCHA, reCAPTCHA or other bot-detection bypass; never fill a
  hidden honeypot field (an input a person cannot see is a bot trap and gets the application
  binned); never force past a validation error by script, fix the value so the form accepts it.
- Never invent an answer. A question whose answer is not in config/application_rules.md
  (form_answers) is asked of the user; in an unattended run the role goes to the hand-off sheet.
- The final submit click needs the user's go-ahead for that role: either for the role on its own,
  or as part of a batch the user approved in one message (see "Batch approval").

## Per role
1. **Repeat check.** `python3 skills/app-tracker/scripts/tracker.py applied-to "<employer>"`.
   Applying to an employer again, even for a similar role, is fine and never stops a role. Two things still matter: the same advert already applied to (also via
   another board or agency) is a duplicate, so skip it; and mention the earlier application in
   the batch list so the new application is worded for the new role.
2. **Still open?** Check the closing date (jobs.closing_date or the advert) and that the advert
   is still online. A closed role (never applied): `tracker.py set-status --id N --status rejected --note "expired: <what the page says> (checked <date>)"`. LinkedIn: fetch `/jobs-guest/jobs/api/jobPosting/<id>` and look for "No longer accepting applications"; Reed: use `/jobs/job/<id>`, never `/jobs/<id>`.
3. **Route check, before any typing.** Open the Apply link and find out what the route needs:
   - an account, sign-in or emailed code: stop; `on_account_wall` in application_rules decides
     between dropping the role and adding it to the hand-off sheet (`tracker.py mark-blocked`);
   - a route that cannot take your own file (for example a one-click apply that only offers
     files stored on the board profile): do not let a generic CV go out unnoticed; ask the user
     to upload the tailored CV to that profile first, or hand the role off.
4. **Attach.** Upload the verified CV (the PDF for direct employers, the .docx where a form or an
   agency asks for Word) and the letter if one exists. Read the page back and confirm the file
   name is shown as attached; if not, retry, and if it still fails, hand the role off. A form
   that marks the CV optional still gets it.
5. **Answer.** Fill answers from config/application_rules.md (form_answers). After filling,
   read the form back: some sites silently leave fields empty, so check every required field
   before moving on.
6. **Go-ahead.** Submit if the role is on a batch the user approved and the form matches what was
   shown (same files, answers from the approved list). Otherwise show the user the role, the
   files attached and every answer given, and wait for a clear yes before the final click.
7. **Record.** `tracker.py set-status --id N --status applied --note "<route>" --cv-sent <file>
   --confirmation page|email|board|none`. If the site showed no confirmation, say so.

## Batch approval
To apply to many roles without a question per role: list them in one message (id, role,
employer, CV and letter file, and the form answers that will be used from application_rules)
and ask for one yes. A yes covers exactly the roles listed. For each of them, submit without
asking again unless the form asks something new or needs an answer, a file or a route that was
not shown: that role then stops for the user's answer and the rest carry on.
Order the list by closing date (soonest first, any role closing within 3 days at the top), then by
score (highest first), and apply in that order.

## After a session
- Board profiles: uploading a CV through some boards replaces the profile's default CV. Restore
  the general CV named in application_rules (general_cv) on every board you used.
- Hand-off sheet: `python3 skills/app-tracker/scripts/tracker.py handoff` writes
  output/handoff_<date>.md with each blocked role's link, files, closing date and reason.
- Run `python3 skills/job-pipeline/scripts/pipeline_status.py --log "<summary>"`.

## Report to the user
A table: id, role, employer, outcome (applied, handed off, closed, skipped), CV sent,
confirmation. Then the hand-off sheet path and any answers the user should check.
