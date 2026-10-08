#!/usr/bin/env bash
# Dry run of the whole pipeline with the fictional sample candidate (Jordan A. Bennett).
# It uses a throwaway data folder and a config folder holding only the shipped examples, so it
# never reads your own settings and never touches your tracker.
# Usage, from the project folder:   bash examples/dry_run.sh  [data folder]
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT_DIR="$(pwd)"
DATA="${1:-${TMPDIR:-/tmp}/jobagent-dry-run}"
MARK=".jobagent-dry-run"

# Safety: only ever clear a folder this script created (it carries the marker file).
case "$(cd "$(dirname "$DATA")" 2>/dev/null && pwd)/$(basename "$DATA")" in
  "/"|"$HOME"|"$ROOT_DIR"|"$ROOT_DIR"/*) echo "Refusing to use $DATA as the data folder."; exit 1;;
esac
if [ -e "$DATA" ]; then
  if [ -f "$DATA/$MARK" ]; then rm -rf "$DATA"
  elif [ -n "$(ls -A "$DATA" 2>/dev/null)" ]; then
    echo "Refusing to use $DATA: it is not empty and was not created by this script."; exit 1
  fi
fi
mkdir -p "$DATA/inbox" "$DATA/output/cvs" "$DATA/config"
touch "$DATA/$MARK"
cp config/*.example.md config/scoring_rubric.md "$DATA/config/"

export JOBAGENT_DATA_DIR="$DATA"
export JOBAGENT_CONFIG_DIR="$DATA/config"
export PYTHONDONTWRITEBYTECODE=1
echo "Data folder: $DATA (sample settings only)"
field() { python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(f'{k}: {d.get(k)}' for k in sys.argv[1:]))" "$@"; }

echo "== 1. create the tracker"
python3 lib/jobdb.py | head -1

echo "== 2. ingest the sample cards (expect 6 parsed, 4 kept, 2 rejected)"
cp examples/inbox/*.json "$DATA/inbox/"
python3 skills/job-ingest/scripts/scrape_ingest.py --as-of 2026-01-15 2>/dev/null | field parsed kept rejected reject_reasons

ID=$(python3 -c "import sys; sys.path.insert(0,'.'); from lib import jobdb; c=jobdb.connect(); print(c.execute(\"SELECT id FROM jobs WHERE company='Acme Analytics'\").fetchone()[0])")
echo "== 3. store the advert, score it, name the CV (job $ID)"
python3 skills/job-ingest/scripts/save_description.py --id "$ID" --file examples/advert_example.txt 2>/dev/null | field id desc_chars
python3 skills/job-match-score/scripts/save_score.py --id "$ID" --score 84 \
  --rationale "Met: launches, ABM, enablement, pipeline reporting. Gaps: line management." \
  --gaps '["line management"]' 2>/dev/null | field id score band status
CV=$(python3 skills/cv-tailor/scripts/cv_name.py --job-id "$ID" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['suggested_cv_file'])")
echo "CV file: $CV"

echo "== 4. build the sample CV and run the three checks"
python3 skills/uk-cv-writer/scripts/build_cv.py skills/uk-cv-writer/assets/cv-content-schema.json "$CV"
echo "-- check_cv (expect no FAIL; one page is a WARN for this short sample)"
python3 skills/uk-cv-writer/scripts/check_cv.py "$CV" examples/keywords_example.json | grep -E "^(FAIL|WARN)|tier1" || true
echo "-- check_grounding (expect 0 unsupported)"
python3 skills/uk-cv-writer/scripts/check_grounding.py "$CV" examples/master_profile.sample.md | grep Summary
echo "-- workflow_check (expect pass)"
python3 skills/cv-verify/scripts/workflow_check.py "$CV" --market uk 2>/dev/null | field verdict fails warns

echo "== 5. register, export, verify, report"
python3 skills/cv-tailor/scripts/register_cv.py --id "$ID" --cv-file "$CV" 2>/dev/null | field id status cv_file
python3 skills/cv-tailor/scripts/export_pdf.py --docx "$CV" | field pdf
python3 skills/cv-verify/scripts/record_verdict.py --id "$ID" --result pass --rescore 82 2>/dev/null | field id status
python3 skills/app-tracker/scripts/export_workbook.py 2>/dev/null
python3 skills/job-pipeline/scripts/pipeline_status.py 2>/dev/null | grep -E "verified \(|advert not read"
echo "Done. The data folder $DATA can be deleted when you no longer need it."
