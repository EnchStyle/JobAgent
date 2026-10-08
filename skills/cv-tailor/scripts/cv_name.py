#!/usr/bin/env python3
"""Deterministic CV output filename for cv-tailor.

Prints the project-relative path for a job's tailored CV so the file on disk and jobs.cv_file
always agree:  output/cvs/<Name>-CV-<Brand>[-<RoleSlug>]-<jobid>.docx
(<Name> is candidate.file_stem in config/application_rules.md, for example Jordan-Bennett)
export_pdf.py later strips the trailing -<jobid> to make the send-ready PDF name, so a role slug
given here carries through to the PDF automatically (never pass it to export_pdf.py as well).

It also reports other CVs already on file for the same brand. When there are any, pass
--role-slug with a short word for this role (for example -DataAnalyst, -ProductLead) so the PDFs
do not overwrite each other.

Usage:
  cv_name.py --job-id 12
  cv_name.py --job-id 12 --company "Acme Analytics"      # override a missing or messy company name
  cv_name.py --job-id 12 --role-slug MobileApp
Read-only.
"""
import re
import sys
import json
import argparse
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import jobdb, paths, config_loader

# Whole-word legal-entity / staffing-agency tokens stripped when deriving a short brand name
# from a raw company string (e.g. "Example GmbH" -> "Example", "Acme Business Ltd." -> "Acme").
# Not exhaustive by design: an ambiguous or multi-word brand can still be steered with --company.
_ENTITY_WORDS = {
    "ab", "ag", "sa", "bv", "oy", "as",
    "ltd", "ltd.", "limited", "llc", "inc", "inc.", "plc", "gmbh", "llp",
    "group", "recruitment",
    "resourcing", "solutions", "consulting", "company", "co", "co.", "corp",
    "corporation", "holdings", "holding",
}


def _ascii_fold(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")


def _slug(s, maxlen=40):
    s = _ascii_fold(s)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return (s[:maxlen].strip("-")) or "na"


def _company_brand(company, maxlen=24):
    """Short CamelCase brand token from a raw company string, legal-entity words dropped.
    E.g. "Example GmbH" -> "Example"; "EXAMPLE Group" -> "Example";
    "Acme Recruitment Solutions Ltd" -> "Acme"."""
    words = re.findall(r"[A-Za-z0-9]+", _ascii_fold(company))
    kept = [w for w in words if w.lower() not in _ENTITY_WORDS] or words
    brand = "".join(w[:1].upper() + w[1:] for w in kept)
    return (brand[:maxlen] or "Employer")


def suggested_cv_file(company, job_id, role_slug=None):
    """output/cvs/<Name>-CV-<CompanyBrand>[-<RoleSlug>]-<jobid>.docx (project-relative)."""
    brand = _company_brand(company)
    tail = f"-{role_slug.strip().strip('-')}" if role_slug else ""
    return f"output/cvs/{config_loader.candidate()['file_stem']}-CV-{brand}{tail}-{job_id}.docx"


def same_brand_files(company, job_id):
    """Other CVs for this brand, on disk or recorded in jobs.db (a collision risk for the PDF name)."""
    brand = _company_brand(company)
    prefix = f"{config_loader.candidate()['file_stem']}-CV-{brand}"
    names = set()
    if paths.CVS.is_dir():
        for f in paths.CVS.glob(prefix + "*"):
            if f.suffix.lower() in (".docx", ".pdf"):
                names.add(f.name)
    try:
        con = jobdb.connect()
        for (cv,) in con.execute("SELECT cv_file FROM jobs WHERE cv_file LIKE ?", (f"%{prefix}%",)):
            names.add(Path(cv).name)
        con.close()
    except Exception:
        pass
    return sorted(n for n in names if not re.search(rf"-{job_id}\.docx$", n))


def main():
    ap = argparse.ArgumentParser(description="Deterministic CV output-filename for a job.")
    ap.add_argument("--job-id", type=int, required=True, help="jobs.id primary key")
    ap.add_argument("--company", help="override target employer (else read from the DB row)")
    ap.add_argument("--role", help="ignored (kept so older calls still work)")
    ap.add_argument("--role-slug", help="short word appended to disambiguate a repeat company")
    args = ap.parse_args()

    if args.company:
        company = args.company
    else:
        con = jobdb.connect()
        try:
            row = jobdb.get_by_id(con, args.job_id)
            if row is None:
                raise SystemExit(f"No job with id {args.job_id}")
            company = row["company"]
        finally:
            con.close()

    others = same_brand_files(company, args.job_id)
    rel = suggested_cv_file(company, args.job_id, args.role_slug)
    # Absolute path to write to (inside the data folder, see JOBAGENT_DATA_DIR); register_cv.py
    # stores it relative to that folder.
    result = {"suggested_cv_file": str(paths.data_path(rel)), "relative_path": rel,
              "other_cvs_for_this_brand": others}
    if others and not args.role_slug:
        result["advice"] = ("This brand already has CVs on file; rerun with --role-slug <Word> "
                            "so the PDF names stay unique.")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
