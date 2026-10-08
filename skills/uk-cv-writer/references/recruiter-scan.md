# Winning the Human Skim

The CV must work for a human reading fast, not just a machine. This file covers
what the evidence says recruiters actually do, and the layout/content choices
that win the skim, all of which are **also** ATS-safe.

## The evidence (with honest caveats)
- **The "6–7 second scan"** comes from TheLadders eye-tracking studies (2012:
  ~6s; 2018: ~7.4s). These are widely cited but are **commercial white papers**
  (small/undisclosed samples, marketing purpose), treat the exact number as
  indicative, not gospel.
- **Peer-reviewed evidence** (Pina et al., 2023, MDPI; 221 recruiters, 2,000+
  CVs) found **time spent on the Experience and Education sections most predicts
  whether a recruiter advances a CV**, and that disengagement (looking away)
  predicts rejection. No fixed 6-second cut-off emerged; engaged reviewers spent
  much longer.
- **Behavioural tracking** (Jan Tegze, 2023, 114 recruiters: 17–46s; ResumeGo
  survey, 2024, 418 recruiters: most spend 30s–1min, **71% skim** rather than
  read, **78% rate skim-ability as highly important**).

**Takeaway:** the first scan is fast and skimming; whether it converts into real
reading depends on the top of the document and the Experience section landing
fast. Optimise for an instant, relevant first impression.

## Where the eye goes (gaze map)
Initial fixations land, roughly in order, on: **name → current title & employer →
previous title & employer → dates → education**, then back to the top bullets of
the most recent role if interest holds. Spatially:
- **Top third of page 1** gets the most attention, name, contact, summary, and
  the first (most recent) role header live here. Make it count.
- **Left margin** is the vertical scan track (the "F-pattern"), job titles,
  employers, and section headings belong hard-left.
- **Right side** gets a glance for **dates**.
- **Page 2** is only read if page 1 earned it.

## Layout rules that win the skim (all ATS-safe)
`build_cv.py` already implements these; preserve them when adjusting content:
1. **Front-load the top third** with a tailored summary, never generic
   "hard-working team player" filler in the highest-value space.
2. **Strong, consistent visual hierarchy**, bold section headings with a thin
   rule; the eye anchors on them.
3. **Left-align anchors**, titles, employers, headings at the left margin.
4. **Dates right-aligned on the same line** as the title (via a tab stop, which
   stays a single paragraph, *not* a real column, so it's ATS-safe).
5. **Front-load every bullet** with the action verb and the number, the eye
   reliably catches the first ~2 words and any digits. "Increased revenue 34% by
   …" beats "Was responsible for an increase of roughly 34% in …".
6. **Numbers as anchors**, figures (34%, £2.4M, 12-person team) interrupt prose
   and pull fixations. Place them early in the bullet.
7. **3–6 bullets** for recent/relevant roles, **1–3** for older ones; dense
   walls of text get skipped.
8. **Generous white space**, clear gaps between role blocks; never a grey wall.
9. **Sizes:** name 18–22pt, headings 12–14pt bold, body 10.5–11.5pt; don't drop
   below 10pt.
10. **Identical two-line structure for every role block** so the eye predicts the
    pattern: line 1 = **bold Title** with the date right-aligned at the far right
    (a short title leaves a clear gap, so title and date never blend); line 2 =
    *Employer, Location* in italics; then the bullets, a gap, and the next role.

## What hurts the skim
- Dense paragraph prose under roles (almost never read on a first pass).
- Burying the most relevant credential when it isn't the most recent role, fix
  it by surfacing it explicitly in the summary.
- Passive openers ("Responsible for…", "Assisted with…"), the eye skips them.
- Clutter: columns, sidebars, photos, icons (also ATS-hostile).
- Too-small fonts / no breathing room → early abandonment.
- A generic, keyword-free summary in the highest-attention zone.

## The reconciliation
A clean, well-spaced, single-column, hierarchical layout is what experienced
recruiters describe as "professional and easy to read", it is **not** visually
weak. The only common design that humans like but ATS breaks is a left sidebar
(skills/contact in a second column): it scrambles on extraction and can vanish.
This skill deliberately avoids it. You lose nothing visually that you can't
recover with bold titles, a heading rule, and good spacing.

## Sources
- Pina et al., 2023, MDPI (peer-reviewed eye-tracking) [High]
- Nielsen Norman Group, F-pattern reading (2006, 2017) [High]
- ResumeGo recruiter survey, 2024 [High]
- StandOut CV synthesis incl. recruiter testimony; Jan Tegze 2023 [High/Medium]
- TheLadders eye-tracking 2012/2018 [Medium, commercial, caveated]
