# filters.example.md : hard gates applied BEFORE scoring

Copy this file to `config/filters.md` (ignored by git) and edit the yaml block for your own
search. Until you do, the scripts read this example and print a warning.

These are hard filters, not scoring inputs. A role must pass every gate here before it is ever
scored. The scripts read only the yaml block at the end; the prose explains the intent.

## Markets
A market is a country you search in. Each market has a currency, a salary floor and the period
the floor is quoted in, the place names that identify it in a listing, and a rule for onsite
roles outside your allowed places. The example ships one active market, the UK (`uk`), with
London and Manchester as office places. A commented block shows how a second market looks
(Germany, `de`, which needs a board first). To add a country, add a market here and a board for it (see AGENTS.md, "Adding a board
or a market").

## Salary
- The floor is applied only when a listing states a salary; a missing salary is never a
  rejection (the row is kept and flagged `salary_unknown` for a manual check).
- A range passes if its TOP is at or above the floor (the default `salary_range_rule: top`). Set
  `salary_range_rule: bottom` on a market to require the LOWEST pay offered to reach the floor, and
  `board_salary_factor: 1.0` on the same market so the board's own salary filter equals the floor.
- A salary in another currency than the market's is kept and flagged, never compared.
- Salaries in other periods (hourly, daily, monthly) are converted to an annual figure before
  the comparison.

## Location and work mode
Remote roles pass. Onsite or hybrid roles pass ONLY in the places listed under `location_allow`.
Place names are matched at the start of a word ("manch" matches "Manchester"); a name written as
"re:<pattern>" is a regular expression for exact rules. For other places the market's
`unlisted_onsite` rule decides: `review` keeps the role and flags
it so the advert is checked (useful where list pages do not show remote status), `reject` drops
it. A remote role whose location names a place in `foreign_location_hints` is kept but flagged
`verify_right_to_work`, because remote roles abroad usually need local right to work; an onsite
or hybrid role there is rejected.

## Freshness
Only roles posted within `max_days_old` days are kept. The posted date is used when the board
shows one.

## Reject-title pre-filter
A cheap keyword drop applied before any scoring. It removes clear mismatches only: keep it short
and specific to titles you will never apply for, because anything listed here is never seen by
the scorer. Every other role has its full advert read before it is judged. Matching is
case-insensitive on the whole title; words listed in `reject_title_word_boundary` must match as
whole words, so a short word such as "intern" cannot drop "International Product Lead".

```yaml
default_market: uk

markets:
  uk:
    label: UK
    currency: GBP
    salary_floor: 30000          # gross, in floor_period; 0 or empty means no floor
    salary_range_rule: top         # top = a range passes when its top reaches the floor; bottom = its lowest pay must
    # board_salary_factor: 0.75    # optional: this market's board filter = floor x factor (default: sources.md)
    floor_period: annual
    default_salary_period: annual  # used when a listing states pay without a period
    salary_floor_by_source: {}     # optional per-board floor, for example {linkedin: 32000}
    location_hints: [united kingdom, england, scotland, wales, northern ireland, "re:\\buk\\b"]
    unlisted_onsite: review
  # Example of a third market. Add a board for it in sources.md before enabling.
  # de:
  #   label: Germany
  #   currency: EUR
  #   salary_floor: 50000
  #   floor_period: annual
  #   location_hints: [germany, deutschland, berlin, münchen, munich, hamburg, köln, frankfurt]
  #   (also add "homeoffice" to remote_hints, and remove germany and deutschland from
  #   foreign_location_hints)
  #   unlisted_onsite: review

# Places where onsite or hybrid work is acceptable; everywhere else a role must be remote.
# Per entry: place, country (a market code above), modes, and optionally
#   match: substrings that identify the place in the location text (default: the place name)
#   match_regex: regular expressions, for example a postcode prefix
#   office_floor: a higher salary floor for onsite or hybrid roles there, in the market's floor_period
location_allow:
  - place: London
    country: uk
    modes: [onsite, hybrid, remote]
  - place: Manchester
    country: uk
    modes: [hybrid, remote]        # hybrid only: a fully onsite role there is rejected
    match: [manchester, salford]

# Places outside every market you search. An onsite or hybrid role in one of these is rejected
# (onsite_abroad); a remote role there is kept but flagged verify_right_to_work.
foreign_location_hints: [united states, usa, canada, india, germany, deutschland, france, spain,
  netherlands, poland, ireland, portugal, romania, ukraine, philippines, brazil, mexico,
  australia, singapore, south africa, new york, toronto]

# Words that mark a listing as fully remote. Do not add "hybrid": hybrid roles follow location_allow.
remote_hints: [remote, work from home, wfh, fully remote]

relevance:
  # Optional title whitelist, off by default: collect everything that passes the hard filters
  # and let the scorer judge fit, so a good role with an unusual title is not missed.
  require: false
  title_any: []

freshness:
  max_days_old: 14

reject_title_word_boundary: [intern]

# Replace with titles you will never apply for. Examples you might add: sales, recruiter,
# driver, nurse, software engineer, accountant (only if they are not your field).
# Keep this to clear mismatches. Before adding a word, check it does not hit any role you kept or
# applied to (a broad word such as "developer" also drops "Business Developer"). Never add a
# keyword screen elsewhere: anything not dropped here is read in full before it is judged.
# Check every change with skills/job-ingest/scripts/audit_reject_titles.py: add a word only when it
# names work you do not do (never a field, technology, employer or place), at least 8 adverts with it
# were read and scored, none reached 50 or was applied to and the best scored 40 or lower; then run
# reapply_title_list.py to drop matching roles that are still unread.
reject_title_contains:
  - intern
  - trainee
  - unpaid
```
