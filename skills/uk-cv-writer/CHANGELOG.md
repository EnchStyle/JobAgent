# Changelog: uk-cv-writer

## 1.1.0
Revised for current Claude models after testing in the JobAgent pipeline.

- SKILL.md rewritten: the same workflow and gates, stated once each with the reason, without
  the repeated emphasis; the old "reinstall the latest .skill" version check is gone.
- Step 4 (gap questions) now names the no-questions path for unattended pipeline runs.
- No em dashes in CV text (the builder's en dash in date ranges stays).
- integrity.md: a title variant the candidate's own master profile sanctions (e.g. Head of
  Product for product roles) is followed, not treated as relabelling.
- check_cv.py: keywords match as words, so "UAT" no longer counts inside "evaluation" and "PR"
  inside "product"; terms of five or more letters still match as stems (inflected languages).
- check_grounding.py: Unicode-aware words, so accented words such as "café" are checked whole.
- build_cv.py: skill items whose first word contains a digit keep their casing.

## 1.0.0
First consolidated release. Capabilities and guardrails:

- **Core:** tailors a master profile + job description into a single-column,
  ATS-safe UK-standard `.docx` (two-line role headers, bold title + right-aligned
  dates, italic employer/location; `*...*` → italics for foreign phrases, Latin names and titles).
- **Length:** default target is a well-filled **two pages**; one page only for
  genuinely early-career histories. `check_cv.py` FAILs a final page <55% full.
- **Timeline honesty:** relevance decides a role's *depth, not its inclusion*;
  never drops the current/most-recent role; keeps a continuous timeline;
  `check_gaps()` FAILs a dropped current role or a >5-month gap.
- **Anti-fabrication:** `check_grounding.py` flags any CV number/word absent from
  the master profile; SKILL.md/integrity.md ban "inference dressed as fact",
  relabeling the real job title, and merging non-contiguous stints.
- **Layout quality:** no 1–2 word widow lines; consistent skill-item
  capitalisation (acronyms/iOS preserved).
- **Header:** phone | email | LinkedIn only, no city/country, no
  nationality/right-to-work line (single country-appropriate phone: +44 UK).
- **No interests/hobbies section**: forbidden in SKILL.md and a hard FAIL in the
  verifier.
- **Verification is a hard gate:** never deliver while `check_cv.py` shows any FAIL.
- **Gap-filling:** asks one batched round of questions to fill genuine gaps before building.
