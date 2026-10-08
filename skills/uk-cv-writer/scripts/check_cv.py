#!/usr/bin/env python3
"""
check_cv.py - Verify a generated CV is ATS-safe, UK-compliant, and well laid out.

Run this after build_cv.py as the final QA gate. It does NOT judge writing
quality; it checks the objective, mechanical properties that make or break ATS
parsing, UK compliance, and a clean professional layout:

  1. Structure: no tables, no header/footer content, no images, single column.
  2. Standard section headings present (so ATS classifies content correctly).
  3. Linear text-extraction preview (what the ATS and the 7-second skim see).
  4. Page count + balance (rendered via LibreOffice) - target is a FULL 2 pages.
  5. Line-break quality: no 1-2 word "widow" lines stranded at the end of bullets.
  6. Prohibited UK personal data (DOB, marital status, nationality, NI no., etc.).
  7. US-spelling flags for a British-English pass.
  8. Optional: keyword coverage against a job description's must-have terms.
  9. Employment timeline: no dropped current role, no unexplained gaps.

Usage:
    python check_cv.py cv.docx
    python check_cv.py cv.docx keywords.json
    python check_cv.py cv.docx keywords.json --no-color
        keywords.json: {"tier1": ["...","..."], "tier2": ["..."]}  (or a flat ["..."])
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from docx import Document
from docx.oxml.ns import qn


_USE_COLOR = (sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
              and "--no-color" not in sys.argv)
GREEN = "\033[92m" if _USE_COLOR else ""
RED = "\033[91m" if _USE_COLOR else ""
YELLOW = "\033[93m" if _USE_COLOR else ""
RESET = "\033[0m" if _USE_COLOR else ""
def ok(m):   print(f"{GREEN}PASS{RESET}  {m}")
def bad(m):  print(f"{RED}FAIL{RESET}  {m}")
def warn(m): print(f"{YELLOW}WARN{RESET}  {m}")
def info(m): print(f"      {m}")


STANDARD_HEADINGS = ["professional summary", "summary", "profile", "personal profile",
                     "skills", "key skills", "core skills",
                     "work experience", "professional experience", "experience",
                     "education", "qualifications"]

PROHIBITED = {
    "date of birth": r"date of birth|d\.?o\.?b\.?\b",
    "age": r"\bage\s*[:\-]\s*\d{2}\b",
    "marital status": r"marital status",
    "nationality": r"\bnationality\b",
    "right to work / citizenship": r"right to work|work authori[sz]ation|\beu citizen",
    "national insurance": r"national insurance|\bni\s*(number|no)\b",
    "gender/sex": r"\bgender\s*[:\-]|\bsex\s*[:\-]",
    "religion": r"\breligion\b",
    "photo reference": r"\bphotograph\b|\bphoto attached\b",
    "full reference contact": r"references?:.*(@|\b0\d{9,10}\b)",
}

US_SPELLINGS = [
    r"\bcolor\b", r"\bcolors\b", r"\bfavor\b", r"\bfavorite\b", r"\bhonor\b",
    r"\bbehavior\b", r"\bbehaviors\b", r"\bcenter\b", r"\bcenters\b",
    r"\btheater\b", r"\bdefense\b", r"\boffense\b", r"\blicense\b(?!\s+to)",
    r"\bresume\b", r"\bcell phone\b", r"\bmath\b", r"\bapartment\b",
    r"\belevator\b", r"\bfulfillment\b", r"\benrollment\b", r"\btraveler\b",
    r"\bcatalog\b", r"\bcanceled\b", r"\bprogram\b(?!ming|me)",
]

# Glyphs that can begin a rendered bullet line (LibreOffice renders Word's List
# Bullet style using the Symbol private-use char U+F0B7; others added for safety).
BULLET_GLYPHS = set("•▪●◦‣·*")


def all_text(doc):
    return "\n".join(p.text for p in doc.paragraphs)


def _norm(s):
    """Lowercase; treat hyphens/slashes as spaces; collapse whitespace - so
    'follow-up' matches 'follow up', avoiding false keyword misses."""
    return re.sub(r"[\s\-/]+", " ", str(s).lower()).strip()


def _has_term(text, term):
    """Term present as a word, not inside another word ("UAT" must not match "evaluation").
    Longer terms may still match as a word stem, which keyword lists for inflected languages
    rely on ("manag" matches "management"); terms of four characters or fewer must match whole."""
    t = _norm(term)
    if not t:
        return False
    tail = r"(?![a-z0-9])" if len(t) <= 4 else ""
    return re.search(r"(?<![a-z0-9])" + re.escape(t) + tail, text) is not None


def render_pdf(docx_path, td):
    """Render the .docx to PDF once (reused by page + layout checks). Returns the
    PDF path or None if LibreOffice is unavailable."""
    prof = f"-env:UserInstallation=file://{os.path.join(td, 'lo')}"
    subprocess.run(["soffice", "--headless", prof, "--convert-to", "pdf",
                    "--outdir", td, docx_path],
                   capture_output=True, text=True, timeout=120)
    pdfs = [f for f in os.listdir(td) if f.endswith(".pdf")]
    return os.path.join(td, pdfs[0]) if pdfs else None


def _layout_text(pdf_path):
    return subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                          capture_output=True, text=True).stdout


def check_structure(doc):
    print("\n== STRUCTURE (ATS parse safety) ==")
    if doc.tables:
        bad(f"{len(doc.tables)} table(s) found. Tables scramble on ATS extraction. Remove them.")
    else:
        ok("No tables (single-column linear layout).")

    hf_text = []
    for s in doc.sections:
        for part in (s.header, s.first_page_header, s.even_page_header,
                     s.footer, s.first_page_footer, s.even_page_footer):
            if part is None:
                continue
            t = "\n".join(p.text for p in part.paragraphs).strip()
            if t:
                hf_text.append(t)
    if hf_text:
        bad("Header/footer contains text. Many ATS ignore these layers - move all "
            "contact details into the body:")
        for t in hf_text:
            info(repr(t[:80]))
    else:
        ok("No header/footer content (contact details must live in the body).")

    xml = doc.element.xml
    if "w:drawing" in xml or "pic:pic" in xml or "v:imagedata" in xml:
        bad("Document contains an image/drawing. ATS cannot read images; remove logos/photos/icons.")
    else:
        ok("No images or drawings.")

    multicol = False
    for s in doc.sections:
        cols = s._sectPr.find(qn("w:cols"))
        if cols is not None and cols.get(qn("w:num")) and int(cols.get(qn("w:num"))) > 1:
            multicol = True
    if multicol:
        bad("A section uses multiple newspaper columns. This scrambles on extraction.")
    else:
        ok("No multi-column sections.")


def check_headings(doc):
    print("\n== SECTION HEADINGS (ATS classification) ==")
    text_lines = [p.text.strip().lower() for p in doc.paragraphs if p.text.strip()]
    found = sorted({h for h in STANDARD_HEADINGS if any(line == h for line in text_lines)})
    has_exp = any(h in found for h in ["work experience", "professional experience",
                                       "experience"])
    has_edu = any(h in found for h in ["education", "qualifications"])
    has_skills = any(h in found for h in ["skills", "key skills", "core skills"])
    if found:
        ok(f"Standard headings detected: {', '.join(found)}")
    if not has_exp:
        warn("No standard Work Experience heading found.")
    if not has_edu:
        warn("No standard Education heading found.")
    if not has_skills:
        warn("No standard Skills heading found.")
    forbidden = {"interests", "hobbies", "interests & hobbies", "interests and hobbies"}
    if any(line in forbidden for line in text_lines):
        bad("An Interests/Hobbies section is present. This skill excludes it by design "
            "(UK norm) - remove it, even if the master profile lists interests.")


def check_skim(doc):
    print("\n== TOP-OF-DOCUMENT SKIM PREVIEW (first ~15 lines a recruiter sees) ==")
    shown = 0
    for p in doc.paragraphs:
        if p.text.strip():
            info(p.text.strip()[:100])
            shown += 1
        if shown >= 15:
            break
    info(f"... [total body word count: {len(all_text(doc).split())}]")


def check_pages(pdf_path):
    print("\n== PAGE COUNT & BALANCE (target: a FULL 2 pages of A4) ==")
    if not pdf_path:
        warn("Could not render to PDF (LibreOffice unavailable); page check skipped.")
        return
    try:
        pi = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
        m = re.search(r"Pages:\s+(\d+)", pi.stdout)
        pages = int(m.group(1)) if m else None

        # Per-page line counts (form feed separates pages in pdftotext output).
        page_chunks = [c for c in _layout_text(pdf_path).split("\f")]
        line_counts = [sum(1 for L in c.split("\n") if L.strip()) for c in page_chunks]
        line_counts = [n for n in line_counts if n > 0]

        if pages is None:
            warn("Rendered PDF but could not read page count.")
            return
        if pages == 2:
            ok("Renders to 2 pages.")
        elif pages == 1:
            warn("Renders to 1 page. Correct for early-career candidates; for an "
                 "experienced candidate you are likely under-selling - add genuine depth.")
            info("Density guide: ~550-750 words of body text fills two pages; under ~450 stays on one.")
            return
        else:
            bad(f"Renders to {pages} pages. UK standard is 2 (3 only for 15+ yr / senior). "
                "Trim older roles to 2-3 bullets and tighten the summary.")

        # Balance: how full is the final page vs the fullest page?
        if pages >= 2 and line_counts:
            fullest = max(line_counts)
            last = line_counts[-1]
            ratio = last / fullest if fullest else 0
            pct = round(ratio * 100)
            if ratio < 0.60:   # rule: final page at least 60% full
                bad(f"Page {pages} is only ~{pct}% full ({last}/{fullest} lines) - a half-empty "
                    "final page looks unbalanced and amateur.")
                info("Fix: add more of the candidate's GENUINE achievements (extra bullets on "
                     "recent roles, a fuller skills/summary) to fill it to a confident full "
                     "page - or, if there isn't enough real content, tighten to a strong single page.")
            else:
                ok(f"Final page ~{pct}% full - reasonably balanced.")
    except Exception as e:
        warn(f"Page check skipped ({e}).")


def check_widows(pdf_path):
    """Flag bullets that wrap and leave only 1-2 words stranded on the last line.
    These 'widows' waste space and look unpolished; the fix is to tighten the
    wording onto one line, or add a concrete detail to fill the line."""
    print("\n== LINE-BREAK QUALITY (no 1-2 word 'widow' lines in bullets) ==")
    if not pdf_path:
        warn("Could not render to PDF; widow check skipped.")
        return
    try:
        lines = _layout_text(pdf_path).replace("\f", "\n").split("\n")
        bullets, cur = [], None

        def is_bullet_start(s):
            return bool(s) and (s[0] in BULLET_GLYPHS or s[:2] in ("- ", "– ", "— "))

        for ln in lines:
            if not ln.strip():
                if cur:
                    bullets.append(cur); cur = None
                continue
            lead = len(ln) - len(ln.lstrip())
            stripped = ln.strip()
            if is_bullet_start(stripped):
                if cur:
                    bullets.append(cur)
                body = stripped[1:] if stripped[0] in BULLET_GLYPHS else stripped[2:]
                cur = [body.strip()]
            elif cur is not None and lead >= 2:        # wrapped continuation of a bullet
                cur.append(stripped)
            else:                                       # heading / role line / skills -> ends bullet
                if cur:
                    bullets.append(cur); cur = None
        if cur:
            bullets.append(cur)

        runts = [b for b in bullets if len(b) >= 2 and 1 <= len(b[-1].split()) <= 2]
        # Rule: a bullet is one line, or two lines whose second line is at
        # least half full. Three or more lines is a fail; add another bullet instead.
        wrapped_firsts = [len(b[0]) for b in bullets if len(b) >= 2]
        full = max(wrapped_firsts) if wrapped_firsts else 0
        too_long = [b for b in bullets if len(b) >= 3]
        thin = [b for b in bullets if len(b) == 2 and full and len(b[-1]) / full < 0.5]
        if too_long:
            bad(f"{len(too_long)} bullet(s) run to 3 or more lines. Maximum is 2: split into two "
                "bullets or tighten.")
            for b in too_long[:10]:
                info(f"{len(b)} lines: {' '.join(b)[:90]}...")
        else:
            ok(f"Every bullet is at most 2 lines ({len(bullets)} bullets).")
        if thin:
            bad(f"{len(thin)} two-line bullet(s) end on a line under half full. Tighten to one "
                "line or add a real detail so the second line is at least half full.")
            for b in thin[:10]:
                info(f"second line {round(100*len(b[-1])/full)}% full: ...{b[-1][:70]}")
        elif bullets:
            ok("Every two-line bullet has a second line at least half full.")
        if runts:
            bad(f"{len(runts)} bullet(s) end with a 1-2 word 'widow' line. Rewrite each: "
                "tighten to a clean single line, OR add a real detail/metric so the last "
                "line is reasonably full - never leave 1-2 words stranded.")
            for b in runts[:10]:
                full = " ".join(b)
                info(f"...{full[-72:]}   (widow: '{b[-1]}')")
        elif bullets:
            ok(f"No widow lines across {len(bullets)} bullets (each is one clean line or a full wrap).")
        else:
            info("No bullet lines detected to analyse.")
    except Exception as e:
        warn(f"Widow check skipped ({e}).")


def check_gaps(doc):
    """Flag employment-timeline problems: an unexplained gap between roles, or a
    dropped current/most-recent role (the latest Work Experience entry ends well
    before today). Relevance should set a role's DEPTH, not delete it from the
    timeline - dropping a role, especially the current one, is what creates the
    unexplained gaps recruiters treat as a red flag. Heuristic: reads dates from
    the Work Experience section only and skips anything it cannot parse. Handles
    English date formats."""
    import datetime
    print("\n== EMPLOYMENT TIMELINE (no dropped current role / no unexplained gaps) ==")
    today = datetime.date.today()
    TODAY = (today.year, today.month)
    MONTHS = {}
    for idx, names in enumerate(
            [("jan", "january"), ("feb", "february"), ("mar", "march"),
             ("apr", "april"), ("may",), ("jun", "june"), ("jul", "july"),
             ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"),
             ("nov", "november"), ("dec", "december")], start=1):
        for n in names:
            MONTHS[n] = idx
    WORK = {"work experience", "professional experience", "experience",
            "employment history", "career history", "additional experience",
            "other experience", "earlier career", "earlier roles"}
    OTHER = {"education", "qualifications", "skills", "key skills", "core skills",
             "certifications", "professional development", "languages", "summary",
             "professional summary", "profile", "personal profile", "references",
             "projects", "publications"}

    def heading_kind(t):
        s = t.strip().lower().rstrip(":")
        if s in WORK:
            return "work"
        if s in OTHER:
            return "other"
        if t.strip() and t.strip() == t.strip().upper() and 1 <= len(t.split()) <= 5 \
                and any(c.isalpha() for c in t):
            return "work" if s in WORK else "other"
        return None

    def parse_point(s, is_end):
        s = s.strip().lower()
        if re.search(r"present|current|\bnow\b|dabar|ongoing|to date|iki dabar", s):
            return TODAY
        ym = re.search(r"(19|20)\d\d", s)
        if not ym:
            return None
        year = int(ym.group(0))
        month = None
        for n, v in MONTHS.items():
            if re.search(r"\b" + n, s):
                month = v
                break
        if month is None:
            rest = re.sub(r"(19|20)\d\d", "", s)
            mnum = re.findall(r"\b(0?[1-9]|1[0-2])\b", rest)
            if mnum:
                month = int(mnum[0])
        if month is None:
            month = 12 if is_end else 1
        return (year, month)

    def months_between(a, b):
        return (b[0] - a[0]) * 12 + (b[1] - a[1])

    roles = []
    in_work = False
    for p in doc.paragraphs:
        t = p.text
        if not t.strip():
            continue
        h = heading_kind(t)
        if h == "work":
            in_work = True
            continue
        if h == "other":
            in_work = False
            continue
        if in_work and "\t" in t:
            dr = t.split("\t")[-1]
            parts = re.split(r"\s*[–—]\s*|\s+-\s+|\s+to\s+", dr)
            if len(parts) >= 2:
                st = parse_point(parts[0], False)
                en = parse_point(parts[-1], True)
                if st and en:
                    roles.append((st, en, t.split("\t")[0].strip()[:40]))

    if not roles:
        info("No datable Work Experience entries found; timeline check skipped.")
        return

    problems = False
    latest = max(roles, key=lambda r: (r[1][0], r[1][1]))
    trail = months_between(latest[1], TODAY)
    if trail > 6:
        bad(f"Most recent role ('{latest[2]}') ends {latest[1][1]:02d}/{latest[1][0]} - "
            f"~{trail} months to today are unexplained. The current/most-recent role may "
            f"have been dropped; keep it on the CV (compress, don't delete).")
        problems = True

    roles_sorted = sorted(roles, key=lambda r: (r[0][0], r[0][1]))
    max_end = roles_sorted[0][1]
    for st, en, lab in roles_sorted[1:]:
        g = months_between(max_end, st)
        if g > 5:
            bad(f"~{g}-month gap before '{lab}' (starts {st[1]:02d}/{st[0]}). Fill it or keep "
                f"the role that covered it - don't leave an unexplained gap.")
            problems = True
        if (en[0], en[1]) > (max_end[0], max_end[1]):
            max_end = en

    if not problems:
        ok(f"Continuous timeline across {len(roles)} roles; most recent role is current.")


def check_prohibited(doc):
    print("\n== UK PROHIBITED PERSONAL DATA ==")
    text = all_text(doc).lower()
    hits = [label for label, pat in PROHIBITED.items() if re.search(pat, text)]
    if hits:
        for h in hits:
            bad(f"Possible prohibited item on a UK CV: '{h}'. Review and remove if personal data.")
    else:
        ok("No prohibited personal data detected (no DOB, marital status, nationality, NI no., photo).")


def check_spelling(doc):
    print("\n== BRITISH ENGLISH PASS ==")
    text = all_text(doc).lower()
    found = sorted({re.search(p, text).group(0) for p in US_SPELLINGS if re.search(p, text)})
    if found:
        warn(f"Possible US spellings to review: {', '.join(found)}")
    else:
        ok("No common US spellings detected.")


def check_keywords(doc, kw_path):
    print("\n== KEYWORD COVERAGE vs JOB DESCRIPTION ==")
    with open(kw_path, "r", encoding="utf-8") as f:
        kw = json.load(f)
    if isinstance(kw, list):
        kw = {"tier1": kw}
    text = _norm(all_text(doc))

    def report(tier_name, terms):
        if not terms:
            return
        present = [t for t in terms if _has_term(text, t)]
        missing = [t for t in terms if not _has_term(text, t)]
        pct = round(100 * len(present) / len(terms)) if terms else 0
        line = f"{tier_name}: {len(present)}/{len(terms)} ({pct}%) present."
        if tier_name == "tier1" and pct >= 75:
            ok(line)
        elif tier_name == "tier1":
            bad(line + " Aim for >=75% of must-have terms.")
        else:
            info(line)
        if missing:
            info(f"  Missing: {', '.join(missing)}")

    report("tier1", kw.get("tier1", []))
    report("tier2", kw.get("tier2", []))


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return
    args = [a for a in sys.argv[1:] if a != "--no-color"]
    if len(args) < 1:
        print("Usage: python check_cv.py cv.docx [keywords.json] [--no-color]",
              file=sys.stderr)
        sys.exit(2)
    path = args[0]
    doc = Document(path)
    print(f"Checking: {path}")
    check_structure(doc)
    check_headings(doc)
    check_skim(doc)
    with tempfile.TemporaryDirectory() as td:
        pdf = render_pdf(path, td)
        check_pages(pdf)
        check_widows(pdf)
    check_gaps(doc)
    check_prohibited(doc)
    check_spelling(doc)
    if len(args) >= 2:
        check_keywords(doc, args[1])
    print("\nDone. Address any FAIL lines before sending; review WARN lines.")


if __name__ == "__main__":
    main()
