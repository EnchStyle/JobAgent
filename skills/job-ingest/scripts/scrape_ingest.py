"""Ingest scraped job cards saved by the browser step.

Reads inbox/scrape_*.json (each {"source": ..., "cards": [...]}, optionally "remote": "remote" when
the search itself was remote-filtered), normalizes each card, applies the hard filters, dedupes,
inserts survivors as status found, logs to logs/, and prints a JSON report.

--pattern limits the run to one scrape's files (e.g. "scrape_*_20260115.json").
--as-of YYYY-MM-DD anchors relative posted dates ("3 days ago") and the freshness window to the
day the cards were scraped. Use it whenever you ingest files from an earlier day.
"""
import sys
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import jobdb, paths, config_loader
import filters
import normalize as norm


def run(inbox_dir=None, db_path=None, pattern="scrape_*.json", as_of=None, archive=True):
    paths.ensure_dirs()
    today = datetime.date.fromisoformat(as_of) if as_of else None
    cfg = config_loader.filters()
    con = jobdb.init_db(db_path)
    jobdb.begin_batch(con)  # one commit per run, not per card (end_batch in the finally below)
    try:
        return _run(con, cfg, today, inbox_dir, pattern, archive)
    finally:
        jobdb.end_batch(con)


def _run(con, cfg, today, inbox_dir, pattern, archive):
    inbox_dir = Path(inbox_dir or paths.INBOX)
    rep = {"files": 0, "parsed": 0, "kept": 0, "review": 0, "inserted": 0, "duplicate": 0,
           "rejected": 0, "skipped_files": 0, "reject_reasons": {}, "by_source": {}}
    warned = set()
    processed = []
    for f in sorted(inbox_dir.glob(pattern)):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A truncated or empty inbox file (the mount can truncate large writes) must not
            # kill the whole run. Skip it and record it so the page can be re-scraped.
            rep["skipped_files"] = rep.get("skipped_files", 0) + 1
            continue
        if not isinstance(d, dict):
            rep["skipped_files"] = rep.get("skipped_files", 0) + 1
            continue
        src = d.get("source")
        cards = d.get("cards") or []
        default_remote = d.get("remote")
        rep["files"] += 1
        processed.append(f)
        bs = rep["by_source"].setdefault(src, {"parsed": 0, "kept": 0, "inserted": 0, "duplicate": 0,
                                                "rejected": 0, "reject_reasons": {}})
        for c in cards:
            rep["parsed"] += 1
            bs["parsed"] += 1
            if isinstance(c, (list, tuple)) and src == "linkedin":
                c = dict(zip(norm.LINKEDIN_ARRAY_KEYS, c))
            if default_remote and isinstance(c, dict) and not c.get("remote"):
                c = dict(c, remote=default_remote)
            try:
                j = norm.normalize(src, c, today)
            except ValueError:
                # A source with no normaliser in normalize.py: count it loudly instead of
                # dropping the card in silence.
                why = f"no_normalizer:{src}"
                rep["rejected"] += 1
                bs["rejected"] += 1
                rep["reject_reasons"][why] = rep["reject_reasons"].get(why, 0) + 1
                bs["reject_reasons"][why] = bs["reject_reasons"].get(why, 0) + 1
                if why not in warned:
                    warned.add(why)
                    print(f"[ingest] WARNING: no normaliser for source '{src}' in {f.name}; its cards "
                          f"were not ingested. Add normalize_{src}() to normalize.py (see AGENTS.md).",
                          file=sys.stderr)
                continue
            r = filters.classify(j, cfg, today)
            if not r["keep"]:
                rep["rejected"] += 1
                bs["rejected"] += 1
                rep["reject_reasons"][r["reason"]] = rep["reject_reasons"].get(r["reason"], 0) + 1
                bs["reject_reasons"][r["reason"]] = bs["reject_reasons"].get(r["reason"], 0) + 1
                continue
            rep["kept"] += 1
            bs["kept"] += 1
            if r["review"]:
                rep["review"] += 1
            j["work_mode"] = r.get("work_mode") or j.get("work_mode")
            j["salary_unknown"] = r.get("salary_unknown", j.get("salary_unknown", 0))
            flags = r.get("flags", [])
            if flags:
                note = j.get("notes") or ""
                j["notes"] = (note + " | " if note else "") + "flags:" + ",".join(flags)
            dups = jobdb.possible_duplicates(con, j.get("company"), j.get("title"))
            if dups:
                note = j.get("notes") or ""
                j["notes"] = (note + " | " if note else "") + "possible_duplicate_of:" + ",".join(str(d["id"]) for d in dups)
            if jobdb.insert_job(con, j):
                rep["inserted"] += 1
                bs["inserted"] += 1
                if dups:
                    rep["possible_duplicates"] = rep.get("possible_duplicates", 0) + 1
            else:
                rep["duplicate"] += 1
                bs["duplicate"] += 1
    if archive and processed:
        # Ingested files move to inbox/_archive_<YYYYMM>/, so the inbox shows only what is still
        # waiting. Unreadable files stay put (counted in skipped_files) so they can be re-scraped.
        con.commit()
        dest = inbox_dir / ("_archive_" + datetime.date.today().strftime("%Y%m"))
        dest.mkdir(exist_ok=True)
        for f in processed:
            target = dest / f.name
            if not target.exists():
                try:
                    f.rename(target)
                except OSError:
                    pass
        rep["archived_files"] = len(processed)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox-dir")
    ap.add_argument("--db")
    ap.add_argument("--pattern", default="scrape_*.json")
    ap.add_argument("--as-of", default=None, help="scrape date YYYY-MM-DD when ingesting older files")
    ap.add_argument("--keep-inbox", action="store_true", help="leave ingested files in inbox/")
    args = ap.parse_args()
    rep = run(args.inbox_dir, args.db, args.pattern, args.as_of, archive=not args.keep_inbox)
    if args.as_of:
        rep["as_of"] = args.as_of
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        (Path(paths.LOGS) / ("scrape_ingest_" + ts + ".log")).write_text(
            json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
