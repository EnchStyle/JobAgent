# uk-cv-writer

A Claude skill that writes a UK-standard, ATS-friendly CV by tailoring your master profile to one
job advert. It ships inside JobAgent (cv-tailor uses it), and it also works on its own.

## What it does
- Builds a single-column .docx: two pages of A4, British English, no photo, date of birth or
  other personal data.
- Maps the advert's requirements to your master profile and asks about gaps instead of
  inventing experience.
- Checks the result: layout and page count (`scripts/check_cv.py`), and that every number and
  claim is backed by your profile (`scripts/check_grounding.py`).

## Use it on its own
1. Copy this folder (`uk-cv-writer/`) somewhere, or zip it.
2. In the Claude app, add it as a skill (Settings, Capabilities, Skills, upload the zip), or in
   Claude Code place the folder in `~/.claude/skills/`.
3. Start from `assets/master-profile-template.md` to write your master profile.
4. Ask: "Write my CV for this advert" and attach the advert and your profile.

Needs Python 3 with python-docx, LibreOffice (`soffice`) for PDF and page counts, and
poppler-utils (`pdftotext`) for the checks.

## Files
| Path | Contents |
|---|---|
| `SKILL.md` | The workflow Claude follows |
| `references/` | UK conventions, ATS formatting, tailoring, bullet writing, integrity rules, recruiter scan |
| `assets/` | Master-profile template and the CV content schema |
| `scripts/` | build_cv.py, check_cv.py, check_grounding.py |
| `CHANGELOG.md` | Version history (1.1.0) |

Licence: MIT, as for the rest of JobAgent (see the LICENSE file at the repository root).
