# ATS Formatting & Keywords

How Applicant Tracking Systems read a CV, what breaks them, and how to make a
document parse perfectly and rank well. `build_cv.py` already enforces the
structural rules; this file explains the *why* and covers the content/keyword
choices that are Claude's job.

## How an ATS actually reads a CV (brief)
A parser runs a pipeline: extract text → tokenise → segment into sections (by
matching headings against a whitelist) → named-entity recognition (tag PERSON,
ORG, DATE, TITLE, SKILL) → write a structured record into a searchable database.
**Recruiters search that extracted database, not your document.** So the goal is
clean extraction into the right fields, then keyword findability.

Reality check (debunking the scare stories):
- The "75% of CVs are auto-rejected by ATS" claim is a **myth** with no credible
  source. ATS are mostly search/organisation tools; **humans make rejections.**
- ATS do **not** mystically "score" you out of contention on their own; recruiters
  configure filters and read the results.
So: don't fear the ATS, just don't hand it something it can't parse, and make
sure your genuine keywords are findable.

## Formatting: DO (all enforced by `build_cv.py`)
- **Single column, top-to-bottom.** This is the single most important rule.
- **Contact details in the body** as plain text, never in a header/footer/text
  box (those layers are frequently ignored).
- **Standard, whitelisted section headings**: used verbatim:
  `Professional Summary` (or `Summary`), `Skills`, `Work Experience` (or
  `Professional Experience`), `Education`, `Certifications`. Avoid creative
  labels ("My Journey", "What I've Done"), they get misrouted or dropped.
- **ATS-safe fonts:** Calibri, Arial, Cambria, Georgia, Garamond. Body 10–12pt,
  headings 14–16pt, name 18–22pt.
- **One consistent date format**: e.g. `January 2020 – March 2023`, with
  `Present` for current roles.
- **Real bullet characters** (• or -) via a list style, not decorative
  glyphs/emoji.
- **Skills as bare, comma-separated tokens** (highest NER recall) **and** woven
  into experience bullets (for context/semantic matching).
- **Acronyms + spelled-out forms** on first use: `Search Engine Optimization
  (SEO)`, `Project Management Professional (PMP)`.

## Formatting: DON'T (each breaks parsing)
- **Multiple columns / sidebars**: the extractor reads straight across the page
  and interleaves the columns into gibberish. The #1 cause of parse failure;
  sidebar content (often skills/contact) can vanish entirely.
- **Tables**: cells are extracted out of order, scrambling rows.
- **Header/footer content**: commonly ignored; contact details there can be lost.
- **Text boxes**: stored outside the main body; frequently skipped.
- **Images, icons, logos, photos**: ATS reads text, not pictures.
- **Skill rating bars / charts**: the label and level are both invisible; write
  `Python (Advanced)` in plain text instead.
- **Non-standard bullets / emoji / decorative arrows**: tokenise as junk; some
  parsers treat them as section breaks.
- **Curly quotes** can trip older parsers, straight quotes are safest.
- **Colour as information**: colour text is invisible in plain-text extraction.
- **Design-tool / scanned PDFs** (Canva, Illustrator, image exports), no
  reliable text layer; require OCR and degrade badly.

## File format & naming
- This skill outputs **`.docx`**, which has a guaranteed text-ordering and is the
  most consistently parsed single format, ideal for uploads and older/enterprise
  ATS (Taleo, older iCIMS).
- A **text-based PDF exported from Word** also parses well in modern ATS and locks
  the visual layout for a human reader. Only design-tool/scanned PDFs are the
  problem. If the posting names a format, follow it.
- **Name the file** `Firstname-Lastname-CV.docx`. Avoid spaces, version numbers,
  and "final_v3".

## Keyword strategy (Claude's job)
Matching is still dominated by recruiters' Boolean keyword search over the
extracted database; newer AI/semantic layers (Workday+HiredScore, Greenhouse AI,
Lever) supplement but don't replace it. So optimise for **exact match first**,
phrased naturally.

What recruiters filter on (survey of recruiters): **skills (76%)**, job title
(55%), certifications (51%), years of experience (44%). Implications:
- Mirror the **exact target job title** somewhere (summary or headline) if the
  candidate's title differs but the role is equivalent.
- Put each high-priority keyword in **at least two places**: the Skills section
  (bare token) **and** inside an achievement bullet (context).
- Lead the summary with 3–4 core JD keywords.
- Use the JD's exact spelling/abbreviation; include both acronym and full form.

**Do not keyword-stuff.** Don't repeat a term more than ~3–4 times, don't list
skills the candidate lacks, and don't force keywords into awkward sentences -
modern AI relevance scorers penalise this, and recruiters notice. A keyword in a
real achievement sentence outranks one in a bare dump. **White / hidden text is a
debunked trick that now gets CVs flagged, not boosted.** See `integrity.md`.

Use `check_cv.py … keywords.json` to confirm ≥75% Tier 1 coverage.

## Sources
- Jobscan, ATS mechanics; tables/columns parse tests; fonts; PDF vs Word;
  file-naming [High]
- ResumeOptimizerPro, 5-parser engineering comparison & failure modes [High]
- Harvard Business School "Hidden Workers" (2021); Interview Guys (origin of the
  75% myth) [High]
- iCIMS glossary; Yale OCS [High]
