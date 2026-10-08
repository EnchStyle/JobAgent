# Getting started with JobAgent

This guide is for the person who will use JobAgent for their own job search. You do not need to
be a programmer: an AI assistant does the technical work, and you make the decisions. Plan on
about two hours for the first setup, most of it spent on your master profile.
docs/FILE_STRUCTURE.md explains every file in the folder.

## What JobAgent will and will not do
| It will | It will not |
|---|---|
| Search the job boards you choose, at a gentle pace | Apply anywhere without your go-ahead for each application |
| Read every advert and score it against your profile | Create accounts, enter passwords or solve CAPTCHAs |
| Write a tailored CV and, where useful, a cover letter | Invent experience, numbers or skills you have not written down |
| Check each document before you see it | Guarantee that a board allows automated reading; that is your responsibility |
| Keep a tracker of every role and its status | Send your data anywhere except the boards you search |

## What you need
- The Claude desktop app with Cowork, and the Claude in Chrome extension, signed in to the job
  boards you want to search.
- LibreOffice (free), for PDF export, and poppler-utils for the CV checks.
- The Python packages in requirements.txt. In Cowork these run in the Cowork shell and are
  usually present already; the assistant checks.
- Optional: a Gmail connector, if you want application confirmations matched to the tracker.

## Try it first (5 minutes, no personal data)
The examples/ folder holds a fictional candidate, Jordan A. Bennett, with a profile, an advert
and some scraped job cards. Ask the assistant: "Run bash examples/dry_run.sh and explain the
output." The script runs every stage on the sample data in a throwaway folder with the shipped
example settings (it never reads your own settings or touches your own tracker, and it only ever
clears a folder it created itself) and prints what to expect at each step:
1. the tracker is created;
2. 6 sample cards are ingested: 4 kept, 2 rejected (one on title, one below the salary floor),
   and a remote role in Berlin is kept but flagged for a right-to-work check;
3. the Acme Analytics advert is stored, scored 84 and given a CV file name;
4. the sample CV is built and checked: no check fails; the grounding check finds nothing
   invented, and the CV check only warns that this short sample fills one page;
5. the CV is registered, exported to PDF and verified, and the overview workbook is written.

## Setup, step by step
1. Download this repository and put the folder somewhere permanent on your computer.
2. Open Claude Cowork, connect the folder, and say: "Read AGENTS.md and help me set up JobAgent."
   The assistant guides you through the steps below.
3. Your details: config/application_rules.md (from the example). Your name, email, one phone
   number per country you apply in, LinkedIn, anything that must never appear in an application
   (for example a current employer), and your standard answers to application forms.
4. Your master profile: copy skills/uk-cv-writer/assets/master-profile-template.md to
   profile/master_profile.md and fill it in. This is the most important step. Write your
   full career record: every role with six to ten bullets, real numbers wherever you have them,
   education, skills and languages. Longer is better; each CV picks from it. Nothing that is not
   in this file will ever be claimed on your behalf. examples/master_profile.sample.md shows
   the format.
5. Your filters: config/filters.md (from the example). The countries you search, your minimum
   salary in each, the places where you would work in an office (anywhere else must be remote),
   how fresh adverts must be, and the few job titles you never want to see.
6. Your searches: config/sources.md (from the example). Job families (a few keywords each),
   which are searched every run ("standing") and which only when you ask, the places each family
   covers, and which boards. Every board starts switched off; switch on only those that cover
   your country.
7. Your scoring: decide whether sales roles stay excluded (config/scoring_rubric.md), and write
   config/scoring_calibration.md from its example with two or three scored roles of your own
   (the assistant can draft them from your profile; the file stays out of git).
8. A first test: one board, one search. Look at what was kept and rejected, and adjust the
   filters before running everything.

## Using it day to day
- "Run the job pipeline": searches, reads, scores, writes and checks documents, then reports.
- "Show me the review band": roles scoring 50 to 59 for you to decide on.
- "Apply to roles 12 and 15": the assistant fills simple forms and asks you before each
  submission.
- "Update the tracker: I have an interview for role 12."
Everything is recorded in jobs.db; output/ holds your CVs, letters and the jobs_overview.xlsx
workbook.

## Countries and limits
The bundled boards cover the United Kingdom (CV-Library, Reed, Indeed), and LinkedIn covers other
countries too. The example settings are for the UK; a commented second market shows how one is
added. Countries are configured in config/filters.md, so adding one is mostly
configuration plus a board extractor, which the assistant can write with you. The bundled CV
writer follows UK conventions, which suit the UK and most of Europe; a US résumé or a German
Lebenslauf needs adjustments, which the assistant should raise with you first.

## Privacy
Your details, profile, filters, searches, tracker and documents stay in your folder and are
excluded from git by .gitignore. If you publish your own fork, check `git status` before every
commit.

## Troubleshooting
| Symptom | Likely cause and fix |
|---|---|
| "JobAgent needs PyYAML" | Install the requirements: `pip install -r requirements.txt` |
| Warning "... not found, using ....example.md" | You have not created your own copy of that config file yet |
| Ingest report shows `no_normalizer:<board>` | The board has an extractor but no normaliser; ask the assistant to add one |
| A board returns nothing | The site changed its page layout; ask the assistant to update that board's extractor |
| Many roles rejected on title | Your reject-title list is too broad: run `python3 skills/job-ingest/scripts/audit_reject_titles.py` to see what each entry drops and which collide with roles you kept, then edit config/filters.md |
| Many roles flagged verify_remote | List pages often hide remote status; the advert is read before scoring |
| Roles abroad flagged verify_right_to_work | A remote role located in another country; check you may work there |
| Many rejections as onsite_abroad | An office role in a country listed in foreign_location_hints; remove that country from the list if you search there |
| PDF export fails | LibreOffice is missing or not on the path |
