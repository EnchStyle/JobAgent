#!/usr/bin/env python3
"""audit_reject_titles.py : evidence check for the reject-title list in config/filters.md.

The reject-title list drops a role on its title alone, before the advert is read, so a wrong
entry hides good roles for ever and a missing one costs a full read of a clear mismatch. This
script checks the list against what the tracker has learnt from full reads. It is read-only.

It reports four things:
  1. collisions  existing entries that match the title of a role scored at or above
                 --positive-score, or applied to (that entry would now hide that role);
  2. substring   existing substring entries whose match lands inside a longer word, with the
                 words actually matched (move an English entry to reject_title_word_boundary;
                 stems in inflected languages are meant to match the start of a longer word);
  3. blocked     per entry, how many scraped cards in the inbox archive it dropped, and how
                 many of those also match relevance.title_any (the drops most worth a look);
  4. candidates  title words and phrases (1 to 3 words) found in at least --min-reads roles that
                 were read in full and scored, none of which scored --positive-score or more or
                 was applied to; with the best score seen and how many unread rows each would drop.

Candidates are evidence, not decisions: a person confirms each one names a different job family
before it is added to config/filters.md. Employer rejections are not evidence here, because those
roles were judged a fit before the application was sent.

  python3 skills/job-ingest/scripts/audit_reject_titles.py
  python3 skills/job-ingest/scripts/audit_reject_titles.py --json audit.json --min-reads 8
  python3 skills/job-ingest/scripts/audit_reject_titles.py --db /path/to/copy.db
"""
import re
import sys
import glob
import json
import sqlite3
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import config_loader, jobdb, paths  # noqa: E402
import filters  # noqa: E402

# Words that say nothing about the job family: seniority, contract, place and filler words.
# A candidate phrase may not start or end with one of these, and a single word may not be one.
STOP = set("""
a an and the of for to in at on with or by from as via x
senior sr snr lead head manager management director principal chief vp associate
uk gb london remote hybrid onsite on-site office based home flexible
contract permanent perm temporary temp fixed term ftc month months week weeks day days
part full time maternity cover interim secondment immediate start
emea europe european global international regional national worldwide
group team new role job opportunity vacancy
england scotland wales ireland northern britain united kingdom
level grade band tier ii iii iv i m f d mfd
""".split())

TOKEN = re.compile(r"[\w+#]+(?:[.'][\w+#]+)*")


def tokens(title):
    return TOKEN.findall((title or "").lower())


def terms_of(title, max_n=3):
    """The 1 to max_n word phrases of a title that can name a job family."""
    toks = tokens(title)
    out = set()
    for n in range(1, max_n + 1):
        for i in range(len(toks) - n + 1):
            g = toks[i:i + n]
            if g[0] in STOP or g[-1] in STOP or any(t.isdigit() or len(t) < 2 for t in g):
                continue
            if n == 1 and len(g[0]) < 3:
                continue
            out.add(" ".join(g))
    return out


def has_term(title, term):
    return f" {term} " in " " + " ".join(tokens(title)) + " "


def single_entry_cfg(cfg, kw):
    return {"reject_title_contains": [kw],
            "reject_title_word_boundary": cfg.get("reject_title_word_boundary", [])}


def load_rows(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT id, title, status, match_score, date_applied FROM jobs")]
    con.close()
    return rows


def load_cards(pattern):
    seen, cards = set(), []
    for f in sorted(glob.glob(pattern, recursive=True)):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not (isinstance(d, dict) and isinstance(d.get("cards"), list)):
            continue
        for c in d["cards"]:
            if not isinstance(c, dict) or not c.get("title"):
                continue
            key = (d.get("source"), str(c.get("id") or c.get("url") or c.get("title")))
            if key in seen:
                continue
            seen.add(key)
            cards.append({"source": d.get("source"), "title": c["title"]})
    return cards


def is_read(r):
    return (r["match_score"] or 0) > 0 or bool(r["date_applied"])


def is_positive(r, pos):
    return (r["match_score"] or 0) >= pos or bool(r["date_applied"])


def audit(rows, cards, cfg, pos=50, min_reads=8, max_n=3, examples=4):
    entries = [k for k in cfg.get("reject_title_contains", []) if k]
    wb = set(k.lower() for k in cfg.get("reject_title_word_boundary", []))
    target = (cfg.get("relevance") or {}).get("title_any", [])
    positives = [r for r in rows if is_positive(r, pos)]
    read = [r for r in rows if is_read(r)]
    unread = [r for r in rows if r["status"] == "found"]

    # 1. collisions
    collisions = []
    for kw in entries:
        one = single_entry_cfg(cfg, kw)
        hit = [r for r in positives if filters.reject_title(r["title"], one)[0]]
        if hit:
            collisions.append({"entry": kw, "count": len(hit), "roles": [
                {"id": r["id"], "title": r["title"], "score": r["match_score"],
                 "status": r["status"]} for r in hit[:examples]]})

    # 2. substring matches landing inside a longer word
    titles = [r["title"] or "" for r in rows] + [c["title"] for c in cards]
    substring = []
    for kw in entries:
        k = kw.lower()
        if k in wb or not k.strip():
            continue
        words = {}
        for t in titles:
            low = t.lower()
            for m in re.finditer(re.escape(k), low):
                s, e = m.start(), m.end()
                before = low[s - 1] if s > 0 else " "
                after = low[e] if e < len(low) else " "
                if before.isalnum() or (after.isalnum() and k[-1].isalnum()):
                    ws = low.rfind(" ", 0, s) + 1
                    we = low.find(" ", e)
                    w = low[ws:we if we != -1 else len(low)]
                    words[w] = words.get(w, 0) + 1
        if words:
            top = sorted(words.items(), key=lambda x: -x[1])
            substring.append({"entry": kw, "matches": sum(words.values()),
                              "words": [f"{w} ({n})" for w, n in top[:8]]})

    # 3. scraped cards each entry dropped
    blocked = {}
    for c in cards:
        rj, kw = filters.reject_title(c["title"], cfg)
        if not rj:
            continue
        b = blocked.setdefault(kw, {"entry": kw, "cards": 0, "target_titles": 0, "examples": []})
        b["cards"] += 1
        if filters.is_relevant(c["title"], target):
            b["target_titles"] += 1
            if len(b["examples"]) < examples:
                b["examples"].append(c["title"])
    blocked = sorted(blocked.values(), key=lambda b: (-b["target_titles"], -b["cards"]))

    # 4. candidates
    stats = {}
    for r in read:
        for t in terms_of(r["title"], max_n):
            s = stats.setdefault(t, {"reads": 0, "positive": 0, "best": 0, "total": 0, "ex": []})
            s["reads"] += 1
            sc = r["match_score"] or 0
            s["total"] += sc
            s["best"] = max(s["best"], sc)
            if is_positive(r, pos):
                s["positive"] += 1
            if len(s["ex"]) < examples:
                s["ex"].append(f'{r["title"]} ({sc})')
    cands = {}
    for t, s in stats.items():
        if s["reads"] < min_reads or s["positive"] or s["best"] >= pos:
            continue
        if filters.reject_title(t, cfg)[0] or filters.is_relevant(t, target):
            continue  # already listed, or a target title family
        cands[t] = s
    # a phrase is redundant when one of its shorter parts is itself a candidate
    keep = {}
    for t, s in cands.items():
        parts = t.split()
        subs = {" ".join(parts[i:j]) for i in range(len(parts)) for j in range(i + 1, len(parts) + 1)} - {t}
        if not (subs & set(cands)):
            keep[t] = s
    candidates = []
    for t, s in sorted(keep.items(), key=lambda x: (-x[1]["reads"], x[0])):
        candidates.append({"term": t, "reads": s["reads"], "best_score": s["best"],
                           "mean_score": round(s["total"] / s["reads"], 1),
                           "unread_rows": sum(1 for r in unread if has_term(r["title"], t)),
                           "examples": s["ex"]})
    return {"summary": {"rows": len(rows), "read_and_scored": len(read),
                        "positive": len(positives), "unread": len(unread),
                        "archived_cards": len(cards), "entries": len(entries),
                        "positive_score": pos, "min_reads": min_reads},
            "collisions": collisions, "substring": substring,
            "blocked": blocked, "candidates": candidates}


def main():
    ap = argparse.ArgumentParser(description="Evidence check for the reject-title list (read-only).")
    ap.add_argument("--db", default=str(jobdb.DB_PATH))
    ap.add_argument("--cards", default=str(paths.DATA / "inbox" / "**" / "*.json"),
                    help="glob of scraped card files (default: everything under inbox/)")
    ap.add_argument("--positive-score", type=int, default=50)
    ap.add_argument("--min-reads", type=int, default=8)
    ap.add_argument("--max-words", type=int, default=3)
    ap.add_argument("--json", help="also write the full result to this file")
    a = ap.parse_args()
    res = audit(load_rows(a.db), load_cards(a.cards), config_loader.filters(),
                a.positive_score, a.min_reads, a.max_words)
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    s = res["summary"]
    print(f"Rows {s['rows']}, read and scored {s['read_and_scored']}, scored {s['positive_score']}+ "
          f"or applied {s['positive']}, unread {s['unread']}, archived cards {s['archived_cards']}, "
          f"list entries {s['entries']}.")
    print(f"\n1. Collisions (entry would hide a {s['positive_score']}+ or applied role): {len(res['collisions'])}")
    for c in res["collisions"]:
        print(f"  {c['entry']}: {c['count']}  e.g. " + "; ".join(
            f"{r['id']} {r['title']} ({r['score']})" for r in c["roles"]))
    print(f"\n2. Substring entries matching inside a longer word: {len(res['substring'])}")
    for c in res["substring"]:
        print(f"  {c['entry']}: {c['matches']}  words: {', '.join(c['words'])}")
    print("\n3. Archived cards dropped per entry (target = also matches relevance.title_any)")
    for b in res["blocked"]:
        ex = ("  e.g. " + "; ".join(b["examples"])) if b["examples"] else ""
        print(f"  {b['entry']}: {b['cards']} cards, {b['target_titles']} target{ex}")
    print(f"\n4. Candidates (>= {s['min_reads']} reads, none {s['positive_score']}+ or applied): "
          f"{len(res['candidates'])}")
    for c in res["candidates"]:
        print(f"  {c['term']}: reads {c['reads']}, best {c['best_score']}, mean {c['mean_score']}, "
              f"unread {c['unread_rows']}  e.g. {'; '.join(c['examples'][:2])}")


if __name__ == "__main__":
    main()
