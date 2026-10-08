"""Hard filters applied BEFORE scoring. Salary, location, freshness, reject-title.

A role must pass every gate to be kept. Salary and location outcomes can be PASS, REVIEW
(kept but flagged for a manual check), or REJECT. Values come from config/filters.md.
"""
import sys
import re
import json
import argparse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import config_loader, markets as mk



def _cfg():
    return config_loader.filters()


def salary_gate(job, cfg):
    """Return (ok, reason, flag_unknown).

    The floor comes from the job's market in config/filters.md (markets.<code>.salary_floor,
    quoted per floor_period), optionally replaced per source (salary_floor_by_source) and raised
    for onsite or hybrid roles in an allowed place (location_allow[].office_floor or
    office_floor). Which end of a stated range is compared is the market's `salary_range_rule`:
    `top` (default) compares the top, `bottom` the lowest pay offered. A missing salary, or one in a
    different currency from the market's, is never a rejection: it is kept and flagged."""
    if job.get("salary_unknown") or (job.get("salary_min") is None and job.get("salary_max") is None):
        return True, "salary_unknown", True
    ms = mk.markets(cfg)
    m = ms.get(job.get("market")) or ms.get(mk.default_market(cfg)) or {}
    cur = (job.get("salary_currency") or "").upper()
    if m.get("currency") and cur and cur != str(m["currency"]).upper():
        return True, "salary_other_currency", True
    floor = m.get("salary_floor")
    by_source = m.get("salary_floor_by_source") or {}
    if job.get("source") in by_source:
        floor = by_source[job["source"]]
    if not floor:
        return True, "salary_ok", False
    per = mk.period_key(m.get("floor_period"))
    floor_annual = float(floor) * mk.PERIOD_TO_ANNUAL.get(per, 1)
    place = _office_place(job, cfg)
    if place:
        extra = place.get("office_floor")
        if extra:
            floor_annual = max(floor_annual, float(extra) * mk.PERIOD_TO_ANNUAL.get(per, 1))
    rule = str(m.get("salary_range_rule") or "top").lower()
    if rule == "bottom":
        top = job.get("salary_min") if job.get("salary_min") is not None else job.get("salary_max")
    else:
        top = job.get("salary_max") or job.get("salary_min")
    jper = mk.period_key(job.get("salary_period") or m.get("default_salary_period"))
    if top is not None and float(top) * mk.PERIOD_TO_ANNUAL.get(jper, 1) < floor_annual:
        return False, f"below_{job.get('market', 'market')}_floor", False
    return True, "salary_ok", False


_COUNTRY_ALIASES = {"gb": "uk", "united kingdom": "uk", "great britain": "uk"}


_WARNED = set()


def _market_of_country(value, cfg):
    """A location_allow country: a market code (uk), its label (UK, Germany) or a known alias."""
    v = str(value or "").lower()
    v = _COUNTRY_ALIASES.get(v, v)
    ms = mk.markets(cfg)
    if v in ms:
        return v
    for code, m in ms.items():
        if str(m.get("label", "")).lower() == v:
            return code
    if v and v not in _WARNED:
        _WARNED.add(v)
        print(f"[filters] location_allow country '{value}' matches no market in config/filters.md; "
              "that entry is ignored", file=sys.stderr)
    return None


def _allowed_places(cfg, market):
    """Entries of location_allow for this market. Each entry: place, country (a market code such
    as UK or IE), modes, and optionally match (list of lower-case substrings; defaults to the place
    name), match_regex (list of regular expressions, for postcodes) and office_floor (in the
    market's floor_period). Entries whose
    modes are only [remote] are ignored here: remote roles pass everywhere unless flagged foreign."""
    out = []
    for e in cfg.get("location_allow", []) or []:
        if _market_of_country(e.get("country"), cfg) != market:
            continue
        modes = [m.lower() for m in (e.get("modes") or ["onsite", "hybrid", "remote"])]
        if not ({"onsite", "hybrid"} & set(modes)):
            continue
        terms = [m.lower() for m in (e.get("match") or [str(e.get("place", "")).lower()]) if m]
        regexes = [re.compile(r, re.I) for r in (e.get("match_regex") or [])]
        out.append(dict(e, _terms=terms, _regexes=regexes))
    return out


def _office_place(job, cfg):
    """The allowed place a non-remote job sits in, or None."""
    text = (job.get("location") or "").lower()
    if (job.get("work_mode") or "").lower() == "remote" or "remote" in text:
        return None
    for e in _allowed_places(cfg, job.get("market") or mk.default_market(cfg)):
        if any(mk.hint_match(term, text) for term in e["_terms"]) or any(rx.search(text) for rx in e["_regexes"]):
            return e
    return None


def location_gate(job, cfg):
    """Return (decision, reason) where decision is pass, review, or reject.
    Remote roles pass. Onsite or hybrid roles pass only in a place listed under location_allow
    in config/filters.md."""
    text = (job.get("location") or "").lower()
    wm = (job.get("work_mode") or "").lower()
    market = job.get("market") or mk.default_market(cfg)
    remote_hints = [h.lower() for h in cfg.get("remote_hints", [])]
    is_remote = wm == "remote" or any(h in text for h in remote_hints)
    foreign = mk.foreign_location(job.get("location"), cfg)
    if is_remote:
        if foreign:
            return "review", "remote_foreign_location"
        return "pass", "remote"
    if foreign:
        # Onsite or hybrid in a country outside your markets (checked before location_allow, so
        # "Berlin, Connecticut, United States" never passes as Berlin).
        return "reject", "onsite_abroad"
    for e in _allowed_places(cfg, market):
        if any(mk.hint_match(term, text) for term in e["_terms"]) or any(rx.search(text) for rx in e["_regexes"]):
            return "pass", str(e.get("place", "allowed_place")).lower()
    m = mk.markets(cfg).get(market) or {}
    generic = m.get("generic_location_terms") or []
    if generic and (text.strip() == "" or any(g in text for g in generic)):
        return "review", f"{market}_generic"
    if str(m.get("unlisted_onsite", "review")).lower() == "reject":
        return "reject", f"{market}_other_city_onsite"
    # List pages often do not show remote status (it lives in the description), so by default a
    # role is NOT rejected on its city alone: it is kept and flagged for a remote check, and the
    # advert is read before it is scored.
    return "review", f"verify_remote_{market}"


def freshness_gate(job, cfg, today=None):
    """Posted within max_days_old of `today` (the scrape date; defaults to the real today)."""
    maxd = cfg.get("freshness", {}).get("max_days_old", 14)
    df = job.get("date_posted") or job.get("date_found")
    if not df:
        return True
    try:
        d = date.fromisoformat(df[:10])
        return ((today or date.today()) - d).days <= maxd
    except Exception:
        return True


def closed_gate(job, today=None):
    """False when the card carries a closing date that has already passed (the closing day itself is
    still open). Cards from boards without a closing date always pass."""
    cd = job.get("closing_date")
    if not cd:
        return True
    try:
        return date.fromisoformat(str(cd)[:10]) >= (today or date.today())
    except Exception:
        return True


def reject_title(title, cfg):
    """Substring match by default, so a word stem also catches inflected forms (useful for
    inflected languages). Keywords listed in reject_title_word_boundary are
    matched as whole words instead, so short English words cannot fire inside a longer one
    (otherwise 'intern' drops 'Head of International Product')."""
    low = (title or "").lower()
    wb = set(k.lower() for k in cfg.get("reject_title_word_boundary", []))
    for kw in cfg.get("reject_title_contains", []):
        if not kw:
            continue
        k = kw.lower()
        if k in wb:
            if re.search(r"\b" + re.escape(k) + r"\b", low):
                return True, kw
        elif k in low:
            return True, kw
    return False, None


def is_relevant(title, keys):
    low = (title or "").lower()
    return any(k and k.lower() in low for k in (keys or []))


def classify(job, cfg=None, today=None):
    cfg = cfg or _cfg()
    rj, kw = reject_title(job.get("title"), cfg)
    if rj:
        return {"keep": False, "review": False, "reason": "reject_title:" + str(kw)}
    rel = cfg.get("relevance", {})
    if rel.get("require") and not is_relevant(job.get("title"), rel.get("title_any", [])):
        return {"keep": False, "review": False, "reason": "not_relevant"}
    if not freshness_gate(job, cfg, today):
        return {"keep": False, "review": False, "reason": "stale"}
    if not closed_gate(job, today):
        return {"keep": False, "review": False, "reason": "expired"}
    loc_dec, loc_reason = location_gate(job, cfg)
    if loc_dec == "reject":
        return {"keep": False, "review": False, "reason": "location:" + loc_reason}
    sal_ok, sal_reason, sal_flag = salary_gate(job, cfg)
    if not sal_ok:
        return {"keep": False, "review": False, "reason": "salary:" + sal_reason}
    flags = []
    if loc_dec == "review":
        flags.append("verify_right_to_work" if loc_reason == "remote_foreign_location" else "verify_location")
    other_currency = sal_reason == "salary_other_currency"
    if sal_flag:
        flags.append("salary_other_currency" if other_currency else "salary_unknown")
    wm = job.get("work_mode")
    if loc_reason in ("remote", "remote_foreign_location") and not wm:
        wm = "remote"
    return {
        "keep": True,
        "review": loc_dec == "review" or sal_flag,
        "reason": "pass",
        "flags": flags,
        "salary_unknown": 1 if (sal_flag and not other_currency) else int(job.get("salary_unknown", 0) or 0),
        "work_mode": wm,
        "location_status": loc_dec,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True, help="json file: list of job dicts")
    args = ap.parse_args()
    cfg = _cfg()
    jobs = json.load(open(args.jobs, encoding="utf-8"))
    kept = review = rej = 0
    reasons = {}
    for j in jobs:
        r = classify(j, cfg)
        if r["keep"]:
            kept += 1
            if r["review"]:
                review += 1
        else:
            rej += 1
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    print(json.dumps({"total": len(jobs), "kept": kept, "review": review,
                      "rejected": rej, "reject_reasons": reasons}, indent=2))


if __name__ == "__main__":
    main()
