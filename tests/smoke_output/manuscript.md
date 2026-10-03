> **DRAFT — not for circulation. Numbers below are from SYNTHETIC test data and are meaningless.**

# Missingness-aware knowledge distillation for low birthweight and preterm birth prediction under state-specific item missingness in U.S. birth certificates

Selorm Buaka, University of Northern Colorado. ORCID [VERIFY: ORCID iD, format 0000-0000-0000-0000; value supplied was buak1126@bears.unco.edu, an email]. [VERIFY: supplied as othnielbuaka@gnail.com; likely othnielbuaka@gmail.com]

## Abstract

**Background.** Completeness of birth-certificate items used in perinatal risk prediction (month prenatal care began, pre-pregnancy BMI, WIC receipt, smoking, education, payer) differs sharply across U.S. states. [VERIFY: author rewrites in own voice]

**Methods.** We used NCHS public-use natality files for 2016–2024 and CDC WONDER state-level item-completeness counts. A teacher model was trained on records complete for all six items; students were distilled to operate under each of 51 jurisdictions' observed missingness, simulated under MCAR and covariate-dependent MAR mechanisms. We compared students with imputation and non-distilled baselines on sensitivity and positive predictive value (PPV) at a 10% alert rate, calibration, and subgroup performance in the 2024 births.

**Results.** Test-year prevalence was 7.8% for low birthweight (LBW) and 9.8% for preterm birth (PTB). Under MAR missingness, the median across states of the PPV gap to the full-information teacher was -0.2 points for the state-distilled student versus -0.7 for the same model trained without distillation (LBW), and -0.3 versus -0.5 (PTB). [VERIFY: author states the conclusion the numbers support, including if it is null]

## 1. Introduction

[VERIFY: author writes. Outline from docs/LITERATURE_TRIAGE.md: (1) state variation in item completeness; (2) deployment-time missingness in prediction (Hoogland 2020; Sisk 2023); (3) missingness shift (Zhou 2023); (4) generalized distillation (Lopez-Paz 2016); (5) gap and contribution; (6) extension of the Ghana neonatal work.]

## 2. Methods

### 2.1 Data
Live births in the NCHS natality public-use files, 2016–2024. The cohort was restricted to singleton births to U.S.-resident mothers with stated birthweight and obstetric-estimate gestational age between 20 and 44 weeks. Training years 2016–2022; tuning year 2023; test year 2024. Public-use files carry no state identifier, so state-specific missingness was taken from CDC WONDER Natality (Expanded): for each state and item, the proportion of births with the item unknown or not stated in 2024.

### 2.2 Outcomes and predictors
LBW: birthweight < 2,500 g. PTB: obstetric-estimate gestation < 37 completed weeks. Predictors were restricted to information available before labor (Table S1); delivery and infant items were excluded to avoid leakage.

### 2.3 Missingness masks
For record *i*, item *j*, state *s*: P(M_ij = 1 | z_i) = expit(c_sj + β z_i), where z_i is a standardized score of always-observed covariates and c_sj is solved so that the mean probability equals the state's WONDER rate. β = 0 gives MCAR. Within-record dependence used a one-factor Gaussian copula (ρ), which preserves each item's marginal probability. [VERIFY: β, ρ, MAR covariates — V4, V5]

### 2.4 Teacher, students, baselines
Teacher: gradient-boosted trees (LightGBM) on records complete for all items, with 5-fold cross-fitting so that soft targets for the student are out-of-fold. Student: same learner on masked inputs plus missingness indicators, trained with cross-entropy against q = α y + (1 − α) expit(logit(p_T)/τ), α = 0.3, τ = 1.0; one student per state and one pooled over the births-weighted state mixture. Baselines: teacher with mean/mode imputation (B1); teacher with chained-equation imputation (B2); the student's learner trained on hard labels only (B3, the distillation ablation); logistic regression with missing indicators (B4).

### 2.5 Evaluation
Each model was evaluated in 30,000 test-year births under each state's mask. Thresholds for the 10% alert rate and for 80% sensitivity were fixed in the tuning year under the same mask, then applied to the test year. Measures: AUROC, AUPRC, sensitivity and PPV at both operating points, calibration intercept and slope, ICI, Brier score. Uncertainty: stratified bootstrap (30 replicates) for the lowest-, median-, and highest-missingness states and paired differences between distilled and non-distilled students. Subgroups: maternal race and Hispanic origin, age band, payer, nativity. A separate analysis used test-year records with naturally occurring missingness (8,036 records).

## 3. Results
**LBW, MAR.** Full-information teacher: median AUROC across states 0.602, PPV at 10% alert 15.3%. State-distilled student: AUROC 0.605 (range 0.601–0.608); PPV gap -0.2 points; sensitivity gap 0.0 points; median ICI 0.66. Non-distilled state model: AUROC 0.595 (range 0.590–0.602); PPV gap -0.7 points; sensitivity gap -0.8 points; median ICI 0.46. Teacher with iterative imputation: AUROC 0.601 (range 0.597–0.603); PPV gap -0.2 points; sensitivity gap -0.2 points; median ICI 0.68. Teacher with mean imputation: AUROC 0.601 (range 0.597–0.603); PPV gap -0.2 points; sensitivity gap -0.3 points; median ICI 0.68. The distilled student had higher PPV than the non-distilled model in 50 of 51 states and lower ICI in 9.

**LBW, MCAR.** Full-information teacher: median AUROC across states 0.602, PPV at 10% alert 15.3%. State-distilled student: AUROC 0.605 (range 0.602–0.609); PPV gap -0.2 points; sensitivity gap 0.0 points; median ICI 0.65. Non-distilled state model: AUROC 0.596 (range 0.589–0.601); PPV gap -0.8 points; sensitivity gap -0.8 points; median ICI 0.44. Teacher with iterative imputation: AUROC 0.602 (range 0.596–0.604); PPV gap -0.1 points; sensitivity gap -0.2 points; median ICI 0.69. Teacher with mean imputation: AUROC 0.602 (range 0.596–0.604); PPV gap -0.1 points; sensitivity gap -0.3 points; median ICI 0.69. The distilled student had higher PPV than the non-distilled model in 49 of 51 states and lower ICI in 8.

**PTB, MAR.** Full-information teacher: median AUROC across states 0.610, PPV at 10% alert 19.1%. State-distilled student: AUROC 0.609 (range 0.603–0.611); PPV gap -0.3 points; sensitivity gap -0.1 points; median ICI 0.60. Non-distilled state model: AUROC 0.604 (range 0.597–0.607); PPV gap -0.5 points; sensitivity gap -0.4 points; median ICI 0.65. Teacher with iterative imputation: AUROC 0.608 (range 0.603–0.610); PPV gap -0.1 points; sensitivity gap 0.0 points; median ICI 0.65. Teacher with mean imputation: AUROC 0.609 (range 0.604–0.611); PPV gap -0.1 points; sensitivity gap 0.0 points; median ICI 0.64. The distilled student had higher PPV than the non-distilled model in 39 of 51 states and lower ICI in 35.

**PTB, MCAR.** Full-information teacher: median AUROC across states 0.610, PPV at 10% alert 19.1%. State-distilled student: AUROC 0.609 (range 0.604–0.611); PPV gap -0.3 points; sensitivity gap -0.1 points; median ICI 0.59. Non-distilled state model: AUROC 0.604 (range 0.597–0.607); PPV gap -0.4 points; sensitivity gap -0.4 points; median ICI 0.63. Teacher with iterative imputation: AUROC 0.608 (range 0.603–0.609); PPV gap 0.0 points; sensitivity gap +0.1 points; median ICI 0.64. Teacher with mean imputation: AUROC 0.609 (range 0.604–0.611); PPV gap 0.0 points; sensitivity gap 0.0 points; median ICI 0.63. The distilled student had higher PPV than the non-distilled model in 41 of 51 states and lower ICI in 31.

Figure 1. State item missingness (2024). Figure 2. Gap to teacher in PPV and sensitivity at the 10% alert rate. Figure 3. Calibration (ICI). Figure 4. Subgroup PPV.

## 4. Discussion
[VERIFY: author writes after reading docs/LIMITATIONS.md, which this section may not outrun.]

## Declarations
**AI assistance.** Claude (Anthropic) assisted with code scaffolding, data-wrangling scripts, document formatting, and literature triage. The author made all modeling decisions, verified every number against pipeline output, and wrote the interpretation. [VERIFY: match target journal's AI policy wording]

**Data and code availability.** NCHS natality public-use files and CDC WONDER are publicly available; no microdata are redistributed. Code: [DOI: Zenodo, after release].

**Funding / conflicts.** [VERIFY]
