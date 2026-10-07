# MAKD-Natality build spec (v0.1, 2026-10-03) — DRAFT

```
PROJECT:        MAKD-Natality — missingness-aware knowledge distillation for low birthweight
                and preterm birth prediction.
                Archetypes: validation study + analysis paper (methods preprint), with a
                replication package (code only; NCHS data are re-fetched, not redistributed).

QUESTION:       When a birth-risk model is deployed in a state whose birth certificates leave
                key items blank (prenatal care onset, pre-pregnancy BMI, WIC, smoking, visits,
                education, payer), does a student model distilled from a full-information
                teacher keep sensitivity, PPV, and calibration closer to the teacher than
                imputation or naive retraining does?

SOURCES:        1. NCHS Natality Public Use Files, 2016–2024 (all U.S. births; 2003 revised
                   certificate in all jurisdictions from 2016). Fixed-width, 1,330-byte records.
                   https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/
                   Layout: User Guide 2024 (UserGuide2024.pdf, same directory tree, Dataset_Documentation).
                   Public domain (U.S. Government work); NCHS data use restrictions apply
                   (no re-identification, no linkage). National level only: no state identifier.
                2. CDC WONDER Natality, Expanded (2016–2024): state-of-residence × year counts
                   of "Unknown or Not Stated" for each masked item, exported by hand
                   (the WONDER API does not serve sub-national natality queries).
                   https://wonder.cdc.gov/natality-expanded-current.html
                   Terms: WONDER data use restrictions; cells < 10 suppressed.

DESIGN:         Semi-synthetic (author decision 1a, 2026-10-03). Real national records;
                state-year missingness masks calibrated to WONDER item-unknown rates and
                imposed on complete records. Masks under MCAR and covariate-dependent MAR,
                with an optional within-record correlation between items.
                Plus one fully real check: performance on records with naturally occurring
                missingness in the national test year.

UNIT:           Live birth. Cohort: singleton, U.S. resident mothers (RESTATUS 1–3),
                known outcome (DBWT, OEGest_Comb stated), gestation 20–44 wk.

OUTCOMES:       LBW = DBWT < 2,500 g.  PTB = OEGest_Comb < 37 completed weeks.
                Modeled separately.

PREDICTORS:     Antenatal-only (available before labor): maternal age, race/Hispanic origin,
                nativity, marital status, education, father's age reported (Y/N), live-birth
                order, prior live births, prior other pregnancy outcomes, pre-pregnancy BMI,
                height, pre-pregnancy diabetes, pre-pregnancy hypertension, previous preterm
                birth, infertility treatment, previous cesarean (count), cigarettes before
                pregnancy, month prenatal care began, WIC, payer, birth year.
                Excluded (leakage): prenatal visit COUNT is end-of-pregnancy and correlates with
                gestation length  -> [VERIFY: author rules include/exclude], gestational
                diabetes/hypertension, eclampsia, labor/delivery, infant fields, plurality.

MASKED ITEMS:   PRECARE, BMI (with M_Ht_In, PWgt_R), WIC, CIG_0, MEDUC, PAY
                (+ PREVIS if included).

MODELS:         Teacher  T: LightGBM, trained on train-years records complete on all masked items.
                Student  S: LightGBM, cross-entropy objective on soft targets
                            q = alpha*y + (1-alpha)*sigmoid(logit(p_T)/tau),
                            inputs = masked features + missingness indicators,
                            masks drawn from the deployment state's pattern
                            (per-state S) and from the pooled state mixture (one S for all).
                Baselines: B1 T + mean/mode imputation; B2 T + iterative (MICE-style)
                           imputation; B3 LightGBM on masked data, hard labels only
                           (the distillation ablation); B4 logistic regression + missing
                           indicators.

SPLIT:          Train 2016–2022; tune 2023; test 2024 (temporal).

MEASURES:       Per state × outcome × model: AUROC; AUPRC; sensitivity and PPV at a fixed
                alert rate (top 10% risk flagged) and at the threshold giving the teacher
                80% sensitivity; calibration intercept and slope; ICI; Brier.
                Subgroups: race/Hispanic origin, maternal age band, payer, nativity.
                Uncertainty: bootstrap over test births (B = 200), stratified by outcome.
                Headline contrast: gap to teacher (S − T) vs (B − T), summarized across states.

OUTPUTS:        code/01..07 scripts; data/processed/qa_report.txt;
                paper/stats.json; paper/tables/*.csv; paper/figures/*.png;
                paper/manuscript.md -> .docx (built from stats.json);
                docs/CODEBOOK, LIMITATIONS, VERIFY_CHECKLIST, NEXT_STEPS,
                WONDER_EXPORT_GUIDE, LITERATURE_TRIAGE, PUBLISH_GUIDE.

VENUES:         1. GitHub repo + Zenodo DOI (code release).
                2. arXiv stat.ME (cross-list stat.AP), target February 2027.
                3. Statistics in Medicine or American Journal of Epidemiology, March 2027.

VERIFY POINTS:  (Selorm rules on each; listed in docs/VERIFY_CHECKLIST.md)
                V1 record-layout positions against the 2024 User Guide (every field)
                V2 national totals reproduce NVSR "Births: Final Data" (counts, LBW %, PTB %)
                V3 predictor set; prenatal visit count in/out
                V4 MAR mechanism: which observed covariates drive missingness, and strength
                V5 within-record item correlation (rho) values to report
                V6 alpha, tau, and student hyperparameters; tuning on 2023 only
                V7 alert rate (10%) and sensitivity target (80%) as the reported operating points
                V8 subgroup definitions and minimum cell size for reporting
                V9 every figure and table number against pipeline output
                V10 author block: ORCID iD (current value is an email), email spelling

LICENSE:        Code MIT. Documents CC BY 4.0. No NCHS microdata redistributed.

ASSUMPTIONS:    Predictors and outcomes per the defaults above (author left Q2/Q3 blank).
                arXiv stat.ME first. Pipeline runs on the author's machine or HPC; this
                sandbox cannot reach ftp.cdc.gov or WONDER, so v0.1 is tested on
                synthetic files in the exact record layout.
```

## Status update, 2026-10-07: what the real data established

**Data in hand.** NCHS public-use files for 2023 and 2024 (2016–2022 downloading); CDC WONDER state × year × item exports for all six masked items, 2016–2024; NVSR *Births: Final Data* 2016–2024; User Guide 2024 (2016–2023 downloading). All in `data/` and `docs/sources/`.

**Verified.**
- Record layout (V1): every configured field position matches the 2024 User Guide (`code/00_check_layout.py`); other years run automatically when their guides arrive. Records are 1,345 characters plus CRLF, not 1,330.
- Totals (V2): U.S.-resident records equal NVSR registered births exactly (2023: 3,596,017; 2024: 3,628,934). Cohort LBW and PTB rates are within 0.05 points of NVSR singleton-only rates.
- WONDER exports reconcile with the microdata: national unknown rates agree within 0.01 points for all six items in both years.
- Smoking item: WONDER's "Number of Cigarettes Before Pregnancy Recode" is used (matches CIG_0). "Tobacco Use" covers the whole pregnancy and was not used.

**Changes forced by the real files.** NCHS zips use Deflate64 compression (parser now streams through `unzip`); server filenames vary in case by year (now listed in config); WONDER exports may omit total rows (denominator bug fixed).

**Design consequence (for the author to rule on).** Real state-level item missingness is low: across 2016–2024 the worst state-year for any item is about 14% (Tennessee, prenatal care, 2016), the median state is near 1%, and only 8 states exceed a 3% mean in any year. At real rates the room for any method to beat imputation is small. The pilot therefore adds a stress arm (`MARx5`: every state's real rates × 5, capped at 95%). Whether to keep it, and how to frame it, is decision V11.

**Pilot.** `config_pilot.yaml` runs the full pipeline on real data now: train on 80% of 2023, tune on the other 20%, test on 2024; reduced sample sizes; per-state students for the 6 highest-missingness states plus the median and lowest state. Outputs in `data/processed_pilot/` and `paper/pilot/`. The main design (train 2016–2022) is unchanged and runs with `config.yaml` once all years are present.

**Pilot ran end to end, 2026-10-07** (36 min training, 61 min evaluation, 2 cores). Generated summary: `paper/pilot/summary.md`; figures `paper/pilot/figures/`; draft text `paper/pilot/manuscript.md`. Patterns to confirm or refute in the main run (no numbers quoted here; see the summary):
1. At real state rates, every method stays within about half a percentage point of the teacher's PPV; teacher + imputation is as good as or better than the students on simulated masks.
2. Distillation beats the same learner without distillation (paired bootstrap: small, consistent AUROC gain; PPV difference not distinguishable from zero).
3. On real records with naturally missing items, the students (trained on masked data with missing indicators) rank above teacher + imputation. Simulated MCAR/MAR masks may understate informative missingness; this is the strongest argument for the method and needs CIs and the main-design data.
4. Logistic regression with missing indicators trails the tree models throughout.
