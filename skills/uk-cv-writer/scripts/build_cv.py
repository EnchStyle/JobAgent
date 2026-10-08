#!/usr/bin/env python3
"""
build_cv.py - Generate an ATS-safe, UK-standard CV as a .docx file.

This script is the deterministic core of the uk-cv-writer skill. It takes a
structured JSON "content model" (the tailored CV content that Claude writes for
a specific job) and renders a single-column Word document that:

  * parses cleanly through Applicant Tracking Systems (no tables, no text
    boxes, no multi-column layout, no header/footer content, no images), and
  * reads well to a human skimming for 7 seconds (clear hierarchy, bold job
    titles, a two-line role header with the date right-aligned clear of the
    title, generous white space).

Why a script instead of writing the .docx by hand each time: the ATS-safety
guarantees (single column, real bullet styles, contact details in the body,
standard headings) must hold on EVERY run regardless of model variance. Encoding
them once here makes every CV structurally safe by construction. Claude's job is
to fill the JSON with excellent, truthful, tailored content; this script makes
sure the container is sound.

Usage:
    python build_cv.py content.json output.docx

See assets/cv-content-schema.json for the full input schema and an example.
"""

import json
import re
import sys
from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ---------------------------------------------------------------------------
# Defaults. Every value can be overridden via the JSON "config" block so the
# skill can tune density to hit a clean two-page fit without editing this file.
# ---------------------------------------------------------------------------
DEFAULTS = {
    "font": "Calibri",          # Calibri/Arial/Cambria/Georgia all parse cleanly
    "body_size": 10.5,          # 10-12pt is the safe body range
    "name_size": 20.0,          # 18-22pt
    "heading_size": 11.0,       # section headings
    "contact_size": 9.5,
    "line_spacing": 1.06,
    "margin_top_mm": 14.0,
    "margin_bottom_mm": 14.0,
    "margin_left_mm": 18.0,
    "margin_right_mm": 18.0,
    "bullet_space_after_pt": 2.0,
    "role_space_after_pt": 6.0,
    "heading_space_before_pt": 8.0,
    "heading_space_after_pt": 3.0,
    "accent_hex": None,          # e.g. "1F3864" for a subtle heading colour; None = black (safest)
    "uppercase_headings": True,
    # Standard, ATS-whitelisted section labels. Override only with care - these
    # exact strings are what ATS section classifiers recognise most reliably.
    "labels": {
        "summary": "Professional Summary",
        "skills": "Skills",
        "experience": "Work Experience",
        "education": "Education",
    },
}


def cfg(config, key):
    return config.get(key, DEFAULTS[key])


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def set_base_styles(doc, config):
    """Set the document-wide default font, size and line spacing on Normal."""
    normal = doc.styles["Normal"]
    normal.font.name = cfg(config, "font")
    normal.font.size = Pt(cfg(config, "body_size"))
    # Ensure the font applies to all script ranges (prevents Word substituting).
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), cfg(config, "font"))
    pf = normal.paragraph_format
    pf.line_spacing = cfg(config, "line_spacing")
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)


def set_page(doc, config):
    section = doc.sections[0]
    section.page_width = Mm(210)      # A4 (UK standard)
    section.page_height = Mm(297)
    section.top_margin = Mm(cfg(config, "margin_top_mm"))
    section.bottom_margin = Mm(cfg(config, "margin_bottom_mm"))
    section.left_margin = Mm(cfg(config, "margin_left_mm"))
    section.right_margin = Mm(cfg(config, "margin_right_mm"))


def content_width_mm(config):
    return 210.0 - cfg(config, "margin_left_mm") - cfg(config, "margin_right_mm")


def add_bottom_border(paragraph, color="auto", size="6"):
    """Add a thin rule under a paragraph (used for section headings).
    A paragraph border is ATS-safe - it is NOT a table and does not affect the
    linear text stream. Inserted at the correct position in pPr (these heading
    paragraphs have no pStyle/numPr, so index 0 is schema-valid)."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.insert(0, pBdr)


def add_right_tab(paragraph, config):
    """Add a right-aligned tab stop at the right margin so dates can sit on the
    same line as a job title. This keeps the entry as ONE paragraph (a single
    text element to the parser) - unlike a real two-column layout, which
    scrambles on extraction."""
    pos = Mm(content_width_mm(config))
    paragraph.paragraph_format.tab_stops.add_tab_stop(pos, WD_TAB_ALIGNMENT.RIGHT)


def accent_color(config):
    hex_ = cfg(config, "accent_hex")
    if hex_:
        return RGBColor.from_string(hex_)
    return None


def add_heading(doc, text, config):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(cfg(config, "heading_space_before_pt"))
    p.paragraph_format.space_after = Pt(cfg(config, "heading_space_after_pt"))
    p.paragraph_format.keep_with_next = True
    label = text.upper() if cfg(config, "uppercase_headings") else text
    run = p.add_run(label)
    run.bold = True
    run.font.size = Pt(cfg(config, "heading_size"))
    col = accent_color(config)
    if col is not None:
        run.font.color.rgb = col
    add_bottom_border(p, color=(cfg(config, "accent_hex") or "auto"))
    return p


def _cap_first(s):
    """Capitalise the first letter of a skills item for a consistent list, while
    leaving items whose first word already contains an uppercase letter untouched
    - this preserves acronyms and intentional casing (SQL, CRM, iOS, eBay)
    and also capitalises an item wrapped in italics markup, e.g. "*per se*" -> "*Per se*".

    Uses str.isalpha() (Unicode-aware) to find the first letter rather than the
    ASCII-only [A-Za-z] regex this used to use. That regex would skip a non-ASCII
    initial letter (e.g. "É", "Ö", "Ł") and capitalise the next ASCII letter
    instead, corrupting text like "Économie" into "ÉConomie" - this fixes it so
    any Unicode letter (non-English CVs included) is found and cased correctly."""
    s = str(s)
    i = None
    for idx, ch in enumerate(s):
        if ch.isdigit():
            return s  # starts with a number ("3 certifications"): leave it as written
        if ch.isalpha():
            i = idx
            break
    if i is None:
        return s
    j = i
    while j < len(s) and not s[j].isspace():
        j += 1
    first = s[i:j]
    # Leave intentional casing alone: acronyms and brands (SQL, iOS, eBay) and tool names
    # that contain digits.
    if any(c.isupper() for c in first) or any(c.isdigit() for c in first):
        return s
    return s[:i] + s[i].upper() + s[i + 1:]


def _add_inline(paragraph, text, size=None, italic=False):
    """Add text to a paragraph, rendering *...* spans in italics so the content
    author can mark foreign phrases, Latin names or publication titles. Everything
    outside the asterisks stays upright. Acronyms and brand names should be left
    un-marked."""
    if text is None:
        return
    for part in re.split(r"(\*[^*]+\*)", str(text)):
        if not part:
            continue
        if len(part) >= 2 and part[0] == "*" and part[-1] == "*":
            run = paragraph.add_run(part[1:-1]); run.italic = True
        else:
            run = paragraph.add_run(part)
            if italic:
                run.italic = True
        if size:
            run.font.size = Pt(size)


def add_bullet(doc, text, config):
    try:
        p = doc.add_paragraph(style="List Bullet")
        _add_inline(p, _cap_first(text))
    except KeyError:
        # Fallback if the template lacks the List Bullet style: a hanging-indent
        # paragraph with a real bullet glyph (still a standard character).
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Mm(6)
        p.paragraph_format.first_line_indent = Mm(-4)
        _add_inline(p, "•  " + _cap_first(text))
    p.paragraph_format.space_after = Pt(cfg(config, "bullet_space_after_pt"))
    p.paragraph_format.line_spacing = cfg(config, "line_spacing")
    return p


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------
def build_header(doc, data, config):
    name_p = doc.add_paragraph()
    name_p.paragraph_format.space_after = Pt(2)
    r = name_p.add_run(data["name"])
    r.bold = True
    r.font.size = Pt(cfg(config, "name_size"))
    col = accent_color(config)
    if col is not None:
        r.font.color.rgb = col

    # Optional professional headline (e.g. target job title) under the name.
    headline = data.get("headline")
    if headline:
        hp = doc.add_paragraph()
        hp.paragraph_format.space_after = Pt(2)
        hr = hp.add_run(headline)
        hr.bold = True
        hr.font.size = Pt(cfg(config, "body_size") + 0.5)

    # Contact details: plain text in the BODY (never a header/footer or text
    # box). Order: phone | email | linkedin | website. A 'location'/city, a
    # nationality, and any right-to-work line are intentionally NOT rendered.
    c = data.get("contact", {})
    parts = [c.get("phone"), c.get("email"), c.get("linkedin"), c.get("website")]
    parts = [p for p in parts if p]
    contact_p = doc.add_paragraph()
    contact_p.paragraph_format.space_after = Pt(4)
    cr = contact_p.add_run("   |   ".join(parts))
    cr.font.size = Pt(cfg(config, "contact_size"))


def build_summary(doc, data, config):
    summary = data.get("summary")
    if not summary:
        return
    add_heading(doc, cfg(config, "labels")["summary"], config)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    _add_inline(p, summary)


def build_skills(doc, data, config):
    skills = data.get("skills")
    if not skills:
        return
    add_heading(doc, cfg(config, "labels")["skills"], config)
    if isinstance(skills, dict):
        # Grouped: {"Category": ["a", "b"], ...} -> one line per category.
        for category, items in skills.items():
            if not items:
                continue
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            br = p.add_run(f"{category}: ")
            br.bold = True
            _add_inline(p, ", ".join(_cap_first(i) for i in items))
    else:
        # Flat list -> a single comma-separated line (highest NER recall and
        # zero parse risk).
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        _add_inline(p, ", ".join(_cap_first(x) for x in skills))


def _entry_header(doc, title, subtitle, right_text, config):
    """Two-line entry header. Line 1 is a SHORT bold title with the date pushed to
    the right margin - because the title is short, the date sits far to the right
    with a clear gap and never collides with a long employer/location string.
    Line 2 carries the employer and location on their own line. This reads far more
    cleanly than cramming title + employer + location + dates onto one line, where
    long left-hand text blends into the right-aligned date."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    if right_text:
        add_right_tab(p, config)
    if title:
        rb = p.add_run(title)
        rb.bold = True
    if right_text:
        p.add_run("\t" + right_text)
    if subtitle:
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(2)
        p2.paragraph_format.keep_with_next = True
        r2 = p2.add_run(subtitle)
        r2.italic = True
        r2.font.size = Pt(cfg(config, "body_size"))
    return p


def _date_range(entry):
    start = entry.get("start", "")
    end = entry.get("end", "")
    if start and end:
        return f"{start} – {end}"   # en dash
    return start or end or ""


def build_experience(doc, data, config):
    roles = data.get("experience")
    if not roles:
        return
    add_heading(doc, cfg(config, "labels")["experience"], config)
    for role in roles:
        title = role.get("title", "")
        company = role.get("company", "")
        location = role.get("location", "")
        right = _date_range(role)
        subtitle = ", ".join([b for b in [company, location] if b])
        _entry_header(doc, title, subtitle, right, config)
        for b in role.get("bullets", []):
            if b and b.strip():
                add_bullet(doc, b.strip(), config)
        # trailing space after the role block
        if doc.paragraphs:
            doc.paragraphs[-1].paragraph_format.space_after = Pt(cfg(config, "role_space_after_pt"))


def build_education(doc, data, config):
    edu = data.get("education")
    if not edu:
        return
    add_heading(doc, cfg(config, "labels")["education"], config)
    for e in edu:
        qual = e.get("qualification", "")
        inst = e.get("institution", "")
        right = _date_range(e)
        _entry_header(doc, qual, inst, right, config)
        detail = e.get("detail")
        if detail:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(cfg(config, "role_space_after_pt"))
            _add_inline(p, detail, size=cfg(config, "body_size"))


def build_additional(doc, data, config):
    """Render any extra sections in order. Accepts a list of {"heading","items"}
    or {"heading","text"}. Short item lists render as a compact comma line;
    longer/achievement items render as bullets."""
    for sec in data.get("additional", []) or []:
        heading = sec.get("heading")
        if not heading:
            continue
        add_heading(doc, heading, config)
        if sec.get("text"):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            _add_inline(p, sec["text"])
            continue
        items = sec.get("items", [])
        if not items:
            continue
        as_bullets = sec.get("bullets")
        if as_bullets is None:
            as_bullets = any(len(str(i)) > 60 for i in items)
        if as_bullets:
            for i in items:
                add_bullet(doc, str(i), config)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            _add_inline(p, ", ".join(_cap_first(str(i)) for i in items))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build(data):
    config = data.get("config", {})
    doc = Document()
    set_base_styles(doc, config)
    set_page(doc, config)

    build_header(doc, data, config)
    build_summary(doc, data, config)
    build_skills(doc, data, config)
    build_experience(doc, data, config)
    build_education(doc, data, config)
    build_additional(doc, data, config)
    return doc


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return
    if len(sys.argv) != 3:
        print("Usage: python build_cv.py content.json output.docx", file=sys.stderr)
        sys.exit(2)
    in_path, out_path = sys.argv[1], sys.argv[2]
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "name" not in data:
        print("ERROR: content JSON must include a top-level 'name'.", file=sys.stderr)
        sys.exit(1)
    doc = build(data)
    doc.save(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
