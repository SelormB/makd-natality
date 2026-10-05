# Verification checklist — Selorm completes before any release

Initial and date each line. `code/publish_gate.py` checks the mechanical items; these are yours.

## Reproduce
- [ ] Fresh fetch via `01_fetch.py`; PROVENANCE.txt has a line per file with SHA-256
- [ ] All six WONDER exports saved and logged (docs/WONDER_EXPORT_GUIDE.md)
- [ ] Full pipeline re-run from a clean `data/processed`; outputs match committed tables
- [ ] Every number in the manuscript traced to `paper/stats.json` after the re-run

## Source-level checks
- [ ] **V1** Every layout position in `config.yaml` checked against the User Guide for 2016, 2020, and 2024 (layouts can shift); OEGest_Comb position resolved
- [ ] **V2** `NVSR_REFERENCE` in `code/04_qa.py` filled from "Births: Final Data" for each year; parsed totals within 0.1%; LBW and PTB rates (all births) match NVSR
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
