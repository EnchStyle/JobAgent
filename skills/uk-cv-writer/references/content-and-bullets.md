# Content & Bullets

How to write the words. The structure is handled by the generator; this is where
a CV is won or lost.

## Achievement bullets: the frameworks
Every experience bullet should answer **"so what?"**, what changed because of
you, and how much. Open with a strong past-tense verb (present tense only for the
current role) and put the impact early.

**Google XYZ formula** (the gold standard):
> "Accomplished **[X]** as measured by **[Y]** by doing **[Z]**."
> X = outcome, Y = the number, Z = how you did it.

**CAR** (Challenge–Action–Result), best for tight single-line bullets:
> [≤5-word context] + [action verb + what you did] + [quantified result].

**STAR** (Situation–Task–Action–Result), for senior roles needing context.

These are scaffolds, not templates to repeat verbatim, vary sentence length and
structure so the CV reads like a person wrote it (see `avoid-ai-writing` cues in
`integrity.md`).

### Before → after
- "Responsible for managing the sales team" →
  **"Led an 8-person sales team to 112% of annual quota by restructuring
  territories and introducing weekly pipeline reviews."**
- "Helped improve customer satisfaction" →
  **"Raised NPS from 42 to 67 in 12 months by launching a post-resolution
  call-back programme across 3 contact centres."**
- "Worked on cost reduction" →
  **"Cut vendor spend by £340K (18%) by renegotiating 12 supplier contracts."**

### Quantification prompts (use when a bullet has no number)
How many people/customers? By how much (%, £, units)? How much faster vs before?
What was the before→after state? What scale (budget, revenue, users, geography)?
**If the master profile has no number and the user can't supply one, keep the
bullet qualitative and flag it, never invent a figure.**

## Line economy: no widows, no half-empty pages
Tight line breaks make a CV look professional and save space:
- Make every bullet either one clean line or two lines whose second line is at least half full. Never three or more lines: split a long achievement into two bullets instead. Use as many bullets as the advert needs, within two pages. Never leave a wrapped line carrying just 1-2 words (a lone "growth." or "discipline.") - it looks unfinished and wastes a whole line.
- Two fixes: (a) **tighten** - cut filler ("in order to"->"to", drop "successfully"/"responsible for") so it fits one line; or (b) **fill** - add a concrete, genuine detail or metric so the last line is reasonably full. Never pad with empty words.
- **Fill the page.** A two-page CV should fill close to two full pages. The second page must be at least 60% full (less means achievements were left out). A 1.3-1.6 page CV with a half-empty second page looks unbalanced - add more genuine achievements to reach a balanced two pages (keep every role at appropriate depth; recent roles can carry 5–6 bullets). **Two full pages is the default target for an experienced candidate;** tighten to one page only for a genuinely early-career history. Don't ship a mostly-empty final page.

The verifier (check_cv.py) flags both widow lines and an under-filled final page.

## Action-verb bank
- **Leadership:** Led, Directed, Spearheaded, Orchestrated, Oversaw, Mentored,
  Mobilised, Scaled, Restructured, Championed.
- **Achievement/delivery:** Delivered, Achieved, Exceeded, Surpassed, Secured,
  Won, Generated, Drove, Launched, Executed.
- **Analytical/financial:** Analysed, Forecasted, Modelled, Audited, Benchmarked,
  Quantified, Optimised, Evaluated.
- **Improvement/efficiency:** Streamlined, Redesigned, Overhauled, Automated,
  Standardised, Consolidated, Reduced, Accelerated, Eliminated.
- **Technical:** Engineered, Architected, Built, Integrated, Migrated, Deployed,
  Refactored, Developed, Automated.
- **Communication/influence:** Negotiated, Presented, Authored, Persuaded,
  Influenced, Facilitated, Liaised, Briefed.

### Verbs/phrases to AVOID (weak, passive)
"Responsible for", "Duties included", "Tasked with", "Helped/Assisted with"
(without ownership), "Involved in", "Worked on", "Made", "Took part in". Replace
each with the actual action you took.

## Clichés → replace with evidence
The principle is **show, don't tell**. Any trait you can simply *assert* is
worthless; prove it instead.
- "Team player" → name a collaborative, measurable outcome.
- "Results-driven" → show a result ("grew ARR £2M→£5.4M in 18 months").
- "Hardworking / dedicated" → show scope ("delivered 3 launches while covering a
  vacant senior role").
- "Excellent communicator" → "Presented quarterly results to the board; briefed a
  400-person all-hands."
- "Detail-oriented" → "Maintained 99.8% data accuracy across 50,000+ monthly
  transactions."
- "Passionate about…" → demonstrate it with something you built or ran.
Cut corporate filler: "synergy", "leverage" (as a verb), "go-getter", "think
outside the box", "dynamic".

## Professional summary
2–4 lines, ~50–150 words, **no first-person pronouns** ("silent first person").
Formula:
> [Seniority + role identity] with [X years'] experience in [domain], specialising
> in [1–2 core competencies from the JD]. [One quantified achievement.] [Optional:
> alignment to the target role.]

Example:
> "Senior FP&A analyst with 8 years' experience in SaaS and financial services,
> specialising in board-level reporting and three-statement modelling. Cut the
> monthly close from 12 to 7 days through automation. Now focused on strategic
> finance in a high-growth environment."

Avoid: "Seeking a challenging role where I can grow" (says nothing about value to
the employer); generic adjective stacks; copying the JD verbatim.

## Skills section
- **Hard skills only** (tools, languages, methodologies, certifications), these
  are verifiable and searchable. Put **soft skills into the bullets as evidence**,
  not in the list ("leadership" proven by a bullet, not claimed in a list).
- Group them (Technical / Tools / Methodologies / Languages); ~8–15 genuinely
  held, JD-relevant skills. Quality over quantity; 30+ signals padding.
- No proficiency bars (not parseable), no obvious entries ("Microsoft Word",
  "Email").
- **Consistent capitalisation.** Each skill item is sentence case: first letter capitalised, the rest lower except acronyms and proper nouns - so "Power BI", "Stakeholder management", but "SQL", "CRM", "iOS". The generator applies the first-letter capital automatically (and leaves anything whose first word already has a capital untouched), so just write items naturally.
- **Italicise foreign phrases, Latin names and publication titles** with *...* markup, for example *per se* or a book title. Do NOT italicise acronyms or brand names. The same *...* markup works in the summary, bullets and education detail.

## Common rejection triggers to avoid
Typos (a single one materially hurts), no tailoring, unprofessional/missing
contact details, passive duty-lists with no metrics, hard-to-skim layout, wrong
length, irrelevant content in prime space, inconsistent formatting, generic
summary, missing employment dates, and any over-claiming that won't survive an
interview.

## Sources
- Harvard (FAS/Extension) résumé guides & action verbs [High]
- Laszlo Bock / Google XYZ formula [High]
- Rezi (102,944-CV analysis of weak verbs); Teal; Jobscan summaries [High/Medium]
- Robert Half 2026 survey (AI-resume backlash, verification) [High]
