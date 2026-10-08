"""export_pdf.py : make a send-ready PDF twin of a tailored CV .docx.

Every CV is delivered as a PAIR in output/cvs:
  - the .docx keeps the tracking name  <Name>-CV-<Company>-<jobid>.docx
    (the trailing <jobid> = jobs.id, so the pipeline and DB can map it), and
  - a PDF twin  <Name>-CV-<Company>.pdf  with the job id STRIPPED, so the
    file the candidate actually sends to an employer has a clean, human name (no
    weird trailing number). The pair sorts next to each other by shared prefix.

Collision rule: when one company has more than one CV, give the role slug to cv_name.py so
the .docx is named <Name>-CV-<Company>-<RoleSlug>-<jobid>.docx; this script then
produces <Name>-CV-<Company>-<RoleSlug>.pdf by itself. --role-slug here is only for
an older .docx whose name has no slug.

The PDF is rendered with LibreOffice (soffice), so it is a TEXT-based PDF (selectable,
ATS-safe) with fonts embedded, which also guarantees accented characters render on any
machine. Requires `soffice` on PATH.

Usage:
  python3 skills/cv-tailor/scripts/export_pdf.py --docx output/cvs/Jordan-Bennett-CV-Acme-173.docx
  python3 skills/cv-tailor/scripts/export_pdf.py --docx output/cvs/Jordan-Bennett-CV-Acme-118.docx --role-slug DataAnalyst
Prints JSON {docx, pdf}.
"""
import re
import sys
import json
import shutil
import argparse
import tempfile
import subprocess
from pathlib import Path


def clean_pdf_name(docx_path, role_slug=None):
    """<Name>-CV-<Company>-<jobid>.docx -> <Name>-CV-<Company>[-<slug>].pdf"""
    stem = Path(docx_path).stem
    base = re.sub(r"-\d+$", "", stem)  # strip the trailing -<jobid>
    if role_slug:
        base = f"{base}-{role_slug.strip().strip('-')}"
    return base + ".pdf"


def export(docx_path, role_slug=None, soffice="soffice"):
    docx = Path(docx_path).resolve()
    if not docx.is_file():
        raise SystemExit(f"no such docx: {docx}")
    out_pdf = docx.parent / clean_pdf_name(docx, role_slug)
    with tempfile.TemporaryDirectory() as td:
        # soffice names the output by the docx basename; convert into a temp dir then rename.
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", td, str(docx)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        produced = Path(td) / (docx.stem + ".pdf")
        if not produced.is_file():
            raise SystemExit("soffice did not produce a PDF (is LibreOffice installed?)")
        shutil.move(str(produced), str(out_pdf))
    return {"docx": str(docx), "pdf": str(out_pdf)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True, help="path to the tailored CV .docx")
    ap.add_argument("--role-slug", default=None,
                    help="short word to disambiguate when a company has more than one CV")
    ap.add_argument("--soffice", default="soffice", help="LibreOffice binary (default: soffice)")
    a = ap.parse_args(argv)
    print(json.dumps(export(a.docx, a.role_slug, a.soffice), ensure_ascii=False))


if __name__ == "__main__":
    main()
