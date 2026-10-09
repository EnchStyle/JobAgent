"""Core behaviour tests: run with  python3 -m pytest -q  from the project root.

They use explicit config dictionaries, the shipped example settings (tests/conftest.py) and a
temporary data folder, so they never touch your own config files or jobs.db.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "job-ingest" / "scripts"))

import filters  # noqa: E402
import normalize as norm  # noqa: E402
from lib import jobdb, markets  # noqa: E402

CFG = {
    "default_market": "uk",
    "markets": {
        "uk": {"label": "UK", "currency": "GBP", "salary_floor": 30000, "floor_period": "annual",
               "location_hints": ["united kingdom", "england"], "unlisted_onsite": "review"},
        "ie": {"label": "Ireland", "currency": "EUR", "salary_floor": 40000, "floor_period": "annual",
               "location_hints": ["dubl", "ireland", "cork"],
               "generic_location_terms": ["ireland"], "unlisted_onsite": "reject"},
    },
    "location_allow": [
        {"place": "London", "country": "uk", "modes": ["onsite", "hybrid", "remote"], "office_floor": 40000},
        {"place": "Dublin", "country": "ie", "modes": ["onsite", "hybrid", "remote"]},
    ],
    "foreign_location_hints": ["germany", "united states"],
    "remote_hints": ["remote", "work from home"],
    "freshness": {"max_days_old": 14},
    "reject_title_word_boundary": ["intern"],
    "reject_title_contains": ["intern", "trainee"],
}


def job(**kw):
    base = {"source": "reed", "market": "uk", "title": "Product Manager", "location": "London",
            "work_mode": "hybrid", "salary_min": 45000, "salary_max": 55000,
            "salary_currency": "GBP", "salary_period": "annual", "date_posted": None}
    base.update(kw)
    return base


def test_keeps_a_good_london_role():
    assert filters.classify(job(), CFG)["keep"]


def test_salary_floor_uses_top_of_range():
    assert filters.classify(job(salary_min=20000, salary_max=31000, location="Remote", work_mode="remote"), CFG)["keep"]
    r = filters.classify(job(salary_min=20000, salary_max=25000, location="Remote", work_mode="remote"), CFG)
    assert not r["keep"] and r["reason"] == "salary:below_uk_floor"


def test_office_floor_applies_onsite_only():
    assert not filters.classify(job(salary_max=36000), CFG)["keep"]          # London hybrid, below 40k
    assert filters.classify(job(salary_max=36000, location="Remote", work_mode="remote"), CFG)["keep"]


def test_missing_or_foreign_currency_salary_is_kept_and_flagged():
    r = filters.classify(job(salary_min=None, salary_max=None, salary_unknown=1), CFG)
    assert r["keep"] and "salary_unknown" in r["flags"]
    r = filters.classify(job(salary_currency="USD", salary_max=10), CFG)
    assert r["keep"] and "salary_other_currency" in r["flags"] and r["salary_unknown"] == 0


def test_onsite_abroad_is_rejected():
    r = filters.classify(job(location="Berlin, Connecticut, United States", work_mode="onsite"), CFG)
    assert not r["keep"] and r["reason"] == "location:onsite_abroad"


def test_place_hints_match_word_starts():
    from lib import markets as mk
    assert mk.hint_match("dubl", "dublin, ireland")
    assert not mk.hint_match("re:\\buk\\b", "kyiv, ukraine")
    assert mk.hint_match("re:\\buk\\b", "leeds, uk")


def test_monthly_pay_against_an_annual_floor():
    ie = dict(source="linkedin", market="ie", location="Dublin", salary_currency="EUR", salary_period="month")
    assert filters.classify(job(salary_min=3000, salary_max=3500, **ie), CFG)["keep"]       # 42,000 a year
    assert not filters.classify(job(salary_min=2500, salary_max=3000, **ie), CFG)["keep"]   # 36,000 a year


def test_location_rules():
    assert filters.classify(job(location="Birmingham"), CFG)["location_status"] == "review"
    r = filters.classify(job(source="linkedin", market="ie", location="Galway", salary_currency="EUR",
                             salary_period="annual", salary_max=55000), CFG)
    assert not r["keep"] and r["reason"] == "location:ie_other_city_onsite"
    r = filters.classify(job(location="Berlin, Germany", work_mode="remote"), CFG)
    assert r["keep"] and "verify_right_to_work" in r["flags"]


def test_reject_title_whole_word():
    assert not filters.classify(job(title="Marketing Intern"), CFG)["keep"]
    assert filters.classify(job(title="Head of International Product"), CFG)["keep"]


def test_salary_parsers():
    assert norm.parse_salary_gbp("£45,000 - £55,000 per annum")["salary_max"] == 55000
    assert norm.parse_salary_gbp("GBP 80K")["salary_min"] == 80000
    s = norm.parse_salary_any("60.000 € pro Jahr")
    assert (s["salary_min"], s["salary_currency"], s["salary_period"]) == (60000, "EUR", "annual")
    s = norm.parse_salary_any("$150,000/yr")
    assert (s["salary_min"], s["salary_currency"]) == (150000, "USD")
    assert norm.parse_salary_any("€3,500/month")["salary_period"] == "month"
    assert norm.parse_salary_any("Competitive") == {}


def test_market_resolution():
    assert markets.market_for("linkedin", "Dublin, Ireland", CFG) == "ie"
    assert markets.market_for("reed", "Remote", CFG) in markets.markets(CFG)
    assert markets.foreign_location("Austin, United States", CFG)


def test_unknown_source_raises():
    try:
        norm.normalize("someboard", {"id": 1})
    except ValueError:
        return
    raise AssertionError("expected ValueError for a source with no normaliser")


def test_database_dedupe(tmp_path):
    db = tmp_path / "t.db"
    con = jobdb.connect(db)  # creates the schema on first use
    j = {"source": "reed", "job_id": "1", "title": "PM", "company": "Acme", "location": "London"}
    assert jobdb.insert_job(con, j) == 1
    assert jobdb.insert_job(con, j) == 0
    assert jobdb.total(con) == 1


def test_salary_parser_ignores_numbers_outside_a_range():
    assert norm.parse_salary_any("€55,000/yr + 10% bonus")["salary_max"] is None
    assert norm.parse_salary_any("60.000 € pro Jahr, 40 Std./Woche")["salary_min"] == 60000
    s = norm.parse_salary_any("$120k - 140k")
    assert (s["salary_min"], s["salary_max"]) == (120000, 140000)
    s = norm.parse_salary_any("45 000 – 55 000 EUR per year")
    assert (s["salary_min"], s["salary_max"], s["salary_period"]) == (45000, 55000, "annual")


def test_every_bundled_normaliser():
    import datetime
    import json
    cards = json.loads((ROOT / "tests" / "fixtures" / "cards.json").read_text(encoding="utf-8"))
    today = datetime.date(2026, 1, 15)
    for source, card in cards.items():
        j = norm.normalize(source, card, today)
        assert j["source"] == source and j["job_id"] and j["title"], source
        assert j["date_found"] == "2026-01-15", source
    assert norm.normalize("cv_library", cards["cv_library"], today)["location"] == "Leeds"
    li = norm.normalize("linkedin", cards["linkedin"], today)
    assert (li["salary_min"], li["salary_currency"]) == (60000, "EUR")


def test_email_check_ignores_sentence_punctuation(tmp_path):
    sys.path.insert(0, str(ROOT / "skills" / "cv-verify" / "scripts"))
    import workflow_check
    f = tmp_path / "letter.md"
    f.write_text("Dear team,\n\nPlease reach me at jordan.bennett@example.com.\n", encoding="utf-8")
    out = workflow_check.check(str(f), market="uk", kind="letter")
    assert not [i for i in out["items"] if i["check"] == "contact email"]


def test_data_dir_env(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("JOBAGENT_DATA_DIR", str(tmp_path))
    from lib import paths
    importlib.reload(paths)
    try:
        assert paths.DB_PATH == tmp_path / "jobs.db" and paths.INBOX == tmp_path / "inbox"
    finally:
        monkeypatch.delenv("JOBAGENT_DATA_DIR")
        importlib.reload(paths)


def _db(tmp_path):
    con = jobdb.connect(tmp_path / "t.db")
    jobdb.insert_job(con, {"source": "reed", "job_id": "1", "title": "Product Manager", "company": "Acme Ltd",
                           "location": "London", "date_found": __import__("datetime").date.today().isoformat()})
    return con


def test_rescore_below_threshold_goes_to_review(tmp_path):
    sys.path.insert(0, str(ROOT / "skills" / "cv-verify" / "scripts"))
    import record_verdict
    con = _db(tmp_path)
    jobdb.update_status(con, 1, "cv_generated", match_score=64)
    out = record_verdict.record_verdict(1, "pass", rescore=52, con=con)
    row = jobdb.get_by_id(con, 1)
    assert out["status"] == "scored" and row["match_score"] == 64 and row["rescore"] == 52


def test_duplicates_and_repeat_guard(tmp_path):
    con = _db(tmp_path)
    assert jobdb.possible_duplicates(con, "ACME", "Product Manager")[0]["id"] == 1
    jobdb.update_status(con, 1, "applied", date_applied="2026-01-15")
    assert jobdb.applied_to_employer(con, "Acme Limited")[0]["id"] == 1


def test_tracker_note_date_not_doubled_and_handoff(tmp_path):
    sys.path.insert(0, str(ROOT / "skills" / "app-tracker" / "scripts"))
    import tracker
    con = _db(tmp_path)
    tracker.cmd_note(con, 1, "2026-01-15 called the recruiter")
    notes = jobdb.get_by_id(con, 1)["notes"]
    assert notes.count("2026-") == 1
    tracker.cmd_mark_blocked(con, 1, "account wall")
    out = tracker.cmd_handoff(con, path=str(tmp_path / "h.md"))
    assert out["rows"] == 1 and "Acme Ltd" in (tmp_path / "h.md").read_text(encoding="utf-8")


def test_unread_rejection_is_refused_and_audited(tmp_path):
    con = _db(tmp_path)
    import pytest
    with pytest.raises(ValueError):
        jobdb.update_status(con, 1, "rejected")
    jobdb.update_status(con, 1, "rejected", notes="2026-01-15 keyword screen of full advert: 3 (below shortlist)")
    assert [r["id"] for r in jobdb.unread_rejections(con)] == [1]
    con.execute("UPDATE jobs SET status='found', notes=NULL WHERE id=1")
    jobdb.set_score(con, 1, 30, {"fit_score": 30}, status="rejected")
    assert jobdb.unread_rejections(con) == []


def test_batch_commits_once_and_rolls_back(tmp_path):
    con = _db(tmp_path)
    jobdb.begin_batch(con)
    jobdb.update_status(con, 1, "scored", match_score=61)
    jobdb.end_batch(con, ok=False)
    assert jobdb.get_by_id(con, 1)["status"] != "scored"
    jobdb.begin_batch(con)
    jobdb.update_status(con, 1, "scored", match_score=61)
    jobdb.end_batch(con)
    assert jobdb.get_by_id(con, 1)["match_score"] == 61


def test_housekeeping_dry_run(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "lib"))
    from lib import housekeeping
    rep = housekeeping.run(dry_run=True)
    assert rep["dry_run"] is True and isinstance(rep["inbox_not_ingested"], list)


def _use_sources(text):
    """Point the config loader at a temporary sources.md for one test."""
    import os
    from lib import config_loader
    p = Path(os.environ["JOBAGENT_CONFIG_DIR"]) / "sources.md"
    p.write_text(text, encoding="utf-8")
    config_loader._load_cached.cache_clear()
    return p


PLAN = """```yaml
search_plan:
  cycle_days: 3
  max_searches_per_run: 3
  board_salary_factor: 0.9
  places:
    uk_remote: {market: uk, remote: true}
    london: {market: uk, city: London, location: "London, England, United Kingdom"}
  families:
    product: {standing: true, places: [uk_remote, london], keywords: [product manager, product owner]}
    delivery: {standing: false, places: [uk_remote], keywords: [project manager]}
  boards:
    reed:
      remote: "https://www.reed.co.uk/jobs/remote-{slug}-jobs?salaryFrom={floor}"
      city: "https://www.reed.co.uk/jobs/{slug}-jobs-in-{city_slug}?salaryFrom={floor}"
scrape_sources:
  reed: {enabled: true, market: uk}
```
"""


def test_search_plan_scope_rotation_and_floor():
    sys.path.insert(0, str(ROOT / "skills" / "job-ingest" / "scripts"))
    import search_plan as sp
    from lib import config_loader
    p = _use_sources(PLAN)
    try:
        standing, plan = sp.build()
        assert {s["keyword"] for s in standing} == {"product manager", "product owner"}
        assert any("jobs-in-london" in s["url"] for s in standing)
        floor = int(config_loader.filters()["markets"]["uk"]["salary_floor"] * 0.9) // 1000 * 1000
        assert all(f"salaryFrom={floor}" in s["url"] for s in standing)
        picked, deferred = sp.due(standing, plan, {})
        assert len(picked) == 3 and len(deferred) == 1          # capped, the rest next run
        state = {s["id"]: sp._today().isoformat() for s in picked}
        picked2, _ = sp.due(standing, plan, state)
        assert [s["id"] for s in picked2] == deferred             # done searches are not due yet
        req, _ = sp.build(scope_families=["delivery"])
        assert [s["keyword"] for s in req] == ["project manager"]          # a request runs only its scope
    finally:
        p.unlink()
        config_loader._load_cached.cache_clear()


def test_title_suffix_counts_as_possible_duplicate(tmp_path):
    con = jobdb.connect(tmp_path / "t.db")
    jobdb.insert_job(con, {"source": "reed", "job_id": "9", "title": "Senior Product Owner (Payments)",
                           "company": "Example Retail Ltd", "location": "London", "date_found": "2099-01-01"})
    assert jobdb.possible_duplicates(con, "Example Retail Ltd", "Senior Product Owner")
    assert not jobdb.possible_duplicates(con, "Example Retail Ltd", "Product")   # one word is too loose


def test_tracker_applied_needs_verified(tmp_path):
    sys.path.insert(0, str(ROOT / "skills" / "app-tracker" / "scripts"))
    import tracker
    con = _db(tmp_path)
    jobdb.update_status(con, 1, "cv_generated")
    try:
        tracker.cmd_set_status(con, 1, "applied")
        raise AssertionError("expected a refusal before cv-verify")
    except SystemExit:
        pass
    jobdb.update_status(con, 1, "verified")
    tracker.cmd_set_status(con, 1, "applied")
    assert jobdb.get_by_id(con, 1)["status"] == "applied"


def test_tracker_reject_needs_a_reason(tmp_path):
    sys.path.insert(0, str(ROOT / "skills" / "app-tracker" / "scripts"))
    import tracker
    con = _db(tmp_path)
    try:
        tracker.cmd_set_status(con, 1, "rejected")
        raise AssertionError("expected a refusal without --note")
    except SystemExit:
        pass
    tracker.cmd_set_status(con, 1, "rejected", note="user: not interested")
    assert jobdb.get_by_id(con, 1)["status"] == "rejected"


def test_ingest_archives_what_it_read(tmp_path):
    import json
    import scrape_ingest
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "scrape_x_reed_20990101.json").write_text(json.dumps({"source": "reed", "cards": []}), encoding="utf-8")
    (inbox / "scrape_bad_reed_20990101.json").write_text("{not json", encoding="utf-8")
    rep = scrape_ingest.run(inbox_dir=str(inbox), db_path=str(tmp_path / "t.db"))
    assert rep["archived_files"] == 1 and rep["skipped_files"] == 1
    assert [f.name for f in inbox.glob("scrape_*.json")] == ["scrape_bad_reed_20990101.json"]


def test_runlock_one_run_at_a_time():
    from lib import runlock
    runlock.release()
    assert runlock.acquire("a")["acquired"]
    assert not runlock.acquire("b")["acquired"]
    assert runlock.acquire("c", stale_hours=0)["acquired"]     # a stale lock is taken over
    assert runlock.release()["released"]


def test_search_plan_any_role_family():
    sys.path.insert(0, str(ROOT / "skills" / "job-ingest" / "scripts"))
    import search_plan as sp
    from lib import config_loader
    text = PLAN.replace("    delivery: {standing: false, places: [uk_remote], keywords: [project manager]}",
                        "    local: {standing: true, any_role: true, places: [london]}").replace(
        '      city: "https://www.reed.co.uk/jobs/{slug}-jobs-in-{city_slug}?salaryFrom={floor}"',
        '      city: "https://www.reed.co.uk/jobs/{slug}-jobs-in-{city_slug}?salaryFrom={floor}"\n'
        '      city_any: "https://www.reed.co.uk/jobs/jobs-in-{city_slug}?salaryFrom={floor}"')
    p = _use_sources(text)
    try:
        standing, _ = sp.build()
        local = [s for s in standing if s["family"] == "local"]
        assert len(local) == 1 and local[0]["keyword"] is None
        assert local[0]["url"].startswith("https://www.reed.co.uk/jobs/jobs-in-london?")
    finally:
        p.unlink()
        config_loader._load_cached.cache_clear()


def test_reed_url_never_bare():
    """Reed 404s on /jobs/<id> even for live adverts ; ingest must store a working form."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "job-ingest" / "scripts"))
    import normalize
    assert normalize._reed_url({"url": "https://www.reed.co.uk/jobs/90000701", "id": 90000701}) == "https://www.reed.co.uk/jobs/job/90000701"
    assert normalize._reed_url({"url": "", "id": 90000701}) == "https://www.reed.co.uk/jobs/job/90000701"
    assert normalize._reed_url({"url": "https://www.reed.co.uk/jobs/product-owner/90000702", "id": 90000702}).endswith("/product-owner/90000702")


def test_closing_dates_and_closed_gate():
    """Closing dates in long or numeric form are parsed; a vacancy that closes today is kept, one that
    closed yesterday is dropped, and a row with no closing date passes."""
    import sys
    import datetime
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "job-ingest" / "scripts"))
    import normalize
    import filters
    today = datetime.date(2026, 1, 15)
    assert normalize._long_date("Sunday 18 January 2026") == "2026-01-18"
    assert normalize._long_date("18 January 2026") == "2026-01-18"
    assert normalize._long_date("18/01/2026") == "2026-01-18"
    assert normalize._long_date("soon") is None
    assert filters.closed_gate({"closing_date": "2026-01-15"}, today)
    assert not filters.closed_gate({"closing_date": "2026-01-14"}, today)
    assert filters.closed_gate({"closing_date": None}, today)

def test_range_rule_bottom_requires_lowest_pay():
    cfg = {**CFG, "markets": {**CFG["markets"], "ie": {**CFG["markets"]["ie"], "salary_floor": 50000,
                                                       "salary_range_rule": "bottom"}}}
    ie = dict(source="linkedin", market="ie", location="Dublin", salary_currency="EUR", salary_period="annual")
    assert not filters.classify(job(salary_min=40000, salary_max=50000, **ie), cfg)["keep"]
    assert not filters.classify(job(salary_min=45000, salary_max=51000, **ie), cfg)["keep"]
    assert filters.classify(job(salary_min=50000, salary_max=60000, **ie), cfg)["keep"]
    assert filters.classify(job(salary_min=52000, salary_max=52000, **ie), cfg)["keep"]
    assert filters.classify(job(salary_min=None, salary_max=55000, **ie), cfg)["keep"]
    # the default rule still passes a range whose top reaches the floor
    top_cfg = {**CFG, "markets": {**CFG["markets"], "ie": {**CFG["markets"]["ie"], "salary_floor": 50000}}}
    assert filters.classify(job(salary_min=40000, salary_max=50000, **ie), top_cfg)["keep"]


def test_market_board_factor_overrides_plan_factor():
    import search_plan
    fc = {**CFG, "markets": {**CFG["markets"], "ie": {**CFG["markets"]["ie"], "salary_floor": 50000,
                                                      "board_salary_factor": 1.0}}}
    assert search_plan.board_floor("ie", 0.75, fc) == "50000"
    assert search_plan.board_floor("uk", 0.75, fc) == "22000"


def test_cv_library_relative_posted_and_miles_location():
    import datetime
    today = datetime.date(2026, 1, 15)
    c = {"id": "1", "title": "Product Owner", "company": "X", "location": "Leeds (5 miles)",
         "salary": "£50,000 - £60,000 per annum", "posted": "2 days ago"}
    j = norm.normalize("cv_library", c, today)
    assert j["date_posted"] == "2026-01-13"
    assert "miles" not in (j["location"] or "")
    c["posted"] = "yesterday"
    assert norm.normalize("cv_library", c, today)["date_posted"] == "2026-01-14"
    c["posted"] = "13/01/2026"
    assert norm.normalize("cv_library", c, today)["date_posted"] == "2026-01-13"


def test_all_flag_ignores_board_caps():
    import search_plan
    searches = [{"id": f"linkedin:x:{i}", "board": "linkedin", "rank": [0, 0, i]} for i in range(20)]
    plan = {"boards": {"linkedin": {"max_searches": 12}}}
    capped, deferred = search_plan.due(searches, plan, {}, request=True)
    assert len(capped) == 12 and len(deferred) == 8
    full, none_deferred = search_plan.due(searches, plan, {}, request=True, ignore_caps=True)
    assert len(full) == 20 and not none_deferred


def test_salary_period_aliases_are_understood():
    assert markets.period_key("monthly") == "month" and markets.period_key("daily") == "day"
    assert markets.period_key("per annum") == "annual" and markets.period_key(None) == "annual"
    cfg = {"default_market": "ie", "markets": {"ie": {"currency": "EUR", "salary_floor": 50000, "floor_period": "annual",
           "salary_range_rule": "bottom"}}}
    job = {"market": "ie", "salary_min": 5000, "salary_max": 6000, "salary_period": "monthly", "salary_currency": "EUR"}
    assert filters.salary_gate(job, cfg)[0] is True


def test_title_list_audit_finds_collisions_and_evidence():
    import audit_reject_titles as audit
    cfg = {"reject_title_contains": ["teacher", "recruitment"], "reject_title_word_boundary": [],
           "relevance": {"title_any": ["product manager"]}}

    def row(i, title, score, status="rejected", applied=None):
        return {"id": i, "title": title, "status": status, "match_score": score, "date_applied": applied}

    rows = [row(1, "Science Teacher", 20),
            row(2, "Senior Product Manager - Recruitment Platform", 77, "scored")]
    rows += [row(10 + i, "Financial Controller", 30) for i in range(8)]
    rows += [row(30 + i, "Payroll Analyst", 20) for i in range(8)]
    rows += [row(40, "Payroll Analyst", 62, "applied", "2026-01-15"),
             row(50, "Financial Controller", None, "found")]
    cards = [{"source": "x", "title": "Product Manager (Recruitment)"},
             {"source": "x", "title": "Recruitment Consultant"}]
    res = audit.audit(rows, cards, cfg, pos=50, min_reads=8)
    assert [c["entry"] for c in res["collisions"]] == ["recruitment"]
    blocked = {b["entry"]: b for b in res["blocked"]}
    assert blocked["recruitment"]["cards"] == 2 and blocked["recruitment"]["target_titles"] == 1
    terms = {c["term"]: c for c in res["candidates"]}
    assert terms["controller"]["unread_rows"] == 1 and terms["controller"]["best_score"] == 30
    assert "payroll analyst" not in terms and "analyst" not in terms and "payroll" not in terms


def test_reapply_title_list_drops_only_unread_rows(tmp_path):
    import reapply_title_list as reapply
    con = _db(tmp_path)
    for i, title in [(2, "Financial Controller"), (3, "Financial Controller")]:
        jobdb.insert_job(con, {"source": "reed", "job_id": str(i), "title": title, "company": f"Co {i}",
                               "location": "London"})
    jobdb.set_score(con, 3, 20, {"fit_score": 20}, status="rejected")
    rows = reapply.plan(con, {"reject_title_contains": ["controller"], "reject_title_word_boundary": []})
    assert [r[0] for r in rows] == [2]
    assert reapply.apply(con, rows, today="2026-01-15") == 1
    assert jobdb.get_by_id(con, 2)["status"] == "rejected"
    assert "reject-title list: title matches 'controller'" in jobdb.get_by_id(con, 2)["notes"]
    assert jobdb.unread_rejections(con) == []
    assert jobdb.get_by_id(con, 1)["status"] == "found"
