"""Resolve JobAgent project paths from anywhere (skills, lib, root).

The project root is the directory that contains both `config/` and `skills/`.
lib/ lives directly under the root, so parents[1] of this file is the root, but we
also walk up to find the markers so scripts keep working if the tree is relocated.
"""
import os
from pathlib import Path


def find_root(start: str | None = None) -> Path:
    p = Path(start or __file__).resolve()
    for anc in [p] + list(p.parents):
        if (anc / "config").is_dir() and (anc / "skills").is_dir():
            return anc
    # Fallback: lib/ is directly under the project root.
    return Path(__file__).resolve().parents[1]


ROOT = find_root()
# JOBAGENT_CONFIG_DIR points the scripts at another config folder (the dry run and the tests use
# a folder holding only the shipped .example.md files, so your own settings are never read).
CONFIG = Path(os.environ["JOBAGENT_CONFIG_DIR"]).expanduser() if os.environ.get("JOBAGENT_CONFIG_DIR") else ROOT / "config"
PROFILE = ROOT / "profile" / "master_profile.md"
# Working data (tracker, scraped cards, documents, logs) lives in the project folder by default.
# Set the environment variable JOBAGENT_DATA_DIR to keep it elsewhere, for example for a dry run
# with the sample data that should not touch your real tracker.
DATA = Path(os.environ["JOBAGENT_DATA_DIR"]).expanduser() if os.environ.get("JOBAGENT_DATA_DIR") else ROOT
DB_PATH = DATA / "jobs.db"
INBOX = DATA / "inbox"
OUTPUT = DATA / "output"
CVS = OUTPUT / "cvs"
COVER_LETTERS = OUTPUT / "cover_letters"
LOGS = DATA / "logs"


def data_path(rel) -> Path:
    """Absolute path of a file stored in jobs.db as a path relative to the data folder."""
    p = Path(rel)
    return p if p.is_absolute() else DATA / p


def to_relative(path) -> str:
    """Path to store in jobs.db: relative to the data folder when the file is inside it."""
    p = Path(path)
    try:
        return str(p.resolve().relative_to(DATA.resolve()))
    except (ValueError, OSError):
        return str(path)


def ensure_dirs() -> None:
    for d in (DATA, INBOX, OUTPUT, CVS, COVER_LETTERS, LOGS):
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print("ROOT:", ROOT)
    for name in ("CONFIG", "PROFILE", "DB_PATH", "INBOX", "CVS", "COVER_LETTERS", "LOGS"):
        print(f"{name}: {globals()[name]}")
