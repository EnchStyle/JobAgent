"""Normalize scraped job cards (from the per-site JS extractors) into job dicts.

Input shapes:
  cv_library: {id,url,title,company,location,salary("£55,000 - £65,000 per annum"),posted("DD/MM/YYYY"),easyApply}
  reed(web):  {id,url,title,company,location,salary("£45,000 - £55,000 per annum"),posted("15 June"),remote("remote"|"hybrid")}
  linkedin:   [id,title,company,location,salary,posted("3 days ago")] or the same keys as a dict
  indeed:     {id,title,company,location,salary,posted,remote}
Output: a job dict for filters.classify and jobdb.insert_job.

Adding a board: write scrapers/<source>.js, add normalize_<source>() below, and register it in
NORMALIZERS and URL_BASE. The market of each job is resolved in normalize() from the location
text and config (lib/markets.py), so a normaliser only needs a sensible default.
"""
import re
import sys
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import markets as mk  # noqa: E402


def parse_salary_gbp(text):
    if not text:
        return {}
    t = re.sub(r"\bGBP\s*", "£", text).replace(",", "")
    # Accepts a "k" suffix (GBP 80K -> 80000) and a second range figure written without its
    # own pound sign (GBP 450 - 600pd).
    nums = []
    for m in re.finditer(r"£\s*(\d+(?:\.\d+)?)\s*([kK])?(?:\s*(?:-|–|to)\s*£?\s*(\d+(?:\.\d+)?)\s*([kK])?)?", t):
        a = float(m.group(1)) * (1000 if m.group(2) else 1)
        nums.append(a)
        if m.group(3):
            b = float(m.group(3)) * (1000 if (m.group(4) or (m.group(2) and float(m.group(3)) < 1000)) else 1)
            nums.append(b)
        if len(nums) >= 2:
            break
    if not nums:
        return {}
    period = "annual"
    if re.search(r"per day|/day|a day|\dpd\b|\bpd\b|p/d|per diem|daily rate", t, re.I):
        period = "day"
    elif re.search(r"per hour|/hour|an hour|/hr", t, re.I):
        period = "hour"
    elif re.search(r"per week|/week", t, re.I):
        period = "week"
    elif re.search(r"per month|/month|pcm", t, re.I):
        period = "month"
    # Boards sometimes label a day rate "per annum" (e.g. "GBP 600 - 650 per annum"). No UK salary is
    # under GBP 1,500 a year, so treat such figures as a day rate rather than rejecting them.
    if period == "annual" and max(nums[:2]) < 1500:
        period = "day"
    return {"salary_min": nums[0], "salary_max": (nums[1] if len(nums) > 1 else None),
            "salary_currency": "GBP", "salary_period": period}


_CURRENCIES = [
    ("GBP", r"£|\bGBP\b"), ("EUR", r"€|\bEUR\b|\beuro?s?\b"), ("USD", r"US\$|\$|\bUSD\b"),
    ("CHF", r"\bCHF\b"), ("PLN", r"zł|\bPLN\b"), ("SEK", r"\bSEK\b"), ("NOK", r"\bNOK\b"),
    ("DKK", r"\bDKK\b"), ("CAD", r"\bCAD\b|C\$"), ("AUD", r"\bAUD\b|A\$"),
]
_PERIODS = [
    ("hour", r"per hour|/\s*h(ou)?r\b|an hour|hourly|/\s*h\b|pro stunde|/\s*std|stündlich"),
    ("day", r"per day|/\s*day|a day|daily|\bpd\b|p/d|per diem|pro tag|/\s*d\b"),
    ("week", r"per week|/\s*w(ee)?k|weekly|pro woche"),
    ("month", r"per month|/\s*mo(nth)?\b|monthly|\bpcm\b|pro monat|/\s*monat|monatlich|brutto/monat"),
    ("annual", r"per (annum|year)|/\s*y(ea)?r\b|\bp\.?a\.?\b|annual|yearly|pro jahr|/\s*jahr|jährlich"),
]


def _to_number(tok):
    """'60.000' -> 60000, '60,000' -> 60000, '45 000' -> 45000, '1,1' -> 1.1, '55.5' -> 55.5."""
    s = tok.strip().replace("\u00a0", " ").replace(" ", "")
    if "." in s and "," in s:
        dec = "." if s.rfind(".") > s.rfind(",") else ","
        s = s.replace("," if dec == "." else ".", "").replace(dec, ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        parts = s.split(sep)
        if all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
            s = "".join(parts)          # thousands separators
        else:
            s = s.replace(",", ".")     # decimal separator
    try:
        return float(s)
    except ValueError:
        return None


def parse_salary_any(text, default_currency=None, default_period=None):
    """Currency- and locale-aware salary parser for boards outside the UK.
    Handles '60.000 € pro Jahr', '$150,000/yr', 'EUR 3,500 per month', 'CHF 120k'. A pound
    amount is passed to parse_salary_gbp, which knows UK board quirks."""
    if not text:
        return {}
    if re.search(r"£|\bGBP\b", text):
        return parse_salary_gbp(text)
    cur = next((code for code, rx in _CURRENCIES if re.search(rx, text, re.I)), default_currency)
    num = r"(\d[\d.,\u00a0 ]*\d|\d)\s*([kK]\b)?"

    def value(m, i):
        n = _to_number(m.group(i))
        if n is not None and m.group(i + 1):
            n *= 1000
        return n

    # The first amount, and a second one only when a range word or sign joins them
    # ("55.000 - 65.000", "55k to 65k", "45 000 – 55 000"). Anything later in the text
    # ("+ 10% bonus", "40 Std./Woche", "30 days holiday") is ignored.
    nums = []
    m = re.search(num + r"(?:\s*[€$£]?\s*(?:-|\u2013|\u2014|to|bis)\s*(?:[€$£]|[A-Z]{3})?\s*" + num + r")?", text)
    if m:
        a = value(m, 1)
        if a is not None:
            nums.append(a)
            b = value(m, 3) if m.group(3) else None
            if b is not None and m.group(2) and not m.group(4) and b < 1000:
                b *= 1000  # "55k - 65" means 55k to 65k
            if b is not None and b >= a:
                nums.append(b)
    if not nums or not cur:
        return {}
    # No period in the text: leave it empty so the filter uses the market's default_salary_period.
    period = next((name for name, rx in _PERIODS if re.search(rx, text, re.I)), default_period)
    return {"salary_min": nums[0], "salary_max": (nums[1] if len(nums) > 1 else None),
            "salary_currency": cur, "salary_period": period}


def uk_date(text):
    if not text:
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def _remote_words():
    """remote_hints from config/filters.md plus a few built-in words in common languages."""
    words = ["remote", "wfh", "work from home", "homeoffice", "home office", "télétravail"]
    try:
        from lib import config_loader
        words += [str(w).lower() for w in (config_loader.filters().get("remote_hints") or [])]
    except Exception:
        pass
    return words


def _work_mode(text):
    low = (text or "").lower()
    if any(w in low for w in _remote_words()):
        return "remote"
    if any(w in low for w in ["hybrid"]):
        return "hybrid"
    return None


URL_BASE = {"cv_library": "https://www.cv-library.co.uk/job/", "reed": "https://www.reed.co.uk/jobs/job/", "linkedin": "https://www.linkedin.com/jobs/view/", "indeed": "https://uk.indeed.com/viewjob?jk="}


def _clean_location(loc):
    if not loc:
        return loc
    loc = re.sub(r"\(\s*\d+\s*miles?(\s*away)?\s*\)", "", loc, flags=re.I)
    loc = loc.replace("Also in other locations", "")
    return re.sub(r"\s+", " ", loc).strip(" ,") or None


def normalize_cv_library(c, today=None):
    loc = _clean_location(c.get("location"))
    job = dict(source="cv_library", market="uk", job_id=str(c.get("id")), title=c.get("title"),
               company=c.get("company"), location=loc,
               work_mode=_work_mode((loc or "") + " " + (c.get("title") or "")), url=c.get("url") or (URL_BASE["cv_library"] + str(c.get("id"))),
               date_posted=uk_date(c.get("posted")) or linkedin_relative_date(c.get("posted"), today),
               date_found=(today or datetime.date.today()).isoformat(),
               notes=("easy_apply" if c.get("easyApply") else None), description=None)
    sal = parse_salary_gbp(c.get("salary"))
    job.update(sal)
    job["salary_unknown"] = 0 if sal else 1
    return job


_REED_MONTHS = {}
for _i, _m in enumerate(["january","february","march","april","may","june","july","august","september","october","november","december"], 1):
    _REED_MONTHS[_m] = _i
    _REED_MONTHS[_m[:3]] = _i


def reed_web_date(text, today=None):
    today = today or datetime.date.today()
    if not text:
        return None
    m = re.match(r"(\d{1,2})\s+(\w+)", text.strip())
    if not m:
        return None
    day = int(m.group(1))
    mon = _REED_MONTHS.get(m.group(2).lower()) or _REED_MONTHS.get(m.group(2)[:3].lower())
    if not mon:
        return None
    try:
        d = datetime.date(today.year, mon, day)
        if d > today:
            d = datetime.date(today.year - 1, mon, day)
        return d.isoformat()
    except ValueError:
        return None


def _reed_url(c):
    """Reed answers 404 to /jobs/<id> even for live adverts; /jobs/job/<id> always resolves."""
    url = c.get("url") or ""
    m = re.match(r"https?://www\.reed\.co\.uk/jobs/(\d+)/?(?:\?.*)?$", url)
    if m:
        return URL_BASE["reed"] + m.group(1)
    return url or (URL_BASE["reed"] + str(c.get("id")))


def normalize_reed(c, today=None):
    """Reed is scraped from its website only (remote-filtered search); there is no API path."""
    loc = c.get("location")
    rmode = (c.get("remote") or "").lower()
    wm = "remote" if rmode == "remote" else ("hybrid" if rmode == "hybrid" else _work_mode((loc or "") + " " + (c.get("title") or "")))
    job = dict(source="reed", market="uk", job_id=str(c.get("id")), title=c.get("title"),
               company=c.get("company"), location=loc, work_mode=wm,
               url=_reed_url(c),
               date_posted=reed_web_date(c.get("posted"), today),
               date_found=(today or datetime.date.today()).isoformat(), description=None, notes=None)
    sal = parse_salary_gbp(c.get("salary"))
    job.update(sal)
    job["salary_unknown"] = 0 if sal else 1
    return job


_REL_UNITS = [  # (pattern, days per unit): English, German, French
    (r"minute|minut|stunde|hour|heure", 0), (r"day|tag|jour", 1),
    (r"week|woche|semaine", 7), (r"month|monat|mois", 30),
]


def linkedin_relative_date(text, today=None):
    """Posted date from a card: an ISO date (LinkedIn's <time datetime>), or a relative age in
    English, German or French ('3 days ago', 'vor 2 Wochen', 'il y a 5 jours')."""
    today = today or datetime.date.today()
    if not text:
        return None
    t = text.lower().strip()
    if "yesterday" in t:
        return (today - datetime.timedelta(days=1)).isoformat()
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
    m = re.search(r"(\d+)\+?\s*([^\W\d_]+)", t)
    if not m:
        return today.isoformat() if any(w in t for w in ("just now", "today", "heute", "aujourd", "just posted")) else None
    n, word = int(m.group(1)), m.group(2)
    per = next((d for rx, d in _REL_UNITS if re.match(rx, word)), None)
    if per is None:
        return None
    days = per * n
    return (today - datetime.timedelta(days=days)).isoformat()


LINKEDIN_ARRAY_KEYS = ("id", "title", "company", "location", "salary", "posted")


def normalize_linkedin(c, today=None):
    """LinkedIn job cards. Salary is usually absent, so most rows carry salary_unknown = 1
    and are kept for a manual check, exactly as the filters.md rule requires. linkedin.js
    stores compact arrays [id, title, company, location, salary, posted]; both arrays and
    dicts are accepted."""
    if isinstance(c, (list, tuple)):
        c = dict(zip(LINKEDIN_ARRAY_KEYS, c))
    loc = _clean_location(c.get("location") or "")
    market = "uk"  # default only; normalize() resolves the real market from the location
    rmode = (c.get("remote") or "").lower()
    wm = rmode if rmode in ("remote", "hybrid", "onsite") else _work_mode((loc or "") + " " + (c.get("title") or ""))
    job = dict(source="linkedin", market=market, job_id=str(c.get("id")), title=c.get("title"),
               company=c.get("company"), location=loc, work_mode=wm,
               url=c.get("url") or (URL_BASE["linkedin"] + str(c.get("id"))),
               date_posted=linkedin_relative_date(c.get("posted"), today),
               date_found=(today or datetime.date.today()).isoformat(),
               notes=("easy_apply" if c.get("easyApply") else None), description=None)
    sal = parse_salary_any(c.get("salary"))
    job.update(sal)
    job["salary_unknown"] = 0 if sal else 1
    return job


def normalize_indeed(c, today=None):
    """Indeed (read-only, low volume). Searches use fromage=14, so every card is inside the
    freshness window; the card's relative age is parsed when shown (same format as LinkedIn)."""
    loc = c.get("location")
    rmode = (c.get("remote") or "").lower()
    wm = rmode if rmode in ("remote", "hybrid", "onsite") else _work_mode((loc or "") + " " + (c.get("title") or ""))
    market = "uk"  # default only; normalize() resolves the real market from the location
    job = dict(source="indeed", market=market, job_id=str(c.get("id")), title=c.get("title"),
               company=c.get("company"), location=loc, work_mode=wm,
               url=c.get("url") or (_url_base("indeed") + str(c.get("id"))),
               date_posted=linkedin_relative_date(c.get("posted"), today),
               date_found=(today or datetime.date.today()).isoformat(), description=None,
               notes=("easy_apply" if c.get("easyApply") else None))
    sal = parse_salary_any(c.get("salary"))
    job.update(sal)
    job["salary_unknown"] = 0 if sal else 1
    return job


def _long_date(text):
    """'Sunday 18 January 2026', '18 January 2026' or '18/01/2026' -> '2026-01-18'; None when not a date."""
    t = (text or "").strip()
    for fmt in ("%A %d %B %Y", "%d %B %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    return None


NORMALIZERS = {"cv_library": normalize_cv_library, "reed": normalize_reed,
               "linkedin": normalize_linkedin, "indeed": normalize_indeed}


def _url_base(source):
    """Listing URL prefix for a source: scrape_sources.<source>.url_base in config/sources.md,
    else the built-in default (for example a different Indeed country domain)."""
    try:
        from lib import config_loader
        v = ((config_loader.sources() or {}).get("scrape_sources", {}).get(source) or {}).get("url_base")
        if v:
            return v
    except Exception:
        pass
    return URL_BASE.get(source, "")


def normalize(source, card, today=None):
    """Normalise one card and resolve its market (config/filters.md markets, then the source's
    market in config/sources.md). Raises ValueError for a source with no normaliser; the ingest
    report counts those under reject_reasons as no_normalizer:<source>."""
    fn = NORMALIZERS.get(source)
    if not fn:
        raise ValueError("no normalizer for " + str(source))
    job = fn(card, today)
    try:
        job["market"] = mk.market_for(source, job.get("location"))
    except Exception:
        pass  # keep the normaliser's default if config cannot be read
    return job
