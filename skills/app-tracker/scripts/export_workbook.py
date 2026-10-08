"""Export the colour-coded tracker workbook, one tab per market.

Markets (countries) come from config/filters.md (markets.<code>.label), so each market's roles
sit in their own tab with their own currency. Structure produced:

  - "Summary"      : per-market counts by reporting category (applied, interview, closed, in
                     progress, review or hold, blocked, rejected, not scored).
  - one tab per market that has rows, in the order the markets are configured, then "Other".

Every data row is colour-coded by status:
  - BLUE    applied
  - PURPLE  interview
  - GREY    closed (an outcome after applying, or an advert that closed)
  - GREEN   in progress: scored at or above the apply threshold, cv_generated or verified
  - YELLOW  review band (scored 50 to 59) or on hold: waiting for the user's decision
  - ORANGE  blocked_login: needs the user to finish by hand
  - RED     rejected (below threshold, location, sales, expired, duplicate or a cull; the reason
            is in the "Rationale / cull reason" column)
  - AMBER   found, not yet scored

The apply threshold is read live from config/scoring_rubric.md (threshold_apply), the same
source save_score.py and eligible.py use. A row's market is worked out from its location text
(markets.<code>.location_hints, and foreign_location_hints for "Other"), then the source's market
in config/sources.md, then the salary currency. Rationale and gaps come from the stored score_breakdown JSON; for
culled rows the reason is read from notes. Written to output/jobs_overview.xlsx via openpyxl.
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, paths, config_loader, markets as mk

try:
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("openpyxl not installed: pip install -r requirements.txt")

DEFAULT_THRESHOLD = 60

HEADERS = ["Ref (job_id)", "Source", "Score", "Status", "Title", "Company", "Location",
           "Mode", "Salary", "Applied", "URL", "Rationale / cull reason", "Gaps", "CV file", "Cover letter"]
WIDTHS = [13, 10, 7, 10, 44, 26, 20, 9, 16, 12, 46, 70, 50, 34, 40]

HEAD_FILL = PatternFill("solid", fgColor="333333")
HEAD_FONT = Font(bold=True, color="FFFFFF")
FILLS = {
    "applied":   PatternFill("solid", fgColor="BDD7EE"),
    "interview": PatternFill("solid", fgColor="D9D2E9"),
    "closed":    PatternFill("solid", fgColor="D9D9D9"),
    "green":     PatternFill("solid", fgColor="C6EFCE"),
    "review":    PatternFill("solid", fgColor="FFF2CC"),
    "blocked":   PatternFill("solid", fgColor="F8CBAD"),
    "red":       PatternFill("solid", fgColor="FFC7CE"),
    "amber":     PatternFill("solid", fgColor="FFEB9C"),
}
def apply_threshold():
    """Apply cutoff from config/scoring_rubric.md (same source save_score.py reads)."""
    try:
        return int(config_loader.scoring().get("threshold_apply", DEFAULT_THRESHOLD))
    except Exception:
        return DEFAULT_THRESHOLD


def market_of(r, ms):
    """Display label of a row's market (see the module docstring for the order of evidence)."""
    keys = r.keys()
    if mk.foreign_location(r["location"] or ""):
        return "Other"  # a place outside every configured market (foreign_location_hints)
    code = (r["market"] if "market" in keys else None) or ""
    if code.lower() not in ms:
        code = mk.market_for((r["source"] or "").lower(), r["location"] or "")
    if code.lower() not in ms:
        cur = (r["salary_currency"] or "").upper()
        code = next((c for c, m in ms.items() if str(m.get("currency", "")).upper() == cur), "")
    m = ms.get(code.lower())
    return m["label"] if m else "Other"


def salary_of(r):
    if r["salary_min"] or r["salary_max"]:
        cur = r["salary_currency"] or ""
        lo = str(int(r["salary_min"])) if r["salary_min"] is not None else ""
        hi = str(int(r["salary_max"])) if r["salary_max"] is not None else ""
        rng = lo + ("-" + hi if hi else "")
        return f"{cur} {rng}".strip()
    return ""


def _band(r):
    try:
        return (json.loads(r["score_breakdown"] or "{}") or {}).get("band")
    except Exception:
        return None


def category(r, threshold):
    """One reporting category per row; the colour and the Summary counts both use it."""
    st = r["status"]
    sc = r["match_score"] or 0
    if st == "applied":
        return "applied"
    if st == "interview":
        return "interview"
    if st == "closed":
        return "closed"
    if st in ("cv_generated", "verified"):
        return "green"
    if st == "scored":
        return "green" if (sc >= threshold and _band(r) != "hold") else "review"
    if st == "blocked_login":
        return "blocked"
    if st == "rejected":
        return "red"
    return "amber"


def fill_for(r, threshold):
    return FILLS[category(r, threshold)]


def rationale_of(r):
    bd = {}
    if r["score_breakdown"]:
        try:
            bd = json.loads(r["score_breakdown"])
        except Exception:
            return r["score_breakdown"], ""
    rat = bd.get("rationale", "") or (r["notes"] or "")
    gaps = bd.get("gaps", []) or []
    return rat, "; ".join(gaps) if isinstance(gaps, list) else str(gaps)


def style_header(ws):
    for i, h in enumerate(HEADERS, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill = HEAD_FILL
        c.font = HEAD_FONT
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def _base(v):
    """Bare filename for a stored path, or '' if none."""
    import os
    return os.path.basename(v) if v else ""


def add_market_tab(wb, name, rows, threshold):
    ws = wb.create_sheet(title=name)
    style_header(ws)
    for r in rows:
        rat, gaps = rationale_of(r)
        ws.append([r["job_id"], r["source"], r["match_score"], r["status"], r["title"],
                   r["company"], r["location"], r["work_mode"], salary_of(r),
                   r["date_applied"] or "", r["url"], rat, gaps,
                   _base(r["cv_file"]), _base(r["cover_letter_file"])])
        fill = fill_for(r, threshold)
        for c in range(1, len(HEADERS) + 1):
            ws.cell(row=ws.max_row, column=c).fill = fill
    ws.auto_filter.ref = ws.dimensions


def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return
    con = jobdb.init_db()
    rows = con.execute(
        "SELECT * FROM jobs ORDER BY (status='applied') DESC, match_score DESC, id"
    ).fetchall()

    ms = mk.markets()
    threshold = apply_threshold()

    buckets = {}
    for r in rows:
        buckets.setdefault(market_of(r, ms), []).append(r)

    order = [m["label"] for m in ms.values()]
    markets = [m for m in order if m in buckets] + [m for m in buckets if m not in order]

    wb = Workbook()
    wb.remove(wb.active)

    sm = wb.create_sheet(title="Summary")
    cols = ["Market", "Applied (all)", "Interview", "Closed", f"In progress (>={threshold})",
            "Review / hold", "Blocked", "Rejected", "Not scored", "Total"]
    sm.append(cols)
    for i in range(1, len(cols) + 1):
        sm.cell(row=1, column=i).fill = HEAD_FILL
        sm.cell(row=1, column=i).font = HEAD_FONT
    for m in markets:
        b = buckets[m]
        cat = [category(r, threshold) for r in b]
        applied_all = sum(1 for r in b if r["status"] in ("applied", "interview")
                          or (r["status"] == "closed" and r["date_applied"]))
        sm.append([m, applied_all, cat.count("interview"), cat.count("closed"), cat.count("green"),
                   cat.count("review"), cat.count("blocked"), cat.count("red"), cat.count("amber"), len(b)])
    for i, w in enumerate([16, 13, 10, 8, 18, 13, 9, 10, 11, 8], 1):
        sm.column_dimensions[get_column_letter(i)].width = w
    sm.freeze_panes = "A2"

    for m in markets:
        add_market_tab(wb, m, buckets[m], threshold)

    paths.ensure_dirs()
    out = paths.OUTPUT / "jobs_overview.xlsx"
    wb.save(out)
    print("wrote", out)
    for m in markets:
        print(f"  {m}: {len(buckets[m])} rows")


if __name__ == "__main__":
    main()
