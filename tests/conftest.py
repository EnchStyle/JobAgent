"""Test isolation: the tests read only the shipped .example.md settings and write only to a
temporary data folder, so they never touch your own config files or jobs.db."""
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_cfg = Path(tempfile.mkdtemp(prefix="jobagent-test-config-"))
for f in (ROOT / "config").glob("*.example.md"):
    shutil.copy(f, _cfg / f.name)
shutil.copy(ROOT / "config" / "scoring_rubric.md", _cfg / "scoring_rubric.md")
os.environ["JOBAGENT_CONFIG_DIR"] = str(_cfg)
os.environ["JOBAGENT_DATA_DIR"] = tempfile.mkdtemp(prefix="jobagent-test-data-")
