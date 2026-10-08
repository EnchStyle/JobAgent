#!/usr/bin/env python3
"""workflow_check.py : the candidate's own workflow rules on a CV or cover letter (cv-verify Gate B, cover-letter).

Deterministic checks for the rules uk-cv-writer does not know about, read from
config/application_rules.md:
  - dashes        em dash anywhere = FAIL; an en dash outside a date range = WARN
  - never_mention every term in the never_mention list (a past employer you leave out, named
                  people, "References available on request") = FAIL, or CHECK when the line looks
                  like a publication citation (a co-author name there is allowed)
  - contact       an email other than the configured one = FAIL; a phone from the wrong market = FAIL
  - employer_rules (CVs, optional) for each configured employer: a line matching one of its
                  forbidden_lines patterns = FAIL; a founder or CEO title next to that employer =
                  CHECK (right only for founder or C-level postings)

Usage:
  python3 skills/cv-verify/scripts/workflow_check.py <file.docx|.md|.txt> [--market <code>] [--kind cv|letter]
(<code> is a market from config/filters.md, for example uk or ie)
Prints JSON {verdict, fails, checks, warns, items[]}. verdict is "fail" when any FAIL exists,
"check" when only CHECK items need a judgement, else "pass". Exit code is always 0.
"""
import re
import sys
import json
import zipfile
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import config_loader  # noqa: E402

EM, EN = "—", "–"
CITATION = re.compile(r"et al\.?|doi|\((19|20)\d\d\)|\b(19|20)\d\d[;,.]\s*\d+|journal|vol\.", re.I)


def read_lines(path):
    p = Path(path)
    if p.suffix.lower() == ".docx" or zipfile.is_zipfile(str(p)):
        from docx import Document
        return [x.text for x in Document(str(p)).paragraphs if x.text.strip()]
    return [l for l in p.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]


def rules():
    try:
        r = config_loader.application_rules() or {}
    except Exception:
        r = {}
    c = config_loader.contact()
    return {
        "email": c["email"] or "you@example.com",
        "phones": c["phones"],
        "never": r.get("never_mention") or [],
        "employers": r.get("employer_rules") or [],
    }


def term_regex(term):
    t = re.escape(term.strip())
    single_word = re.fullmatch(r"[A-Z][a-z]+", term.strip()) is not None
    return re.compile(r"(?<!\w)" + t + (r"(?!\w)" if single_word else ""), re.I)


def digits(s):
    return re.sub(r"\D", "", s or "")


def check(path, market=None, kind=None):
    lines = read_lines(path)
    text = "\n".join(lines)
    kind = kind or ("cv" if Path(path).suffix.lower() == ".docx" and "cv" in Path(path).name.lower() else "letter")
    R = rules()
    items = []

    def add(level, name, detail):
        items.append({"level": level, "check": name, "detail": detail})

    # dashes
    em = [l for l in lines if EM in l]
    for l in em[:6]:
        add("FAIL", "em dash", l.strip()[:140])
    prose_en = []
    for l in lines:
        for m in re.finditer(EN, l):
            left, right = l[max(0, m.start() - 14):m.start()], l[m.end():m.end() + 14]
            if re.search(r"\d", left) or re.search(r"\d|present|heute|today", right, re.I):
                continue
            prose_en.append(l.strip()[:140])
    for l in prose_en[:6]:
        add("WARN", "en dash used as punctuation", l)

    # never-mention terms
    for term in R["never"]:
        rx = term_regex(term)
        for l in lines:
            if rx.search(l):
                level = "CHECK" if CITATION.search(l) else "FAIL"
                add(level, f"never mention: {term}",
                    ("inside what looks like a citation (fine only as a co-author name): " if level == "CHECK" else "")
                    + l.strip()[:160])

    # contact details
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)))
    bad = [e for e in emails if e.lower() != R["email"].lower()]
    for e in bad:
        add("FAIL", "contact email", f"{e} found; use {R['email']}")
    if kind == "cv" and not emails:
        add("WARN", "contact email", f"no email found; the CV should carry {R['email']}")
    # Any phone-like run of digits (international or national format).
    phones = set(re.findall(r"(?:\+|\b0)\d[\d ()-]{6,16}\d", text))
    pd = {digits(p) for p in phones}
    if not market:
        add("WARN", "phone", "no --market given, so the phone was not checked against the market")
    else:
        mine = R["phones"].get(market)
        if not mine:
            add("WARN", "phone", f"no phone configured for market '{market}' in contact.phones")
        elif kind == "cv" and digits(mine) not in pd:
            add("WARN", "phone", f"the {market} phone {mine} is not on the CV")
        for other, num in R["phones"].items():
            if other != market and digits(num) and digits(num) in pd:
                add("FAIL", "phone", f"the {other} number is on a {market} application"
                    + (f"; use {mine}" if mine else ""))

    # employer rules (CVs): how a configured past employer may and may not appear
    if kind == "cv":
        for rule in R["employers"]:
            emp = (rule or {}).get("name") or ""
            for fl in (rule or {}).get("forbidden_lines") or []:
                rx = re.compile(fl.get("pattern", "$^"), re.I)
                for l in lines:
                    if rx.search(l):
                        add("FAIL", f"employer rule: {emp}",
                            (fl.get("message") or "forbidden line") + ": " + l.strip()[:120])
            titles = (rule or {}).get("founder_titles_need_reason") or []
            if emp and titles:
                title_rx = re.compile(r"\b(" + "|".join(re.escape(x) for x in titles) + r")\b", re.I)
                for i, l in enumerate(lines):
                    if title_rx.search(l) and len(l) < 90 and emp.lower() in " ".join(lines[i:i + 2]).lower():
                        add("CHECK", f"employer title: {emp}",
                            "founder or CEO title: right only for a founder or C-level posting: " + l.strip()[:100])

    fails = sum(1 for x in items if x["level"] == "FAIL")
    checks = sum(1 for x in items if x["level"] == "CHECK")
    warns = sum(1 for x in items if x["level"] == "WARN")
    return {"file": str(path), "kind": kind, "market": market,
            "verdict": "fail" if fails else ("check" if checks else "pass"),
            "fails": fails, "checks": checks, "warns": warns, "items": items}


def main(argv=None):
    ap = argparse.ArgumentParser(description="The candidate's workflow rules on a CV or cover letter.")
    ap.add_argument("file")
    ap.add_argument("--market", default=None, help="market code from config/filters.md, e.g. uk or ie")
    ap.add_argument("--kind", choices=["cv", "letter"], default=None)
    a = ap.parse_args(argv)
    try:
        out = check(a.file, a.market, a.kind)
    except Exception as exc:  # fail closed: a file that cannot be read is never reported clean
        out = {"file": a.file, "verdict": "fail", "fails": 1, "checks": 0, "warns": 0,
               "items": [{"level": "FAIL", "check": "read", "detail": f"{type(exc).__name__}: {exc}"}]}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
