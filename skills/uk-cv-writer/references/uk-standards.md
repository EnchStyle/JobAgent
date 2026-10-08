# UK CV Standards

Conventions for a UK CV (not a US resume). These are encodable rules drawn from
UK government and university careers authorities (sources at the end).

## Length
- **Two pages of A4 is the standard** for an experienced professional. This is
  the default target.
- **One page** only for school leavers / very early career with little to show.
- **Three pages** is defensible only for 15+ years' experience or senior/
  specialist roles, and must be earned by substance, not padding. Never exceed 3.
- **Academic CVs** are the exception: no fixed limit; include publications,
  conferences, teaching, grants, full referee details.
- Rule of thumb: a tight two pages beats a padded three.

## Section order (experienced professional)
1. **Name** (as the heading, do **not** title the document "Curriculum Vitae"
   or "CV"; it wastes the most valuable space).
2. **Contact details**.
3. **Professional summary / personal profile** (recommended).
4. **Skills** (optional but useful for ATS keyword matching; especially for
   technical/quantitative roles, place near the top).
5. **Work experience** (reverse chronological).
6. **Education** (reverse chronological).
7. **Additional**, certifications, languages, professional memberships.
8. **References** (optional; usually omitted, see below). This skill does **not** include an interests/hobbies section.

For **graduates / early career**, swap 5 and 6 so **Education comes before Work
Experience**.

## Contact details
**Include:** full name, mobile number, professional email
(`firstname.lastname@…`), **city/region only**, and a LinkedIn URL if current.
Add a portfolio/website link if relevant to the role.

**Do not include a full home address**, city/region is enough, and a full
address is a fraud risk when a CV is uploaded to job boards. Put all contact
details in the **body**, never in a Word header/footer (ATS often ignore those).

## What to EXCLUDE on a UK CV (and why)
UK norms, shaped by the Equality Act 2010, mean these are omitted to avoid
inviting discrimination and to protect privacy:
- **Photograph**: not standard; risks appearance bias. (Exception: acting/
  modelling.)
- **Date of birth / age**: age is a protected characteristic.
- **Marital status, nationality, gender, religion**: all protected
  characteristics; right to work is checked separately, after offer.
- **Full home address**: city/region only.
- **National Insurance number**: sensitive ID; never on a CV.
- **Salary** (current or expected), discuss later, only if asked.
- **The title "Curriculum Vitae"/"CV"**: the name is the heading.
- **Referees' names and contact details**: don't put third parties' personal
  data on a circulated document (academic CVs excepted).

The verifier (`check_cv.py`) scans for most of these and flags them.

## Dates
- Use **month + year**, written out: `March 2021 – Present`. (`Mar 2021` is also
  fine; pick one style and stay consistent.)
- Use **"Present"** for an ongoing role, not "Current".
- Avoid `04/2021` and `Jan. 2021` (a full stop after the abbreviation trips some
  ATS) and avoid year-only ranges except for older roles.
- Everywhere else on the CV, UK date order is **day-month-year** (16 June 2026).

## Education & UK qualifications
- Reverse chronological. Per entry: qualification + classification, institution,
  dates.
- **Degree classifications:** write `First-Class Honours` (or `1st`), `2:1`,
  `2:2`, `Third`. Example: `BA (Hons) Marketing, 2:1`.
- **A-levels:** subject + grade (e.g. `Mathematics – A, Chemistry – B`).
- **GCSEs:** group them, `9 GCSEs (A–C) including Maths and English`, don't
  list each one.
- Include degree modules only if directly relevant to the role.
- Predicted results: state clearly, e.g. `predicted 2:1, graduating June 2026`.
- For experienced professionals, keep education to a compact block after
  experience.

## Personal profile / summary
- 2–4 lines, ~50–150 words, placed just under contact details.
- Write in **"silent first person"**, no "I"/"he"/"she". UK/most-European
  convention. ("Senior finance analyst with 8 years' experience…" not "I am a…").
- Lead with professional identity + years + domain, add one quantified standout,
  and align to the target role. It is a hook, not a biography.
- Pick first-person-implied OR third-person and be consistent; never switch.

## References
- **Interests / hobbies:** not used, do not add an interests or hobbies section.
- **References:** it is fully acceptable (and space-saving) to **omit** the
  section; employers assume references are available. "References available on
  request" is harmless filler, drop it if space is tight. (Academic CVs: include
  full referee details.)

## British English & terminology
- Use **"CV"**, never "resume/résumé".
- British spelling: organise, recognise, specialise, programme, centre, colour,
  honour, behaviour, licence (noun)/license (verb), practice (noun)/practise
  (verb), traveller, modelling, ageing, defence, whilst.
  - Note: `-ize` endings (organize, optimize) are *valid* in Oxford British
    spelling, so they are acceptable; the clear US-only forms above are what to
    avoid.
- "mobile" not "cell"; "CV" not "resume"; "covering letter" not "cover letter".
- Currency in achievements: **£** (e.g. "raised £5,000").

## Conflicts / judgement calls
- **Profile vs none:** include by default for professionals; for graduates a
  "Key Achievements" block can substitute. Always include a profile if the CV is
  uploaded without a covering letter.
- **One vs two pages for graduates:** two pages is the ceiling; one is fine only
  if experience doesn't fill two. The "one-page rule" is a US import, not a UK
  requirement.
- **Right to work:** don't state nationality. A neutral "Right to work in the
  UK" line is acceptable only if the candidate is applying from abroad and wants
  to pre-empt the question; it is not standard.

## Sources (UK authorities)
- National Careers Service (gov.uk), careers-advice/cv-sections [High]
- Prospects.ac.uk (Jisc/AGCAS), how-to-write-a-cv; personal-statement [High]
- TARGETjobs, big guide to CV writing [High]
- Reed.co.uk, free CV template; education on a CV; Equality Act 2010 [High]
- Totaljobs, keywords in your CV [High]
