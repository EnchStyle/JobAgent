# Integrity Guardrails

A CV that wins screening but can't survive an interview is a failure, and in
2026, employers actively cross-check CVs against LinkedIn and flag AI-inflated
applications. Optimisation that crosses into fabrication backfires. These
guardrails keep the CV both sharp and true. They are non-negotiable.

## The core rule
**The master profile is the only source of facts.** Never add an employer, title,
date, qualification, metric, or skill that isn't genuinely the candidate's. You
may *select, reorder, and rephrase*, you may not *invent*. The trap to watch is **inference dressed as fact**: stretching vague real entries ("operations & strategy", "ecosystem partnerships", "budget ownership") into specific claims the profile never makes ("ran procurement and supplier negotiation"). If the profile doesn't say it, it doesn't go on the CV. Show each role's real dates and separate stints honestly: never merge two non-contiguous periods into one continuous span (e.g. two contracts with other jobs in between), and **never relabel the actual job title to match the advert**. The one exception is a title variant the candidate's own master profile sanctions for a type of role (for example a profile that says to show "Head of Product" for product roles): that is the candidate's presentation choice, so follow it and do not invent others.

**Provenance audit (mechanical, do this every time):** after building, run `scripts/check_grounding.py <cv>.docx <master-profile>`. It flags every number and content word in the CV that isn't in the master profile. Cut unsupported numbers outright (a fabricated metric is the worst offence); for each flagged line, confirm it restates a real entry and delete anything that doesn't. Over-flagging is intended, verify, don't game it.

## The Three-Question Test
Before finalising any bullet, the candidate should be able to answer:
1. **What specifically did I do?**
2. **What did I overcome / how did I do it?**
3. **What changed as a result, and how do I know?**
If an answer is vague or fabricated, rewrite or remove the bullet.

## Specific guardrails
1. **Source, don't invent.** All numbers come from the user's input. If a bullet
   has no metric and none can be obtained, keep it qualitative and flag it in the
   match report, do **not** manufacture a figure.
2. **Confirm new skills.** Don't auto-insert a JD keyword into the Skills section
   unless the candidate genuinely has it. If the master profile is silent,
   *suggest* it and ask ("The JD wants Tableau, do you have it?") rather than
   asserting it.
3. **Reframe ≠ fabricate.** Mirroring the JD's *wording* for work the candidate
   genuinely did is good. Upgrading the *substance* (scope, seniority, results)
   beyond the truth is not. (Examples in `jd-tailoring.md`.)
4. **No title inflation.** Use real job titles (or a variant the master profile itself
   sanctions). If the candidate's title undersells equivalent work, clarify in the summary
   rather than rewriting the title.
5. **Keep it consistent with LinkedIn.** Titles, dates, and headline achievements
   should match what a recruiter will see elsewhere. Remind the user.
6. **Handle gaps honestly.** Don't disguise employment gaps with a functional
   format (which also parses badly). State them briefly and positively if needed.

## Avoid the AI "tell": and avoid gaming tricks
- Vary bullet length and structure; don't make every line the same rhythm or open
  every bullet with the same word. Preserve the candidate's real voice. (If asked
  to "make it sound less like AI", apply the `avoid-ai-writing` skill.)
- **Never** use hidden/white text or keyword stuffing. It's a debunked trick that
  modern ATS flag as manipulation, it gets CVs binned, not boosted.

## What to put in the delivery match report
- Tier 1 keyword coverage (e.g. "11/12 must-haves covered").
- **Honest gaps:** Tier 1/2 requirements with no genuine evidence, so the user
  can decide how to address them.
- Any bullets flagged as lacking a metric, with the specific number to supply.
This turns integrity limits into useful, actionable feedback for the user.

## Sources
- Robert Half 2026 survey, AI-application backlash; skill-verification [High]
- Mohawk College Career Services, ethical AI résumé use [High]
- Interview Guys, the Three-Question Test; AI-résumé pitfalls [High/Medium]
