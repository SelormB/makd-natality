**Status: DRAFT v0.4.0 (2026-10-07). Available-data results complete in `paper/available/`. Record layout verified against all nine User Guides (2016–2024). Real data verified (2016, 2017, 2023, 2024 files match NVSR totals exactly; WONDER reconciles within 0.01 pt). Current analysis: available-data design (train 2016, 2017, 2023; test 2024) in `paper/available/`; pilot in `paper/pilot/`; main 2016–2022 design pending the remaining downloads. Not for citation.**

# MAKD-Natality

Missingness-aware knowledge distillation for low birthweight (LBW) and preterm birth (PTB) prediction when U.S. states leave different birth-certificate items blank.

A teacher model is trained on births with complete prenatal care onset, pre-pregnancy BMI, WIC, smoking, education, and payer. Students are distilled to work under each state's real item-missingness rates (from CDC WONDER), imposed on national records. Models are compared on sensitivity, positive predictive value, calibration, and subgroup performance, the measures that matter when the outcome is rare.

Author: Selorm Buaka, University of Northern Colorado. See `AUTHORS.json`.

## Why semi-synthetic
Since 2005 the NCHS public-use natality files carry no state identifier, so a state's missingness cannot be read off the record-level data. This project takes each state's item-unknown rates from CDC WONDER and simulates them (MCAR and covariate-dependent MAR) on complete national records, plus one fully real check on records with naturally occurring missingness. See `docs/LIMITATIONS.md`.

## Run it

Requirements: Python 3.10+; `pip install -r requirements.txt`. Real-data runs need roughly 32 GB RAM and benefit from many cores (HPC recommended).

```
python code/00_check_layout.py    # verify field positions against each year's User Guide (docs/sources/user_guides)
python code/01_fetch.py           # NCHS public-use zips, 2016–2024 (~230 MB each), provenance logged
# manual: export 6 files from CDC WONDER into data/wonder/  (docs/WONDER_EXPORT_GUIDE.md)
python code/02_parse.py           # fixed-width -> cohort parquet per year
python code/03_wonder.py          # state x year x item unknown rates
python code/04_qa.py              # READ data/processed/qa_report.txt before going further
python code/05_train.py           # teacher, students, baselines
python code/06_evaluate.py        # metrics by state, bootstrap, subgroups, natural missingness
python code/07_figures.py         # paper/figures/
python code/08_manuscript.py      # paper/manuscript.md from paper/stats.json
python code/09_summary.py         # paper/summary.md: headline comparisons from the tables
python code/10_preprint_pdf.py    # paper/MAKD-Natality_preprint_<run>.pdf (pandoc + XeLaTeX; DRAFT watermark until final)
```

Every modeling decision is in `config.yaml`. Items marked VERIFY are provisional.

Available-data design (2016, 2017, 2023 → 2024): `bash tests/run_available.sh` (restartable; ~4–5 h on 2 cores).

Pilot on the 2023–2024 files only: prefix the 02–09 commands with `MAKD_CONFIG=config_pilot.yaml`. Results: `paper/pilot/summary.md`, figures in `paper/pilot/figures/` (about 40 min training + 60 min evaluation on 2 cores).

Test without real data: `bash tests/run_smoke.sh` (synthetic files in the exact record layout, scratch copy of the repo, about 30 minutes on 2 cores).

## Layout
`code/` numbered scripts and the `makd` package · `config.yaml` · `data/raw` (not committed) · `data/processed/qa_report.txt` · `paper/` stats.json, tables, figures, manuscript · `docs/` build spec, codebook, limitations, verification checklist, WONDER export guide, literature triage, next steps, publish guide.

## Sources
- NCHS Natality Public Use Files 2016–2024, https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/ (U.S. Government work; NCHS data use restrictions apply: no re-identification, no linkage).
- CDC WONDER Natality, Expanded, https://wonder.cdc.gov/natality-expanded-current.html (WONDER data use restrictions apply).
No microdata are redistributed in this repository.

## License and citation
Code: MIT (`LICENSE`). Documents: CC BY 4.0. Cite via `CITATION.cff` (DOI after release).
