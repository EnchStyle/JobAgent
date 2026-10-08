# checks.md : worked judgement calls for cv-verify

The gates in SKILL.md are mechanical until a CHECK item or a grounding REVIEW line needs a
decision. These examples show where the lines fall.

## Employer presentation (employer_rules)
The examples use a fictional past employer, "Northwind Software", with these rules in
config/application_rules.md: never shown as "Northwind Software, Manchester"; founder titles only for
founder or C-level postings; "Head of Product" only for product roles.
- "Northwind Software, Manchester": fail (a pairing the user ruled out).
- "Co-Founder & CEO" on a marketing manager CV: fail ("use the standard title from the
  profile"). On an application for a founder-in-residence or CEO post: pass.
- "Head of Product" on a product manager CV: pass (the profile sanctions it for product roles).
  On a business analyst CV: fail.

## Names and exclusions
- "Built the reporting dashboards for Example Current Employer Ltd" when that name is on the
  never_mention list: fail; describe the work without naming the employer.
- "Smith, J., Jones, H. et al. (2019) ..." in a publications list: pass; co-author names stay in
  a citation.
- Any mention of a past employer on the never_mention list: fail. Its absence from the timeline
  is deliberate and is not a gap to fill.

## Grounding REVIEW lines
- "Led requirements gathering with stakeholders" where the profile describes writing user
  stories and acceptance criteria with the team: a fair restatement, pass.
- "Negotiated supplier contracts" where the profile only says "partnerships": inference dressed
  as fact, fail.
- A number the profile does not contain (340% growth): fabricated metric, fail.

## Re-score
Stored 64, re-score 52 because the most relevant product work sits on page 2 under three
unrelated bullets: fail with "move the product and analytics bullets to the top of that role".
Stored 64, re-score 58 with the relevant work up front: pass; the difference is judgement noise.
