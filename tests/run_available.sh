#!/usr/bin/env bash
# Run the available-data design end to end; safe to re-run after an interruption
# (parse is skipped when its outputs exist; training and evaluation resume from disk).
set -euo pipefail
cd "$(dirname "$0")/.."
export MAKD_CONFIG=config_available.yaml OMP_NUM_THREADS=1
P=data/processed_avail
mkdir -p $P
[ -f $P/parse_log.json ] || python3 code/02_parse.py
python3 code/03_wonder.py
python3 code/04_qa.py > $P/qa_stdout.txt
grep -q "Checks flagged: 0" $P/qa_report.txt || { echo "QA flagged problems; see $P/qa_report.txt"; exit 1; }
OMP_NUM_THREADS=2 python3 code/05_train.py
python3 code/06_evaluate.py
python3 code/07_figures.py
python3 code/08_manuscript.py
python3 code/09_summary.py
echo "available-data run complete"
