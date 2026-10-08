"""Job markets (countries) as configuration.

A market groups the rules that differ by country: the currency, the salary floor and the period
it is quoted in, the place names that identify the country in a listing, and how an onsite role
outside the allowed places is treated. Markets are defined in the `markets` block of
config/filters.md; each scrape source in config/sources.md names its default market.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import config_loader  # noqa: E402

# Multipliers that turn a salary in a given period into an annual figure.
PERIOD_TO_ANNUAL = {"annual": 1, "year": 1, "month": 12, "week": 52, "day": 260, "hour": 1800}
_PERIOD_ALIASES = {"yearly": "annual", "annum": "annual", "per annum": "annual", "pa": "annual", "monthly": "month", "weekly": "week",
                   "daily": "day", "hourly": "hour"}


def period_key(value, default="annual"):
    """A salary period as one of the PERIOD_TO_ANNUAL keys; aliases such as monthly, daily or per annum are mapped
    (a stored 'monthly' used to be read as a yearly figure)."""
    v = str(value or default).strip().lower()
    return _PERIOD_ALIASES.get(v, v)


def markets(cfg=None):
    """code -> market settings, from config/filters.md."""
    cfg = cfg if cfg is not None else config_loader.filters()
    m = cfg.get("markets")
    out = {}
    if not m:
        sys.exit("config/filters.md has no `markets` block; copy it from config/filters.example.md")
    for code, v in m.items():
        v = dict(v or {})
        v["code"] = str(code).lower()
        v.setdefault("label", str(code).upper())
        v["location_hints"] = [str(h).lower() for h in (v.get("location_hints") or [])]
        v["generic_location_terms"] = [str(h).lower() for h in (v.get("generic_location_terms") or [])]
        v.setdefault("unlisted_onsite", "review")
        v.setdefault("floor_period", "annual")
        v.setdefault("default_salary_period", v["floor_period"])
        v.setdefault("salary_floor_by_source", {})
        # Which end of a stated pay range must reach the floor: "top" (the default; a 40k to 50k ad
        # passes a 40k floor) or "bottom" (the lowest pay offered must reach it).
        v["salary_range_rule"] = str(v.get("salary_range_rule") or "top").lower()
        # Optional per-market board filter factor; None means use search_plan.board_salary_factor.
        v.setdefault("board_salary_factor", None)
        out[v["code"]] = v
    return out


def default_market(cfg=None):
    cfg = cfg if cfg is not None else config_loader.filters()
    ms = markets(cfg)
    d = str(cfg.get("default_market") or "").lower()
    return d if d in ms else (next(iter(ms)) if ms else "uk")


def source_market(source):
    """The market a scrape source is configured for in config/sources.md, or None."""
    try:
        srcs = (config_loader.sources() or {}).get("scrape_sources", {}) or {}
        v = (srcs.get(source) or {}).get("market")
        return str(v).lower() if v else None
    except Exception:
        return None


def hint_match(hint, text):
    """True when a place hint occurs in lower-case location text. A plain hint matches at the
    start of a word, so stems work ("manch" matches "Manchester") but "uk" does not match inside
    "Lukas". A hint written as "re:<pattern>" is a regular expression, for example "re:\\buk\\b"
    so that "uk" never matches "Ukraine"."""
    h = str(hint or "").lower()
    if not h:
        return False
    if h.startswith("re:"):
        return re.search(h[3:], text) is not None
    if not h[0].isalnum():
        return h in text
    return re.search(r"(?<![a-z0-9])" + re.escape(h), text) is not None


def market_for(source, location, cfg=None):
    """Market of one listing: a market whose place names appear in the location text wins; then
    the source's configured market; then default_market."""
    cfg = cfg if cfg is not None else config_loader.filters()
    text = (location or "").lower()
    ms = markets(cfg)
    configured = source_market(source)
    # The source's own market is checked first so a shared place name cannot pull a listing away.
    order = ([configured] if configured in ms else []) + [c for c in ms if c != configured]
    for code in order:
        if any(hint_match(h, text) for h in ms[code]["location_hints"]):
            return code
    return configured if configured in ms else default_market(cfg)


def foreign_location(location, cfg=None):
    """True when the location text names a place listed in foreign_location_hints (places outside
    every market you search, for example other countries)."""
    cfg = cfg if cfg is not None else config_loader.filters()
    text = (location or "").lower()
    hints = [str(h).lower() for h in (cfg.get("foreign_location_hints") or [])]
    # A place that also identifies one of your markets is never foreign (for example when a new
    # market is added but its country is still in foreign_location_hints).
    own = [h for m in markets(cfg).values() for h in m["location_hints"]]
    if any(hint_match(h, text) for h in own):
        return False  # the text names one of your markets ("Northern Ireland, United Kingdom")
    return any(hint_match(h if h.startswith("re:") else "re:(?<![a-z])" + re.escape(h) + "(?![a-z])", text)
               for h in hints if h)


def label(code, cfg=None):
    m = markets(cfg).get(str(code or "").lower())
    return m["label"] if m else "Other"
