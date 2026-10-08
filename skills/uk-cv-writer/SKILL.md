---
name: uk-cv-writer
description: >-
  Write a professional, ATS-optimised, UK-standard CV by tailoring a master
  profile to a specific job description. Use this whenever the user wants to
  create, tailor, rewrite, improve, or "ATS-proof" a CV or resume, including
  requests like "write my CV for this job", "tailor my CV to this advert",
  "make my CV pass ATS", "two-page UK CV", "update my CV for this role", or
  whenever the user supplies a master profile or career history plus a job
  description or advert. Produces a single-column .docx that parses cleanly
  through Applicant Tracking Systems and survives a recruiter's quick skim,
  following UK conventions (two pages of A4, British English, no photo, date of
  birth or personal data). Trigger this even if the user does not say the words
  "ATS" or "UK": any CV-tailoring task should use it.
---

# UK CV Writer

Turn a candidate's **master profile** and a **target job description** into a tailored,
two-page, UK-standard CV delivered as one ATS-safe `.docx`. (Version 1.1.0; see CHANGELOG.md.)

The CV has to work twice: an Applicant Tracking System must parse it cleanly so the details land
in the recruiter's database, and a recruiter skimming for a few seconds must see the most
relevant, quantified evidence first. Two-column templates fail the first test, so this skill
builds one clean single-column document that serves both (see `references/recruiter-scan.md`).

## The rule everything else serves: optimise, never fabricate
The master profile is the only source of facts. Tailoring means choosing, ordering and
rephrasing what is genuinely there to match the advert; it never means inventing employers,
titles, dates, metrics or skills. A claim the candidate cannot defend collapses at the first
interview question, and employers now cross-check CVs against LinkedIn. When a strong bullet
lacks a number, ask for it or flag the gap; do not supply one. `references/integrity.md` has the
guardrails; the subtle trap is inference dressed as fact (stretching "partnerships" into
"negotiated supplier contracts").

Rules the candidate's own profile states (how titles are shown, names that must not appear,
contact details, dashes) apply on top of this skill. When a calling workflow supplies its own
rules and file names, follow those too.

## Inputs
1. **Master profile**: the full career history in any format. Read all of it. If the user has
   none, offer `assets/master-profile-template.md` and help build one.
2. **Job description**: the full advert. With only a title or company, ask for the text:
   tailoring depends on it, and an untailored CV is the commonest reason for rejection.

## Workflow
Read each reference file at the step that needs it.

**Done means:** `check_cv.py` shows no FAIL and `check_grounding.py` shows no unsupported
numbers, with every flagged line confirmed as a fair restatement of the profile. Generate, check,
fix, re-run; the CV is not shown as finished before that.

1. **Parse the profile.** Every role (title, employer, location, dates), achievement and metric,
   skill, qualification and certification. Note which achievements carry numbers.
2. **Analyse the advert** (`references/jd-tailoring.md`). Extract the exact target title, Tier 1
   must-haves (essential, required or repeated), Tier 2 nice-to-haves, the role's top three to
   five priorities, and the advert's exact terms including acronyms and their spelled-out forms.
   Save `keywords.json` as `{"tier1": [...], "tier2": [...]}`, each term written as it reads in
   prose ("follow up", not "follow-up"). Avoid bare two-letter acronyms as terms.
3. **Map evidence to requirements.** For each Tier 1 item find the strongest genuine evidence;
   where the profile says the same thing in other words, mirror the advert's term honestly. No
   evidence means a gap. Decide how much depth each role gets, not whether it appears: keep a
   continuous reverse-chronological timeline, keep the current role, compress older or less
   relevant roles to one or two lines, and reframe cross-domain roles for transferable skills.
   Do not change a real job title to match the advert.
4. **Close gaps by asking, once.** Put the gaps into one batched round of questions (use an
   interactive question tool if there is one): Tier 1 requirements with no evidence, the
   strongest three to five bullets missing a metric, and any choice that materially changes the
   CV. Treat each answer as a new profile fact, used exactly as given, and suggest adding it to
   the master profile. Unanswered means the gap stays a gap. When no one can answer (an
   unattended pipeline run) or the user wants a one-shot draft, skip this step and list the
   questions and gaps in the final report instead.
5. **Write the content** (`references/content-and-bullets.md` for frameworks and verbs,
   `references/integrity.md` for the guardrails, `references/uk-standards.md` for what to
   include and exclude). Write straight into the JSON model (`assets/cv-content-schema.json`),
   because bullet length only makes sense in the layout:
   - Contact line: one phone number in the format of the CV's country, a professional email,
     LinkedIn. No home city, nationality or right-to-work line (the verifier fails them).
   - Summary: two to four lines, no first person, target identity plus years plus domain, one
     quantified standout, the advert's language used honestly.
   - Skills: confirmed hard skills only, grouped. Soft skills belong in bullets as evidence.
   - Bullets: open with a strong past-tense verb, put the number or impact early (the eye takes
     the first two words and any digits), XYZ or CAR shape, metrics only from the profile. Three
     to six for recent or relevant roles, one to three for older ones; the most relevant current
     role can carry more when that is what fills two pages honestly.
   - Line economy: each bullet is one line, or two lines with the second at least half full;
     never three or more (split it into two bullets). The second page is at least 60% full.
   - Plain punctuation: no em dashes (commas, colons or "to" instead); the builder's en dash in
     date ranges is fine. British spelling throughout.
   - No Interests or Hobbies section in any language; the verifier fails it.
6. **Build**: `python3 scripts/build_cv.py content.json "<output>.docx"`. The builder guarantees
   the ATS-safe container (A4, one column, body-level contact details, real bullet styles,
   tab-stop dates, no tables, text boxes, headers, footers or images). Keep section labels at
   the defaults (Professional Summary, Skills, Work Experience, Education) unless writing in
   another language. Name the file `Firstname-Lastname-CV.docx` unless the calling workflow
   gives a name.
7. **Verify**:
   ```bash
   python3 scripts/check_cv.py "<output>.docx" keywords.json
   python3 scripts/check_grounding.py "<output>.docx" <master-profile>
   ```
   check_cv covers structure, headings, the skim preview, UK personal data, British spelling,
   page count (rendered with LibreOffice), page balance, widow lines, timeline gaps and Tier 1
   coverage (aim for 75% or more). check_grounding lists every number and word not found in the
   profile: an unsupported number is a fabricated metric, so cut or correct it; for each flagged
   line confirm it restates something real and delete it if not. It over-flags on purpose
   (mirrored synonyms appear too), so judge each line rather than chasing zero.
   The usual fixes: a thin final page means adding more of the candidate's genuine achievements
   (about 550 to 750 words of body text fills two pages at default settings; under about 450
   stays on one); three pages means trimming older roles and anything irrelevant to this advert
   before touching the `config` margins and sizes. One page is right only for an early-career
   history.
8. **Deliver** the `.docx` with a short report: Tier 1 coverage ("11 of 12 must-haves"), the
   honest gaps left after step 4, and any bullets waiting for a number.

If the user also wants a PDF (for sending to a person), convert the finished `.docx` with
`soffice --headless --convert-to pdf`; a Word-exported PDF parses fine.

## References
- `references/uk-standards.md`: UK conventions, section order, what to leave out and why, dates,
  degree classes, British spelling.
- `references/ats-formatting.md`: how ATS parse, what breaks them, safe headings, fonts and
  dates, keyword mechanics, file naming, debunked myths.
- `references/recruiter-scan.md`: the eye-tracking evidence and layout rules for the skim.
- `references/content-and-bullets.md`: XYZ, CAR and STAR, verb bank, cliché replacements,
  summary and skills sections.
- `references/jd-tailoring.md`: the advert to keywords to mapping method.
- `references/integrity.md`: the guardrails that keep an optimised CV truthful.

## Scripts and assets
- `scripts/build_cv.py content.json out.docx`: renders the ATS-safe .docx.
- `scripts/check_cv.py out.docx [keywords.json]`: the QA gate.
- `scripts/check_grounding.py out.docx master-profile`: the anti-fabrication check.
- `assets/cv-content-schema.json`: the JSON model with a full worked example.
- `assets/master-profile-template.md`: a structure for building a master profile.
