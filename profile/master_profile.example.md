# master_profile.example.md : how to set up your master profile

Start here: copy `skills/uk-cv-writer/assets/master-profile-template.md` to
`profile/master_profile.md` (ignored by git) and fill it in, section 0 included.
`examples/master_profile.sample.md` shows a filled-in profile for a fictional candidate.

The master profile is the only source of facts the pipeline may use: the scorer credits only what
it states, and the CV and cover-letter checks flag any number or claim it does not contain. Keep
it long and complete; each CV selects from it.

## Section 0, CV output rules (read by cv-tailor, cover-letter and cv-verify)
Your standing instructions for how your career is presented. Examples:
- Standard title for each role, and any alternative title allowed for a given kind of posting
  (for example "Head of Product" only for product roles).
- Roles that may be left out, and how a gap should be framed if one opens.
- Names that never appear (a current employer, a confidential client). Mirror these in the
  never_mention list in config/application_rules.md so workflow_check.py enforces them.
- What kind of practitioner you are, stated honestly (for example "builds with AI tools; not a
  software engineer"), so the scorer and the letters do not overclaim.
- The voice for cover letters (for example "plain, direct, evidence first").
