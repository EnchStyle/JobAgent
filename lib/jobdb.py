"""Canonical jobs.db contract for JobAgent.

Single owner of the database schema and all reads/writes. Every skill imports from here
so there is exactly one dedupe rule, one status vocabulary, and one insert path.

Dedupe: prefer the source-native job_id; otherwise a normalized company+title+location key.
Enforced by a UNIQUE index so re-runs cannot create a second row for a role already tracked
in ANY status.

Storage note: the DB lives on a mounted folder that cannot back WAL or unlink journal files,
so connect() uses TRUNCATE journaling. Do not change it to WAL/DELETE (raises disk I/O error).
"""
import sys
import re
import json
import contextlib
import sqlite3
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.paths import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  dedupe_key        TEXT UNIQUE NOT NULL,
  job_id            TEXT,
  source            TEXT NOT NULL,
  title             TEXT,
  company           TEXT,
  location          TEXT,
  work_mode         TEXT,
  salary_min        REAL,
  salary_max        REAL,
  salary_currency   TEXT,
  salary_period     TEXT,
  salary_unknown    INTEGER DEFAULT 0,
  url               TEXT,
  date_found        TEXT,
  date_posted       TEXT,
  match_score       INTEGER,
  score_breakdown   TEXT,
  cv_file           TEXT,
  cover_letter_file TEXT,
  status            TEXT NOT NULL DEFAULT 'found',
  date_applied      TEXT,
  gmail_thread_id   TEXT,
  notes             TEXT,
  description       TEXT,
  closing_date      TEXT,
  rescore           INTEGER,
  cv_sent           TEXT,
  confirmation      TEXT,
  created_at        TEXT,
  updated_at        TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedupe  ON jobs(dedupe_key);
CREATE INDEX        IF NOT EXISTS idx_jobs_status  ON jobs(status);
CREATE INDEX        IF NOT EXISTS idx_jobs_source  ON jobs(source);
"""

STATUSES = [
    "found", "scored", "cv_generated", "verified", "applied",
    "blocked_login", "rejected", "interview", "closed",
]

INSERT_COLS = [
    "dedupe_key", "job_id", "source", "title", "company", "location", "work_mode",
    "salary_min", "salary_max", "salary_currency", "salary_period", "salary_unknown",
    "url", "date_found", "date_posted", "status", "gmail_thread_id", "notes", "description",
    "closing_date", "created_at", "updated_at",
]


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _today():
    return datetime.date.today().isoformat()


# Bulk writes: on a synced or mounted folder every commit is a slow disk sync, so a script that
# writes hundreds of rows opens a batch, and the row functions below then commit once at the end
# instead of once per row (hundreds of rows took over a minute with a commit per row).
_BATCH = set()


def begin_batch(con):
    _BATCH.add(id(con))


def end_batch(con, ok=True):
    """Close a batch: commit what was written (ok=True) or undo it. Call it in a finally block,
    so a crash still saves the rows written so far."""
    _BATCH.discard(id(con))
    if ok:
        con.commit()
    else:
        con.rollback()


@contextlib.contextmanager
def batch(con):
    """`with jobdb.batch(con):` commits once at the end, also when an error stops the loop."""
    begin_batch(con)
    try:
        yield con
    finally:
        end_batch(con)


def _commit(con):
    if id(con) not in _BATCH:
        con.commit()


def connect(db_path=None):
    db = Path(db_path or DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    _BATCH.discard(id(con))  # a new connection never inherits a batch left open by an old one
    con.row_factory = sqlite3.Row
    # Mounted folder cannot back WAL shared-memory nor unlink journals; TRUNCATE is the
    # one durable rollback mode that works here. Do not switch to WAL or DELETE.
    con.execute("PRAGMA journal_mode=TRUNCATE;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    # Create the tables on first use, so no script fails with "no such table: jobs" on a fresh
    # clone. CREATE ... IF NOT EXISTS makes this a no-op on an existing database.
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone() is None:
        con.executescript(SCHEMA)
        con.commit()
    _migrate(con)
    return con


def init_db(db_path=None):
    con = connect(db_path)
    con.executescript(SCHEMA)
    con.commit()
    _migrate(con)
    return con


def _norm(s):
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip()


def dedupe_key(source, job_id, company, title, location):
    if job_id not in (None, "", 0):
        return f"id:{source}:{str(job_id).strip()}"
    return "k:" + "|".join(_norm(x) for x in (company, title, location))


def job_exists(con, key):
    return con.execute("SELECT 1 FROM jobs WHERE dedupe_key=?", (key,)).fetchone() is not None


def insert_job(con, job):
    """Insert one normalized job dict. Returns 1 if inserted, 0 if it was a duplicate."""
    key = job.get("dedupe_key") or dedupe_key(
        job.get("source"), job.get("job_id"), job.get("company"), job.get("title"), job.get("location")
    )
    now = _now()
    vals = {
        "dedupe_key": key,
        "job_id": (str(job["job_id"]) if job.get("job_id") not in (None, "") else None),
        "source": job.get("source"),
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "work_mode": job.get("work_mode"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_currency": job.get("salary_currency"),
        "salary_period": job.get("salary_period"),
        "salary_unknown": int(job.get("salary_unknown", 0) or 0),
        "url": job.get("url"),
        "date_found": job.get("date_found") or _today(),
        "date_posted": job.get("date_posted"),
        "status": job.get("status", "found"),
        "gmail_thread_id": job.get("gmail_thread_id"),
        "notes": job.get("notes"),
        "description": job.get("description"),
        "closing_date": job.get("closing_date"),
        "created_at": now,
        "updated_at": now,
    }
    placeholders = ",".join("?" for _ in INSERT_COLS)
    cur = con.execute(
        f"INSERT OR IGNORE INTO jobs ({','.join(INSERT_COLS)}) VALUES ({placeholders})",
        [vals[c] for c in INSERT_COLS],
    )
    _commit(con)
    return cur.rowcount


def set_score(con, job_pk, score, breakdown, status="scored"):
    payload = breakdown if isinstance(breakdown, str) else json.dumps(breakdown, ensure_ascii=False)
    con.execute(
        "UPDATE jobs SET match_score=?, score_breakdown=?, status=?, updated_at=? WHERE id=?",
        (int(score), payload, status, _now(), job_pk),
    )
    _commit(con)


def update_status(con, job_pk, status, **fields):
    assert status in STATUSES, f"unknown status {status}"
    if status == "rejected" and not (fields.get("notes") or "").strip():
        row = con.execute("SELECT status, score_breakdown FROM jobs WHERE id=?", (job_pk,)).fetchone()
        if row is not None and row["status"] != "rejected" and not row["score_breakdown"]:
            # A role is only rejected for fit from a full read (save_score.py) or with a stated
            # reason. A keyword screen or a title score is never a reason.
            raise ValueError("rejecting an unread role needs a stated reason (notes=...) or a "
                             "full-read score via save_score.py")
    sets = ["status=?", "updated_at=?"]
    args = [status, _now()]
    for k, v in fields.items():
        sets.append(f"{k}=?")
        args.append(v)
    args.append(job_pk)
    con.execute(f"UPDATE jobs SET {','.join(sets)} WHERE id=?", args)
    _commit(con)


def get_by_status(con, status):
    return con.execute("SELECT * FROM jobs WHERE status=? ORDER BY id", (status,)).fetchall()


def get_by_id(con, job_pk):
    return con.execute("SELECT * FROM jobs WHERE id=?", (job_pk,)).fetchone()


# Columns added after the first release; older databases gain them on first use.
_ADDED_COLUMNS = {
    "description": "TEXT",
    "closing_date": "TEXT",      # YYYY-MM-DD from the advert; queues sort by it
    "rescore": "INTEGER",        # cv-verify's independent re-score (match_score is kept)
    "cv_sent": "TEXT",           # which CV file actually went with the application
    "confirmation": "TEXT",      # how the application was confirmed: page, email, board, none
}


def _migrate(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(jobs)")}
    changed = False
    for name, kind in _ADDED_COLUMNS.items():
        if name not in cols:
            con.execute(f"ALTER TABLE jobs ADD COLUMN {name} {kind}")
            changed = True
    if changed:
        con.commit()


_ENTITY = re.compile(r"\b(ltd|limited|plc|llc|inc|gmbh|ab|ag|sa|bv|group|holdings?|recruitment|the)\b")


def _norm_company(s):
    return re.sub(r"\s+", " ", _ENTITY.sub(" ", _norm(s))).strip()


def _same_title(a, b):
    """Equal titles, or one is the other plus a suffix ("senior product owner" and "senior
    product owner payments"), for titles of two words or more. A flag only."""
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    return len(short.split()) >= 2 and long_.startswith(short + " ")


def possible_duplicates(con, company, title, exclude_id=None, days=60):
    """Rows that look like the same role: same employer and title after normalisation (legal-entity
    words dropped), found within `days` days, on any board. Used at ingest (flag) and before
    applying (repeat-application guard)."""
    c, t = _norm_company(company), _norm(title)
    if not c or not t:
        return []
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    out = []
    for r in con.execute("SELECT id, company, title, status, source, date_found FROM jobs "
                         "WHERE (date_found IS NULL OR date_found >= ?)", (since,)):
        if exclude_id is not None and r["id"] == exclude_id:
            continue
        if _norm_company(r["company"]) == c and _same_title(_norm(r["title"]), t):
            out.append({"id": r["id"], "status": r["status"], "source": r["source"]})
    return out


def applied_to_employer(con, company):
    """Earlier applications to the same employer (any role), newest first."""
    c = _norm_company(company)
    if not c:
        return []
    return [{"id": r["id"], "title": r["title"], "status": r["status"], "date_applied": r["date_applied"]}
            for r in con.execute("SELECT id, company, title, status, date_applied FROM jobs "
                                 "WHERE status IN ('applied','interview','closed') AND date_applied IS NOT NULL "
                                 "ORDER BY date_applied DESC")
            if _norm_company(r["company"]) == c]


def set_description(con, job_pk, description, **fields):
    sets = ["description=?", "updated_at=?"]
    args = [description, _now()]
    for k, v in fields.items():
        sets.append(f"{k}=?")
        args.append(v)
    args.append(job_pk)
    con.execute(f"UPDATE jobs SET {','.join(sets)} WHERE id=?", args)
    _commit(con)


UNREAD_REJECT_MARKERS = ("keyword screen", "not read by claude", "below shortlist", "ranking cut-off")


def unread_rejections(con):
    """Rejected rows with no full-read score whose notes say they were dropped unread (a keyword
    screen, a ranking cut-off). These should be zero: such rows go back to `found` and are read."""
    rows = con.execute("SELECT id, title, company, notes FROM jobs WHERE status='rejected' "
                       "AND (score_breakdown IS NULL OR score_breakdown='')").fetchall()
    out = []
    for r in rows:
        n = (r["notes"] or "").lower()
        if "re-scored" in n or re.search(r"reviewed \d{4}-\d{2}-\d{2}: still rejected", n):
            continue  # read later, or reviewed and kept rejected with a stated reason
        if any(m in n for m in UNREAD_REJECT_MARKERS):
            out.append(r)
    return out


def counts(con):
    rows = con.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status").fetchall()
    return {r["status"]: r["n"] for r in rows}


def total(con):
    return con.execute("SELECT COUNT(*) n FROM jobs").fetchone()["n"]


if __name__ == "__main__":
    con = init_db()
    print("Initialized", DB_PATH)
    print("Statuses:", STATUSES)
    print("Row count:", total(con))
    print("Counts by status:", counts(con))
