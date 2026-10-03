#!/usr/bin/env bash
# End-to-end test on SYNTHETIC data in a scratch copy of the repository.
# Usage: bash tests/run_smoke.sh [scratch_dir]
# Nothing here touches the real data folders of the repository you run it from.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${1:-$(mktemp -d)}/makd-smoke"
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
(cd "$REPO" && tar --exclude=./data --exclude=./paper/figures --exclude=./paper/tables -cf - .) | (cd "$SCRATCH" && tar -xf -)
mkdir -p "$SCRATCH"/data/{raw,wonder,processed} "$SCRATCH"/paper/{figures,tables}
cd "$SCRATCH"
export MAKD_SMOKE=1
python tests/make_synthetic.py --root . --n-per-year "${N_PER_YEAR:-60000}"
python code/02_parse.py
python code/03_wonder.py
python code/04_qa.py > /dev/null
python code/05_train.py
python code/06_evaluate.py
python code/07_figures.py
python code/08_manuscript.py
echo "smoke run complete: $SCRATCH"
