# Verification checklist — Selorm completes before any release

Initial and date each line. `code/publish_gate.py` checks the mechanical items; these are yours.

## Reproduce
- [ ] Fresh fetch via `01_fetch.py`; PROVENANCE.txt has a line per file with SHA-256
- [ ] All six WONDER exports saved and logged (docs/WONDER_EXPORT_GUIDE.md)
- [ ] Full pipeline re-run from a clean `data/processed`; outputs match committed tables
- [ ] Every number in the manuscript traced to `paper/stats.json` after the re-run

## Source-level checks
- [ ] **V1** `python code/00_check_layout.py` reports every field ok for every year (2016–2024: 26/26 fields ok for all nine years, 234 checks, on 2026-10-07). Open `data/processed/layout_check.csv` and spot-check three fields by hand in a guide
- [ ] **V2** QA section 3 shows OK for every year (births match NVSR exactly; LBW/PTB within 0.15 pt of NVSR singleton rates). 2016, 2017, 2023 and 2024 passed 2026-10-07. Check three values in `docs/sources/nvsr/nvsr_reference.json` against the PDFs
- [ ] QA section 5 reconciliation: WONDER vs file unknown rates within 0.5 points for every item-year
- [ ] Five state-item rates checked by hand in WONDER (QA section 6 lists lowest/median/highest)

## Judgment calls to own (edit config.yaml or record agreement here)
- [ ] **V3** Predictor set; prenatal visit count excluded (leakage into PTB) — agree / change
- [ ] **V4** MAR covariates and weights (teen, unmarried, foreign-born, NH White, high parity) and β = 1
- [ ] **V5** Copula ρ = 0.5 for MAR (and 0 for MCAR): justification written
- [ ] **V6** α = 0.3, τ = 1; any tuning done on 2023 only, never on 2024
- [ ] **V7** Operating points: 10% alert rate, 80% sensitivity
- [ ] **V8** Subgroups and minimum 50 events per cell
- [ ] "Not Available" counted as missing; suppressed WONDER cells set to 5
- [ ] Cross-fitting K = 5 for soft targets
- [ ] **V11** Stress arm (`MARx5`, real rates × 5): keep, change the multiplier, or drop; decide how the paper frames real-rate vs stress results
- [ ] **V12** Pilot numbers (paper/pilot) are never quoted as results; only the main-design run is reported
- [ ] **V13** Natural-missingness analysis (bootstrap CIs added 2026-10-07): decide whether it becomes a primary analysis (it is the only fully real test)
- [ ] **V14** Report the available-data design (2016, 2017, 2023 → 2024) as the analysis, or wait for the main 2016–2022 design

## Row-level spot checks
- [ ] Five parsed records compared field by field with the raw fixed-width line
- [ ] Five extreme predictions (highest risk) inspected for plausibility
- [ ] Five random records (record the seed)

## Figures and text
- [ ] **V9** Every figure regenerated from current tables; each plotted value spot-checked against CSV
- [ ] Literature triage: every cited paper opened and read; all [VERIFY] reference details resolved
- [ ] Manuscript rewritten in your own voice; nothing you cannot defend remains
- [ ] AI-use disclosure matches the target journal's policy

## Before it goes public
- [ ] **V10** AUTHORS.json: ORCID iD set to 0009-0005-3991-4859 (confirm); email spelling
- [ ] `config.yaml: final: true`, figures and manuscript regenerated; `python code/publish_gate.py . --allow-draft-in code/ tests/` passes (code and tests contain the stamping logic itself, so they are scanned as warnings, not blockers)
- [ ] Evidence log row written the day of release
