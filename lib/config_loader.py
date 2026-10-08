"""Load machine-readable config from the fenced ```yaml blocks inside config/*.md.

The .md files are the single human-editable source of truth; code reads only their yaml blocks.
PyYAML is required (pip install -r requirements.txt).
"""
import re
import sys
import functools
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.paths import CONFIG

try:
    import yaml
except ImportError:  # a clear message instead of a silent install or a fragile fallback parser
    sys.exit("JobAgent needs PyYAML: run  pip install -r requirements.txt  (or pip install pyyaml)")


def _extract_blocks(text: str):
    blocks = re.findall(r"```yaml\s*\n(.*?)```", text, re.DOTALL)
    if blocks:
        return blocks
    # Robustness: if a config file's closing ``` fence is missing (e.g. a truncated write on the
    # mounted filesystem), a strict match would find NO block and silently return empty config,
    # which would disable every filter. Fall back to parsing the opening ```yaml through EOF so a
    # truncated tail costs at most a few trailing lines, never the whole config.
    m = re.search(r"```yaml\s*\n(.*)\Z", text, re.DOTALL)
    return [m.group(1)] if m else []


def _merge_blocks(text: str) -> dict:
    merged: dict = {}
    for block in _extract_blocks(text):
        data = yaml.safe_load(block) or {}
        if isinstance(data, dict):
            _deep_update(merged, data)
    return merged


def _deep_update(base: dict, new: dict):
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


@functools.lru_cache(maxsize=None)
def _load_cached(name: str) -> dict:
    return _load(name)


def load(name: str) -> dict:
    """Read config/<name> (cached per process; returns a fresh copy each call)."""
    import copy
    return copy.deepcopy(_load_cached(name))


def _load(name: str) -> dict:
    """Read config/<name>. Personal files (for example application_rules.md) are not shipped;
    when one is missing, its <name>.example.md twin is read instead and a warning is printed,
    so a fresh clone runs end to end before the user has filled in their own details."""
    path = CONFIG / name
    if not path.is_file():
        example = CONFIG / name.replace(".md", ".example.md")
        if example.is_file():
            print(f"[config] {name} not found, using {example.name}; copy it to {name} and "
                  f"fill in your own details", file=sys.stderr)
            path = example
    return _merge_blocks(path.read_text(encoding="utf-8"))


def sources() -> dict:
    return load("sources.md")


def filters() -> dict:
    return load("filters.md")


def scoring() -> dict:
    return load("scoring_rubric.md")


def application_rules() -> dict:
    return load("application_rules.md")


def contact() -> dict:
    """Contact details from config/application_rules.md: {"email", "linkedin", "website",
    "phones": {market: number}} (contact.phones is keyed by the market codes in filters.md)."""
    c = dict((application_rules() or {}).get("contact") or {})
    phones = {str(k).lower(): str(v) for k, v in (c.get("phones") or {}).items() if v}
    return {"email": c.get("email") or "", "linkedin": c.get("linkedin") or "",
            "website": c.get("website") or "", "phones": phones}


def candidate() -> dict:
    """The candidate's name and the file-name stem used for CVs and cover letters, from the
    `candidate` block of config/application_rules.md. Example: {"name": "Jordan A. Bennett",
    "file_stem": "Jordan-Bennett"} gives Jordan-Bennett-CV-<Brand>.pdf."""
    c = (application_rules() or {}).get("candidate") or {}
    name = (c.get("name") or "Your Name").strip()
    stem = (c.get("file_stem") or re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-") or "Candidate")
    return {"name": name, "file_stem": stem}


if __name__ == "__main__":
    import json
    print("FILTERS:", json.dumps(filters(), indent=2)[:800])
    print("SOURCES keys:", list(sources().keys()))
    print("SCORING:", json.dumps(scoring(), indent=2)[:400])
