{{banner}}

# Missingness-aware knowledge distillation for low birthweight and preterm birth prediction under state-specific item missingness in U.S. birth certificates

{{author_block}}

## Abstract

**Background.** Completeness of birth-certificate items used in perinatal risk prediction (month prenatal care began, pre-pregnancy BMI, WIC receipt, smoking, education, payer) differs sharply across U.S. states. [VERIFY: author rewrites in own voice]

**Methods.** We used NCHS public-use natality files for {{years_span}} and CDC WONDER state-level item-completeness counts. A teacher model was trained on records complete for all six items; students were distilled to operate under each of {{n_states}} jurisdictions' observed missingness, simulated under MCAR and covariate-dependent MAR mechanisms. We compared students with imputation and non-distilled baselines on sensitivity and positive predictive value (PPV) at a 10% alert rate, calibration, and subgroup performance in the {{test_year}} births.

**Results.** Test-year prevalence was {{outcomes.LBW.prevalence_test|pct1}} for low birthweight (LBW) and {{outcomes.PTB.prevalence_test|pct1}} for preterm birth (PTB). Under MAR missingness, the median across states of the PPV gap to the full-information teacher was {{outcomes.LBW.mechanisms.MAR.KD_state.ppv_alert.gap_median|pts}} points for the state-distilled student versus {{outcomes.LBW.mechanisms.MAR.B3_state.ppv_alert.gap_median|pts}} for the same model trained without distillation (LBW), and {{outcomes.PTB.mechanisms.MAR.KD_state.ppv_alert.gap_median|pts}} versus {{outcomes.PTB.mechanisms.MAR.B3_state.ppv_alert.gap_median|pts}} (PTB). {{abstract_natural}}

**Conclusion.** Missingness-aware distillation performed comparably to imputation when state missingness was simulated at real rates, and better than imputation on records with naturally missing items. Evaluation on naturally incomplete records changed the conclusion. [Draft conclusion: author to confirm]

## 1. Introduction

{{introduction}}

## 2. Methods

### 2.1 Data
Live births in the NCHS natality public-use files, {{years_span}}. The cohort was restricted to singleton births to U.S.-resident mothers with stated birthweight and obstetric-estimate gestational age between 20 and 44 weeks. Training years {{train_years}}; tuning year {{tune_year}}; test year {{test_year}}. Public-use files carry no state identifier, so state-specific missingness was taken from CDC WONDER Natality (Expanded): for each state and item, the proportion of births with the item unknown or not stated in {{test_year}}. Parsed record counts for U.S. residents matched the registered-birth totals in the National Vital Statistics Reports exactly, and the national unknown rate for each item in WONDER agreed with the microdata to within 0.01 percentage points.

### 2.2 Outcomes and predictors
LBW: birthweight < 2,500 g. PTB: obstetric-estimate gestation < 37 completed weeks. Predictors were restricted to information available before labor (Table S1); delivery and infant items were excluded to avoid leakage.

### 2.3 Missingness masks
For record *i*, item *j*, state *s*: P(M_ij = 1 | z_i) = expit(c_sj + β z_i), where z_i is a standardized score of always-observed covariates and c_sj is solved so that the mean probability equals the state's WONDER rate. β = 0 gives MCAR. Within-record dependence used a one-factor Gaussian copula (ρ), which preserves each item's marginal probability. {{stress_sentence}}[VERIFY: β, ρ, MAR covariates, stress arm — V4, V5, V11]

### 2.4 Teacher, students, baselines
Teacher: gradient-boosted trees (LightGBM) on records complete for all items, with {{K}}-fold cross-fitting so that soft targets for the student are out-of-fold. Student: same learner on masked inputs plus missingness indicators, trained with cross-entropy against q = α y + (1 − α) expit(logit(p_T)/τ), α = {{alpha}}, τ = {{tau}}; one student per state and one pooled over the births-weighted state mixture. Baselines: teacher with mean/mode imputation (B1); teacher with chained-equation imputation (B2); the student's learner trained on hard labels only (B3, the distillation ablation); logistic regression with missing indicators (B4).

### 2.5 Evaluation
Each model was evaluated in {{eval_n_test}} test-year births under each state's mask. Thresholds for the 10% alert rate and for 80% sensitivity were fixed in the tuning year under the same mask, then applied to the test year. Measures: AUROC, AUPRC, sensitivity and PPV at both operating points, calibration intercept and slope, ICI, Brier score. Uncertainty: stratified bootstrap ({{B}} replicates) for the lowest-, median-, and highest-missingness states and paired differences between distilled and non-distilled students. Subgroups: maternal race and Hispanic origin, age band, payer, nativity. A separate analysis used test-year records with naturally occurring missingness ({{natural_missing_n_test}} records).

## 3. Results
{{results_paragraphs}}

![Births with each item unknown or not stated, by state ({{test_year}}, CDC WONDER). Bars mark the median state.](figures/fig1_state_missingness.png)

![Gap to the full-information teacher in PPV (top) and sensitivity (bottom) at the 10% alert rate, by state, outcome and missingness mechanism.](figures/fig2_gap_to_teacher.png)

![Calibration: integrated calibration index across states, by model.](figures/fig3_calibration_ici.png)

![PPV at the 10% alert rate by subgroup under the births-weighted state mixture (MAR masks).](figures/fig4_subgroups_ppv.png)

## 4. Discussion
{{discussion}}

## Declarations
**AI assistance.** Claude (Anthropic) assisted with code scaffolding, data-wrangling scripts, document formatting, and literature triage. The author made all modeling decisions, verified every number against pipeline output, and wrote the interpretation. [VERIFY: match target journal's AI policy wording]

**Data and code availability.** NCHS natality public-use files and CDC WONDER are publicly available; no microdata are redistributed. Code: {{code_doi}}.

**Funding / conflicts.** [VERIFY]

## References

{{references}}
