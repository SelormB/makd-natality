> **DRAFT — not for circulation. Numbers below are from the PILOT run (train 80% of 2023, tune 20% of 2023, test 2024; reduced samples). Feasibility only: do not quote. The main design trains on 2016-2022.**

# Missingness-aware knowledge distillation for low birthweight and preterm birth prediction under state-specific item missingness in U.S. birth certificates

Selorm Buaka, University of Northern Colorado. ORCID 0009-0005-3991-4859. [VERIFY: supplied as othnielbuaka@gnail.com; likely othnielbuaka@gmail.com]

## Abstract

**Background.** Completeness of birth-certificate items used in perinatal risk prediction (month prenatal care began, pre-pregnancy BMI, WIC receipt, smoking, education, payer) differs sharply across U.S. states. [VERIFY: author rewrites in own voice]

**Methods.** We used NCHS public-use natality files for 2023–2024 and CDC WONDER state-level item-completeness counts. A teacher model was trained on records complete for all six items; students were distilled to operate under each of 51 jurisdictions' observed missingness, simulated under MCAR and covariate-dependent MAR mechanisms. We compared students with imputation and non-distilled baselines on sensitivity and positive predictive value (PPV) at a 10% alert rate, calibration, and subgroup performance in the 2024 births.

**Results.** Test-year prevalence was 6.9% for low birthweight (LBW) and 8.6% for preterm birth (PTB). Under MAR missingness, the median across states of the PPV gap to the full-information teacher was -0.2 points for the state-distilled student versus -0.5 for the same model trained without distillation (LBW), and -0.1 versus -0.1 (PTB). [VERIFY: author states the conclusion the numbers support, including if it is null]

## 1. Introduction

[VERIFY: author writes. Outline from docs/LITERATURE_TRIAGE.md: (1) state variation in item completeness; (2) deployment-time missingness in prediction (Hoogland 2020; Sisk 2023); (3) missingness shift (Zhou 2023); (4) generalized distillation (Lopez-Paz 2016); (5) gap and contribution; (6) extension of the Ghana neonatal work.]

## 2. Methods

### 2.1 Data
Live births in the NCHS natality public-use files, 2023–2024. The cohort was restricted to singleton births to U.S.-resident mothers with stated birthweight and obstetric-estimate gestational age between 20 and 44 weeks. Training years 2023 (80% of records); tuning year 2023 (held-out 20%); test year 2024. Public-use files carry no state identifier, so state-specific missingness was taken from CDC WONDER Natality (Expanded): for each state and item, the proportion of births with the item unknown or not stated in 2024. Parsed record counts for U.S. residents matched the registered-birth totals in the National Vital Statistics Reports exactly, and the national unknown rate for each item in WONDER agreed with the microdata to within 0.01 percentage points.

### 2.2 Outcomes and predictors
LBW: birthweight < 2,500 g. PTB: obstetric-estimate gestation < 37 completed weeks. Predictors were restricted to information available before labor (Table S1); delivery and infant items were excluded to avoid leakage.

### 2.3 Missingness masks
For record *i*, item *j*, state *s*: P(M_ij = 1 | z_i) = expit(c_sj + β z_i), where z_i is a standardized score of always-observed covariates and c_sj is solved so that the mean probability equals the state's WONDER rate. β = 0 gives MCAR. Within-record dependence used a one-factor Gaussian copula (ρ), which preserves each item's marginal probability. A stress arm (MARx5) multiplied every state's observed rates by 5, capped at 95%, to show behavior under much poorer completeness than any state reports. [VERIFY: β, ρ, MAR covariates, stress arm — V4, V5, V11]

### 2.4 Teacher, students, baselines
Teacher: gradient-boosted trees (LightGBM) on records complete for all items, with 3-fold cross-fitting so that soft targets for the student are out-of-fold. Student: same learner on masked inputs plus missingness indicators, trained with cross-entropy against q = α y + (1 − α) expit(logit(p_T)/τ), α = 0.3, τ = 1.0; one student per state and one pooled over the births-weighted state mixture. Baselines: teacher with mean/mode imputation (B1); teacher with chained-equation imputation (B2); the student's learner trained on hard labels only (B3, the distillation ablation); logistic regression with missing indicators (B4).

### 2.5 Evaluation
Each model was evaluated in 100,000 test-year births under each state's mask. Thresholds for the 10% alert rate and for 80% sensitivity were fixed in the tuning year under the same mask, then applied to the test year. Measures: AUROC, AUPRC, sensitivity and PPV at both operating points, calibration intercept and slope, ICI, Brier score. Uncertainty: stratified bootstrap (100 replicates) for the lowest-, median-, and highest-missingness states and paired differences between distilled and non-distilled students. Subgroups: maternal race and Hispanic origin, age band, payer, nativity. A separate analysis used test-year records with naturally occurring missingness (100,000 records).

## 3. Results
**LBW, MAR.** Full-information teacher: median AUROC across states 0.681, PPV at 10% alert 18.3%. State-distilled student: AUROC 0.679 (range 0.678–0.680); PPV gap -0.2 points; sensitivity gap -0.3 points; median ICI 0.21. Non-distilled state model: AUROC 0.677 (range 0.676–0.679); PPV gap -0.5 points; sensitivity gap -0.7 points; median ICI 0.14. Teacher with iterative imputation: AUROC 0.680 (range 0.678–0.681); PPV gap -0.1 points; sensitivity gap -0.2 points; median ICI 0.28. Teacher with mean imputation: AUROC 0.681 (range 0.678–0.681); PPV gap -0.1 points; sensitivity gap -0.1 points; median ICI 0.26. The distilled student had higher PPV than the non-distilled model in 8 of 8 states and lower ICI in 0.

**LBW, MARx5.** Full-information teacher: median AUROC across states 0.681, PPV at 10% alert 18.3%. State-distilled student: AUROC 0.676 (range 0.670–0.680); PPV gap -0.6 points; sensitivity gap -0.9 points; median ICI 0.18. Non-distilled state model: AUROC 0.674 (range 0.668–0.678); PPV gap -0.7 points; sensitivity gap -0.9 points; median ICI 0.13. Teacher with iterative imputation: AUROC 0.678 (range 0.668–0.680); PPV gap -0.4 points; sensitivity gap -0.5 points; median ICI 0.28. Teacher with mean imputation: AUROC 0.679 (range 0.669–0.681); PPV gap -0.3 points; sensitivity gap -0.4 points; median ICI 0.27. The distilled student had higher PPV than the non-distilled model in 7 of 8 states and lower ICI in 0.

**LBW, MCAR.** Full-information teacher: median AUROC across states 0.681, PPV at 10% alert 18.3%. State-distilled student: AUROC 0.679 (range 0.678–0.680); PPV gap -0.2 points; sensitivity gap -0.3 points; median ICI 0.21. Non-distilled state model: AUROC 0.677 (range 0.676–0.679); PPV gap -0.5 points; sensitivity gap -0.6 points; median ICI 0.14. Teacher with iterative imputation: AUROC 0.680 (range 0.678–0.680); PPV gap -0.1 points; sensitivity gap -0.2 points; median ICI 0.28. Teacher with mean imputation: AUROC 0.681 (range 0.679–0.681); PPV gap -0.1 points; sensitivity gap -0.1 points; median ICI 0.26. The distilled student had higher PPV than the non-distilled model in 8 of 8 states and lower ICI in 0.

**PTB, MAR.** Full-information teacher: median AUROC across states 0.669, PPV at 10% alert 22.8%. State-distilled student: AUROC 0.667 (range 0.666–0.668); PPV gap -0.1 points; sensitivity gap +0.1 points; median ICI 0.48. Non-distilled state model: AUROC 0.665 (range 0.663–0.666); PPV gap -0.1 points; sensitivity gap -0.2 points; median ICI 0.48. Teacher with iterative imputation: AUROC 0.667 (range 0.665–0.668); PPV gap 0.0 points; sensitivity gap 0.0 points; median ICI 0.44. Teacher with mean imputation: AUROC 0.668 (range 0.667–0.669); PPV gap -0.1 points; sensitivity gap -0.1 points; median ICI 0.44. The distilled student had higher PPV than the non-distilled model in 5 of 8 states and lower ICI in 3.

**PTB, MARx5.** Full-information teacher: median AUROC across states 0.669, PPV at 10% alert 22.8%. State-distilled student: AUROC 0.663 (range 0.655–0.667); PPV gap -0.3 points; sensitivity gap -0.3 points; median ICI 0.49. Non-distilled state model: AUROC 0.662 (range 0.653–0.666); PPV gap -0.4 points; sensitivity gap -0.4 points; median ICI 0.52. Teacher with iterative imputation: AUROC 0.665 (range 0.653–0.667); PPV gap -0.2 points; sensitivity gap -0.2 points; median ICI 0.46. Teacher with mean imputation: AUROC 0.666 (range 0.655–0.668); PPV gap -0.3 points; sensitivity gap -0.2 points; median ICI 0.45. The distilled student had higher PPV than the non-distilled model in 7 of 8 states and lower ICI in 6.

**PTB, MCAR.** Full-information teacher: median AUROC across states 0.669, PPV at 10% alert 22.8%. State-distilled student: AUROC 0.667 (range 0.666–0.668); PPV gap -0.1 points; sensitivity gap +0.1 points; median ICI 0.49. Non-distilled state model: AUROC 0.665 (range 0.663–0.666); PPV gap -0.2 points; sensitivity gap -0.3 points; median ICI 0.52. Teacher with iterative imputation: AUROC 0.667 (range 0.665–0.668); PPV gap 0.0 points; sensitivity gap 0.0 points; median ICI 0.44. Teacher with mean imputation: AUROC 0.668 (range 0.666–0.669); PPV gap -0.1 points; sensitivity gap -0.1 points; median ICI 0.44. The distilled student had higher PPV than the non-distilled model in 7 of 8 states and lower ICI in 6.

**LBW, records with naturally missing items** (n = 100,000; 9,303 events; models trained under MAR masks). The pooled distilled student had AUROC 0.686 and PPV 24.5% at the 10% alert threshold. Paired bootstrap 95% intervals: versus teacher with mean imputation, AUROC difference +0.005 to +0.009 and PPV difference -0.02 to +0.78 points; versus teacher with iterative imputation, AUROC difference +0.013 to +0.017 and PPV difference +0.75 to +1.71 points; versus the same learner without distillation, AUROC difference +0.001 to +0.003 and PPV difference +0.30 to +1.02 points.

**PTB, records with naturally missing items** (n = 100,000; 11,710 events; models trained under MAR masks). The pooled distilled student had AUROC 0.686 and PPV 31.0% at the 10% alert threshold. Paired bootstrap 95% intervals: versus teacher with mean imputation, AUROC difference +0.009 to +0.011 and PPV difference -0.27 to +0.39 points; versus teacher with iterative imputation, AUROC difference +0.016 to +0.019 and PPV difference +0.56 to +1.23 points; versus the same learner without distillation, AUROC difference +0.001 to +0.004 and PPV difference -0.41 to +0.23 points.

Figure 1. State item missingness (2024). Figure 2. Gap to teacher in PPV and sensitivity at the 10% alert rate. Figure 3. Calibration (ICI). Figure 4. Subgroup PPV.

## 4. Discussion
[VERIFY: author writes after reading docs/LIMITATIONS.md, which this section may not outrun.]

## Declarations
**AI assistance.** Claude (Anthropic) assisted with code scaffolding, data-wrangling scripts, document formatting, and literature triage. The author made all modeling decisions, verified every number against pipeline output, and wrote the interpretation. [VERIFY: match target journal's AI policy wording]

**Data and code availability.** NCHS natality public-use files and CDC WONDER are publicly available; no microdata are redistributed. Code: [DOI: Zenodo, after release].

**Funding / conflicts.** [VERIFY]
