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
