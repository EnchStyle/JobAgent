# application_rules.example.md : your standing rules for anything an employer sees

Copy this file to `config/application_rules.md` and replace the example values with your own.
The real file is ignored by git, so your contact details never leave your computer. Until it
exists, the scripts read this example and print a warning. The example belongs to the fictional
candidate used in examples/ (Jordan A. Bennett), so the sample data passes every check.

Read by cv-tailor, cover-letter, cv-verify and the apply step of job-pipeline. The master profile
(profile/master_profile.md) is the fact base, and its section 0 holds the CV output rules; this
file collects the rules you add on top of those, plus your standard answers for application
forms. When the two disagree, the newer dated instruction wins. Scripts read the yaml block at
the end, so edit values there.

## Contact details
- Email on every CV, cover letter and application form: the `contact.email` value below.
- One phone number per market (`contact.phones`, keyed by the market codes in
  config/filters.md). An application carries the number for its market; a number from another
  market is a fail. List only the markets you apply in.
- LinkedIn: the `contact.linkedin` value. No home address, date of birth or nationality line.

## Never mention
- Anything you do not want in an application, listed under `never_mention` below: for example a
  current employer you are not disclosing, a named manager, a confidential client.
  Something deliberately absent from the master profile is not a gap in the timeline.
- Co-author names inside a publication citation are the one exception, because removing them
  breaks the citation.
- "References available on request", author positions ("2nd author").
- Anything from the pipeline's own bookkeeping: scores, flags, gap lists, or remarks about what
  an advert does not say.

## Employer presentation (optional)
If one of your roles must be shown in a particular way (a trading name versus the legal entity,
a location it must never be paired with, a founder title that only fits founder-level postings),
describe it under `employer_rules` below. workflow_check.py fails a CV that breaks a
forbidden_lines pattern and asks for a judgement on founder titles.

## Dashes
No em dashes in anything written for an employer. Use commas, full stops, parentheses or "to".
The en dash that the CV builder puts in date ranges ("March 2020 – August 2021") is fine; do not
use dashes as punctuation in sentences.

## Cover letters and gaps
Mention a gap in a letter only when it helps the case: at most one sentence, tied to that
advert, framed around what you bring, and worded for that letter alone. The full gap list
belongs in the report to you, never in the letter.

## Application forms (your standard answers)
Form answers live in the `form_answers` block below. The assistant answers only from there: a
question with no configured answer is asked of you (or, in an unattended run, the role goes to
the hand-off sheet). It never picks a salary figure, a date or a yes or no on its own.
- Compulsory office days: answer according to your location rule in config/filters.md. If
  attendance is a condition of the job and it breaks that rule, drop the role and report it.
- An account, a portal sign-in or an emailed code: `on_account_wall` decides (drop the role, or
  put it on the hand-off sheet for you to finish). The assistant never creates accounts or types
  passwords or codes.
- Ask before submitting anything.

## CV attachment
- Always attach the tailored CV to every application, even when the form marks it optional.
- If an upload fails, retry until the file is confirmed attached before submitting.
- After applying through a board, restore `general_cv` as the board profile's default CV.

## Portfolio (optional)
If you have a portfolio or website, list it under `portfolio` with the kinds of roles each case
supports. A CV or letter includes the link only when one case fits the advert.

```yaml
candidate:
  name: Jordan A. Bennett        # printed at the top of cover letters
  file_stem: Jordan-Bennett      # file names: Jordan-Bennett-CV-<Brand>.pdf

contact:
  email: jordan.bennett@example.com
  phones:                        # one per market code in config/filters.md
    uk: "07700 900123"
  linkedin: linkedin.com/in/jordanbennett
  website: ""                    # optional; used in the letter header when there is no LinkedIn

# workflow_check.py reports every hit with its context (case-insensitive). A hit inside a
# publication citation (co-author name) is allowed; anything else is a fail.
never_mention:
  - Example Current Employer Ltd
  - References available on request

on_account_wall: handoff        # handoff (prepare everything, you finish) or drop
general_cv: ""                  # the CV to restore as default on board profiles after applying

# Standard answers. Leave a value empty if you want to be asked each time.
form_answers:
  salary_expectation: Negotiable
  salary_if_forced: {uk: ""}           # a figure per market code, or empty to be asked
  notice_period: ""                    # for example "4 weeks"
  available_from: ""                   # for example "within one month of an offer"
  right_to_work: {uk: ""}
  preferred_office: ""
  willing_to_relocate: ""
  criminal_convictions: ""
  armed_forces_or_reservist: ""
  conflict_of_interest: ""
  reasonable_adjustments: ""
  postal_address: ""                   # only for forms that require it; never on a CV
  references: "Available on request to the employer, not stated on the CV"

portfolio:
  url: ""
  cases: []          # for example [{name: "Launch case study", role_types: [product marketing]}]

# Optional. One entry per past employer with presentation rules; delete the block if unused.
employer_rules:
  - name: Northwind Software
    founder_titles_need_reason: ["Co-Founder", "Cofounder", "CEO", "Chief Executive"]
    forbidden_lines:
      - pattern: "Northwind Software\\s*,\\s*Manchester"
        message: "Northwind Software is never shown with Manchester"
```
