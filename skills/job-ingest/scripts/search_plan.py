#!/usr/bin/env python3
"""search_plan.py : the list of searches to run, built from config/sources.md `search_plan`.

One place decides WHAT is searched: the job families (each a list of keywords, with the places it
is searched in and whether it is part of every normal run), the places, and a URL template per
board. This script turns them into concrete search URLs, so a scheduled run, a manual "run the
pipeline" and a one-off request all search the same way, and nothing depends on remembering what
was searched last time.

  Normal run (scheduled or "run the pipeline"): every family with `standing: true`.
      python3 skills/job-ingest/scripts/search_plan.py
  A specific request ("scan delivery roles", "look for product roles in London"): that scope only,
  for this run. Nothing in config changes; a family becomes standing only when the user says so.
      python3 skills/job-ingest/scripts/search_plan.py --family delivery
      python3 skills/job-ingest/scripts/search_plan.py --keywords "product manager,product owner" --places london
  After each search is scraped and saved to inbox/, record it so the next run knows:
      python3 skills/job-ingest/scripts/search_plan.py --done <search id> [<search id> ...]
  See the families and what a normal run covers:
      python3 skills/job-ingest/scripts/search_plan.py --list

A family with `any_role: true` has no keywords: it lists every role in its places (the board's
`city_any` template), for places where any working pattern is fine and the market is small
enough to read everything (the title filter and the hard gates still apply).

Rotation: a standing search is due when it has not run for `cycle_days`; due searches come
oldest first, up to `max_searches_per_run` if set (and a board's own `max_searches`), so a run
that is cut short or skipped is caught up next time. `stop_after_days` per search is the paging window:
the days since that search last ran plus one, capped at config/filters.md max_days_old.

Board salary filter: the floor from config/filters.md times a factor: the market's own
`board_salary_factor` when set, otherwise the plan-wide `board_salary_factor` in sources.md. With
the `top` range rule a factor below 1 (40,000 x 0.9 = 36,000) keeps a range that reaches the floor
(40k to 50k) from being hidden by a board that filters on the bottom of the range. With the
`bottom` range rule the board filter should equal the floor (factor 1.0): anything lower only
lists roles the code then rejects. The code applies the real floor after scraping.

If sources.md has no `search_plan` block, the boards' own search_url and also_run lists are used
as before. Prints JSON. State is kept in logs/search_state.json.
"""
import re
import sys
import json
import math
import argparse
import datetime
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import config_loader, paths, markets as mk  # noqa: E402

STATE = paths.LOGS / "search_state.json"


def _today():
    return datetime.date.today()


def _load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(state):
    paths.ensure_dirs()
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")


def slug(text):
    s = (text or "").lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def board_floor(market, factor, fcfg):
    m = mk.markets(fcfg).get(market) or {}
    floor = m.get("salary_floor")
    if not floor:
        return ""
    if m.get("board_salary_factor") is not None:  # the market's own setting beats the plan-wide one
        factor = m["board_salary_factor"]
    v = float(floor) * float(factor)
    step = 1000 if v >= 10000 else 100
    return str(int(math.floor(v / step) * step))


def _fill(template, keyword, place, floor):
    return template.format(
        q=urllib.parse.quote(keyword or ""),
        q_plus=urllib.parse.quote_plus(keyword or ""),
        slug=slug(keyword),
        city=place.get("city", ""),
        city_slug=slug(place.get("city", "")),
        location_q=urllib.parse.quote(place.get("location") or place.get("city", "")),
        floor=floor,
    )


def build(scope_families=None, keywords=None, places_filter=None, include_all=False, today=None):
    """Return the full candidate list (not yet rotated) for the requested scope."""
    scfg = config_loader.sources() or {}
    fcfg = config_loader.filters() or {}
    plan = scfg.get("search_plan")
    boards = scfg.get("scrape_sources") or {}
    out = []
    if not plan:  # legacy: explicit URL lists per board
        for b, bc in boards.items():
            if not (bc or {}).get("enabled"):
                continue
            for u in [bc.get("search_url")] + list(bc.get("also_run") or []):
                if u:
                    out.append({"id": f"{b}:legacy:{slug(u)[-60:]}", "board": b, "family": "legacy",
                                "keyword": None, "place": None, "url": u, "standing": True,
                                "remote_filtered": "f_WT=2" in u or "/remote-" in u})
        return out, {}
    places = plan.get("places") or {}
    families = plan.get("families") or {}
    factor = plan.get("board_salary_factor", 1.0)
    if keywords:
        fams = {"request": {"standing": False, "keywords": keywords,
                            "places": places_filter or list(places)}}
    else:
        fams = {k: v for k, v in families.items()
                if (scope_families and k in scope_families)
                or (not scope_families and (include_all or (v or {}).get("standing")))}
        unknown = set(scope_families or []) - set(families)
        if unknown:
            raise SystemExit(f"unknown family {sorted(unknown)}; known: {', '.join(families)}")
    for b, bc in boards.items():
        bc = bc or {}
        tpl = (plan.get("boards") or {}).get(b) or {}
        if not bc.get("enabled") or not tpl:
            continue
        bmarket = str(bc.get("market") or "").lower()
        allowed = tpl.get("families")
        for ui, u in enumerate(tpl.get("fixed_urls") or []):  # boards searched by category, not keyword
            if keywords or scope_families:
                continue  # category searches belong to normal runs, not to a specific request
            pk = tpl.get("fixed_place")
            fl = board_floor(bmarket, factor, fcfg)
            out.append({"id": f"{b}:{tpl.get('fixed_label') or 'categories'}:{ui + 1}", "board": b, "family": "all", "keyword": None,
                        "place": pk, "url": u.format(floor=fl), "standing": True, "remote_filtered": False,
                        "rank": (0, ui, 0)})
        for fi, (fk, fam) in enumerate(fams.items()):
            if allowed and fk not in allowed and not scope_families and fk != "request":
                continue  # a board's family list limits normal runs; a request may use every board
            for pi, pk in enumerate(places_filter or fam.get("places") or list(places)):
                place = places.get(pk)
                if place is None:
                    raise SystemExit(f"unknown place {pk!r}; known: {', '.join(places)}")
                pm = str(place.get("market") or "").lower()
                kind = "remote" if place.get("remote") else "city"
                any_role = bool(fam.get("any_role"))
                if kind == "city" and place.get("city") in (tpl.get("skip_cities") or []) and not any_role:
                    kind = "remote"  # this board's national search already covers the city
                template = tpl.get(kind + "_any" if any_role else kind)
                if not template:
                    continue
                if bmarket and pm and pm != bmarket and not tpl.get("any_market"):
                    continue  # a UK board is not searched for a place in another market, unless it covers both
                fl = board_floor(pm or bmarket, factor, fcfg)
                kws = [None] if any_role else (fam.get("keywords") or [])
                for ki, kw in enumerate(kws):
                    out.append({"id": f"{b}:{fk}:{slug(kw) or 'any'}:{pk}", "board": b, "family": fk, "keyword": kw,
                                "place": pk, "url": _fill(template, kw, place, fl),
                                "standing": bool(fam.get("standing")), "remote_filtered": kind == "remote"
                                and bool(tpl.get("remote_is_filtered", True)), "rank": (ki, fi, pi)})
    # one search per id (a keyword listed in two families is searched once)
    seen, uniq = set(), []
    for s in out:
        key = (s["board"], s["url"])
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return uniq, plan


def due(searches, plan, state, today=None, request=False, ignore_caps=False):
    today = today or _today()
    fcfg = config_loader.filters() or {}
    maxd = int((fcfg.get("freshness") or {}).get("max_days_old", 14))
    cycle = int(plan.get("cycle_days", 1)) if plan else 1
    cap_total = int(plan.get("max_searches_per_run", 10 ** 6)) if plan else 10 ** 6
    board_caps = {b: int(t.get("max_searches")) for b, t in ((plan or {}).get("boards") or {}).items()
                  if t and t.get("max_searches")}
    rows = []
    for s in searches:
        last = state.get(s["id"])
        age = (today - datetime.date.fromisoformat(last)).days if last else None
        if not request and age is not None and age < cycle:
            continue
        s = dict(s)
        s["last_run"] = last
        s["stop_after_days"] = min(maxd, (age + 1) if age is not None else maxd)
        rows.append(s)
    # Oldest first; among equals, the first keyword of every family, then the second, and so on
    # (families in priority order), places and boards interleaved,
    # so a capped run covers the top families on every board rather than one board in full.
    rows.sort(key=lambda s: (s["last_run"] or "0000-00-00", tuple(s.get("rank") or (99, 99, 99)), s["board"]))
    picked, deferred, per_board = [], [], {}
    for s in rows:
        b = s["board"]
        if not ignore_caps and ((not request and len(picked) >= cap_total) or per_board.get(b, 0) >= board_caps.get(b, 10 ** 6)):
            deferred.append(s["id"])
            continue
        per_board[b] = per_board.get(b, 0) + 1
        picked.append(s)
    return picked, deferred


def main():
    ap = argparse.ArgumentParser(description="Build the list of searches for this run.")
    ap.add_argument("--family", action="append", help="run only this family (repeatable); not saved to config")
    ap.add_argument("--keywords", help="comma-separated keywords for a one-off request")
    ap.add_argument("--places", help="comma-separated place keys for --keywords (default: all places)")
    ap.add_argument("--all", action="store_true", help="every search now, ignoring rotation")
    ap.add_argument("--done", nargs="+", metavar="ID", help="record these searches as run today")
    ap.add_argument("--list", action="store_true", help="show families, places and the size of a normal run")
    a = ap.parse_args()
    state = _load_state()
    if a.done:
        t = _today().isoformat()
        for i in a.done:
            state[i] = t
        _save_state(state)
        print(json.dumps({"recorded": len(a.done), "date": t}))
        return
    if a.list:
        scfg = config_loader.sources() or {}
        plan = scfg.get("search_plan") or {}
        allsearch, _ = build(include_all=True)
        standing, _ = build()
        fams = {k: {"standing": bool(v.get("standing")), "places": v.get("places"),
                    "keywords": v.get("keywords")} for k, v in (plan.get("families") or {}).items()}
        by_board = {}
        for s in standing:
            by_board[s["board"]] = by_board.get(s["board"], 0) + 1
        print(json.dumps({"families": fams, "places": plan.get("places"),
                          "standing_searches": len(standing), "standing_by_board": by_board,
                          "all_searches": len(allsearch), "cycle_days": plan.get("cycle_days"),
                          "max_searches_per_run": plan.get("max_searches_per_run")},
                         ensure_ascii=False, indent=2))
        return
    kws = [k.strip() for k in a.keywords.split(",") if k.strip()] if a.keywords else None
    places = [p.strip() for p in a.places.split(",") if p.strip()] if a.places else None
    request = bool(a.family or kws)
    searches, plan = build(scope_families=a.family, keywords=kws, places_filter=places)
    picked, deferred = due(searches, plan, state, request=request or a.all, ignore_caps=a.all)
    by_board = {}
    for s in picked:
        by_board[s["board"]] = by_board.get(s["board"], 0) + 1
    print(json.dumps({"scope": ("request: " + ", ".join(a.family or kws)) if request else "standing",
                      "date": _today().isoformat(), "searches": picked, "by_board": by_board,
                      "deferred_to_next_run": len(deferred)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
