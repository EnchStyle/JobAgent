# JD Tailoring Method

A repeatable process to turn a job description into the tailoring plan. This is
the highest-leverage step: an untailored CV is the most common rejection reason,
and tailoring is what drives both ATS keyword coverage and human relevance.

## Step 1: Extract from the JD
Read the whole JD once, then pull out:
- **The exact job title(s)** used (recruiters filter by title).
- **Required / essential** requirements ("you will have…", "essential").
- **Preferred / desirable** requirements ("nice to have", "bonus").
- **Repeated terms**: anything mentioned 2+ times is weighted; note frequency.
- **Tools, methodologies, certifications, domain jargon** (e.g. Agile, IFRS,
  Salesforce, ABM, Kubernetes), with both acronym and full form.
- **The real purpose of the hire**: what 3–5 outcomes is this person for?

## Step 2: Triage into tiers
- **Tier 1 (critical):** explicitly required, repeated, or listed first. These
  must appear in the CV, in the JD's wording, where you genuinely have them.
- **Tier 2 (important):** mentioned once, or in the "desirable" list.
- **Tier 3 (background):** assumed industry norms; don't spend space on these.

Aim for **≥75% Tier 1 coverage** in the finished CV (verified by `check_cv.py`).

## Step 3: Map evidence → requirements
For each Tier 1 (then Tier 2) item, find the strongest evidence in the master
profile and decide how to surface it:
- **Direct evidence** → feature it prominently; lead a bullet with it + a metric.
- **Adjacent/transferable evidence** → reframe an existing bullet using the JD's
  term (honest mirroring, same work, their words).
- **No evidence** → record it as a **gap**. Do not fabricate. Gaps go in the
  delivery match report so the user can address them in a covering letter or by
  adding genuine evidence to their master profile.

## Step 4: Select depth and order (keep the timeline continuous)
**Relevance decides a role's DEPTH, not whether it appears.** Keep every role on a
continuous reverse-chronological timeline, dropping a role (often to hide a career
change) is exactly what creates the unexplained gaps recruiters treat as a red flag,
and interview rates fall sharply with multi-year gaps.
- **Never drop the current / most-recent role.** It shows what the candidate is
  doing now and anchors the timeline. If it is off-target, compress it, don't cut it.
- **Scale depth to relevance:** most recent/relevant roles get 3–6 achievement
  bullets; less-relevant or older roles get 1–2 lines; a run of old or minor roles
  can collapse into a short **"Additional experience"** block (title, employer,
  dates, one line each).
- **Reframe cross-domain roles for transferable skills** instead of cutting them:
  surface the outcomes and competencies that carry over, leading teams, analysing
  data, delivering projects, owning a budget, in the target's language. A
  career change is a strength when framed this way, not noise.
- **Order bullets most-JD-relevant first** within each role.
- **Reframe seniority** to fit the target (foreground leadership/strategy for a step
  up), without inflating titles or scope, and **never change the actual job title**
  to match the advert.
- **Only omit** a role that is genuinely short (<3 months) or old (>10–15 years),
  and only when omitting it **leaves no gap**. When in doubt, compress, don't delete.

## Step 5: Write the tailored summary
Rewrite the summary for *this* application: include the target job title, 2–3
Tier 1 keywords, and one quantified proof point; align the closing phrase to the
role's stated priorities. (See `content-and-bullets.md`.)

## Step 6: Build the keyword list and verify
Write `keywords.json` = `{"tier1":[...],"tier2":[...]}` from steps 1–2, generate
the CV, then run `check_cv.py out.docx keywords.json`. If Tier 1 < 75%, find
genuine evidence for the missing terms and surface it (Skills section + a bullet);
if there is no genuine evidence, leave it as a stated gap, coverage is never a
licence to fabricate.

## Honest mirroring vs fabrication (the line)
- **OK:** the master file says "client liaison"; the JD says "stakeholder
  management", use "stakeholder management" (same work).
- **OK:** "managed 3 people" → "Led a team of 3".
- **Not OK:** adding "board-level stakeholder management" when contacts were
  mid-management; adding "financial modelling" the candidate has never done;
  inflating "was on a team" into "directed the team".

See `integrity.md` for the full guardrails.

## Sources
- Jobscan tailoring methodology & match-rate guidance [High]
- Totaljobs, keywords in your CV [High]
- Recruiter filtering survey (skills/title/certs/experience) [High]
