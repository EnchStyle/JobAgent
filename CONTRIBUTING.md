# Contributing

Contributions are welcome, especially new board extractors, new markets, and fixes for
extractors broken by site changes.

- Keep personal data out of every commit: no real names, contact details, employers you applied
  to, salaries or search histories, including in examples and comments. Use the fictional
  sample candidate (Jordan A. Bennett) or "Acme" and "Example" names.
- Keep behaviour configurable in config/ rather than hard-coded.
- Run `python3 -m pytest -q` before opening a pull request, and add a test for new filter or
  parsing behaviour.
- For a new board: add `skills/job-ingest/scrapers/<board>.js`, a `normalize_<board>()` function
  registered in `NORMALIZERS` and `URL_BASE` in `normalize.py`, a disabled example block in
  `config/sources.example.md`, and a sample card in `tests/fixtures/cards.json` (the test suite
  runs every bundled normaliser on it).
- Writing style for anything a candidate or employer sees: British English, no em dashes.
