# Literature triage — DRAFT (2026-10-03)

Purpose: a starting map, not a review. Every entry must be opened and read by the author before it is cited; entries tagged [VERIFY] have details (authors, volume, year) not yet confirmed against the source. Nothing here has been summarized from the full text; one-line notes describe why each item matters to MAKD-Natality.

## 1. Distillation and privileged information (the method's lineage)

| Ref | Why it matters |
|---|---|
| Hinton, Vinyals, Dean (2015). Distilling the knowledge in a neural network. arXiv:1503.02531 | Origin of soft-target distillation and temperature. |
| Vapnik, Vashist (2009). A new learning paradigm: learning using privileged information. *Neural Networks* 22(5–6) [VERIFY pages] | Training-time-only features: here, the items a state leaves blank. |
| Lopez-Paz, Bottou, Schölkopf, Vapnik (2016). Unifying distillation and privileged information. ICLR. https://leon.bottou.org/publications/pdf/iclr-2016.pdf | "Generalized distillation": teacher sees privileged features, student does not. MAKD is this setting with jurisdiction-specific privileged sets. Closest methodological ancestor. |

## 2. Missing predictors at deployment (the statistical problem)

| Ref | Why it matters |
|---|---|
| Hoogland et al. (2020). Handling missing predictor values when validating and applying a prediction model to new patients. *Stat Med*. https://doi.org/10.1002/sim.8682 | Core comparator literature for SiM; frames deployment-time missingness. Likely reviewer reference. |
| Li et al. (2021). Evaluation of predictive model performance of an existing model in the presence of missing data. *Stat Med*. https://doi.org/10.1002/sim.8978 | Validation under missingness; informs how the evaluation is framed. |
| Sperrin et al. (2020). Missing data should be handled differently for prediction than for description or causal explanation. *J Clin Epidemiol*. https://research.manchester.ac.uk/en/publications/missing-data-should-be-handled-differently-for-prediction-than-fo/ | Justifies missing indicators and "imputation at deployment must be available at deployment." |
| Sisk, Sperrin, Peek, van Smeden, Martin (2023). Imputation and missing indicators for handling missing data in the development and deployment of clinical prediction models: a simulation study. *Stat Methods Med Res*. https://journals.sagepub.com/doi/full/10.1177/09622802231165001 | Closest simulation design to ours; the B1–B4 baselines should be recognizable to these authors. |
| van Smeden et al. (2020/21). A cautionary note on the use of the missing indicator method for handling missing data in prediction research. *J Clin Epidemiol*. https://www.jclinepi.com/article/S0895-4356(20)30702-2/abstract | Counterpoint on indicators; cite in limitations of B4 and of indicators in the student. |
| Tsvetanova et al. (2021). Missing data was handled inconsistently in UK prediction models. *J Clin Epidemiol*. https://www.sciencedirect.com/science/article/abs/pii/S0895435621002882 | Motivation: practice is inconsistent. |
| Nijman et al. (2022). Missing data is poorly handled and reported in prediction model studies using machine learning. *J Clin Epidemiol*. https://www.sciencedirect.com/science/article/pii/S0895435621003759 | Motivation for the ML side. |
| [VERIFY authors] (2025). Addressing missingness in predictive models that use electronic health record data. *Ann Intern Med*. https://doi.org/10.7326/ANNALS-24-01516 | Recent clinical-audience framing; check overlap. |
| Josse, Chen, Prost, Scornet, Varoquaux. On the consistency of supervised learning with missing values. [VERIFY venue/year: arXiv 2019; journal version] | Theory: imputation quality vs prediction quality; supports native-NaN trees + indicators. |
| Le Morvan, Josse, Scornet, Varoquaux (2021). What's a good imputation to predict with missing values? NeurIPS. [VERIFY] | Same thread; relevant to why teacher+imputation can underperform. |

## 3. Missingness that differs between training and deployment sites

| Ref | Why it matters |
|---|---|
| Zhou, Balakrishnan, Lipton (2023). Domain adaptation under missingness shift. AISTATS, PMLR 206. https://proceedings.mlr.press/v206/zhou23b.html (code: https://github.com/acmi-lab/Missingness-Shift) | The formal name for our problem: same population, different missingness by site. Must be cited and contrasted (they adapt; we distill). |
| Stokes et al. (2025). Domain adaptation under MNAR missingness. arXiv:2504.00322 | MNAR extension; relevant to our MCAR/MAR-only limitation. |
| MIRRAMS (2025). Learning robust tabular models under unseen missingness shifts. arXiv:2507.08280 [VERIFY authors] | Robust-to-unseen-pattern alternative; a possible extra baseline for the journal version. |

## 4. Validation measures for rare outcomes

| Ref | Why it matters |
|---|---|
| Van Calster et al. (2019). Calibration: the Achilles heel of predictive analytics. *BMC Med* 17:230 [VERIFY] | Calibration hierarchy; justifies intercept, slope, and curve. |
| Austin, Steyerberg (2019). The Integrated Calibration Index (ICI) and related metrics. *Stat Med* [VERIFY] | Definition of ICI used in `metrics.py`. |
| Collins et al. (2024). TRIPOD+AI statement. *BMJ* [VERIFY] | Reporting checklist for the manuscript (both target journals expect it). |

## 5. Birth certificate data: domain and data quality

| Ref | Why it matters |
|---|---|
| Martin et al. (2013). Assessing the quality of medical and health data from the 2003 birth certificate revision: results from two states. *NVSR* 62 [VERIFY issue number] | Item validity, not only completeness: completeness ≠ accuracy; belongs in limitations. |
| Births: Final Data for 2016–2024. *NVSR* (e.g., https://www.cdc.gov/nchs/data/nvsr/nvsr67/nvsr67_01.pdf for 2016) | Reference totals for QA check V2. |
| User Guide to the 2024 Natality Public Use File. https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2024.pdf | Record layout (V1) and item definitions. |
| [VERIFY authors] (2022). Identifying the early signs of preterm birth from U.S. birth records using machine learning techniques. *Information* 13(7):310. https://www.mdpi.com/2078-2489/13/7/310 | Prior ML on U.S. birth records; check its predictor window for leakage before citing as a comparator. |
| Your Ghana neonatal manuscript (submitted) [VERIFY: citation as "under review" per journal policy] | Positions this as the U.S. national extension. |

## Positioning (for the author to accept, revise, or reject)

1. The missing-data-in-prediction literature (Section 2) compares imputation and indicator strategies but trains each model on the data it will see; it does not use a full-information model to supervise a reduced-information one.
2. The missingness-shift literature (Section 3) adapts a model across sites; it does not exploit the fact that, in vital records, many jurisdictions report items completely and can supply a teacher.
3. A candidate statistical argument [author to verify before use]: with temperature 1, if the teacher is calibrated for P(y | full x), and missingness is independent of the outcome given the full x (true by construction for the simulated masks, not guaranteed for real MNAR missingness), then E[p_T(x) | x_observed, M] = P(y | x_observed, M). The soft target is therefore unbiased for what the student should learn and has lower variance than the 0/1 label (a Rao–Blackwell-type argument). This would predict gains concentrated in high-missingness states and in rare-outcome PPV, which is what the study measures. Temperature ≠ 1 breaks the unbiasedness, which is why tau = 1 is the default and why recalibrated results are reported separately.

## Searches still to run (author)
PubMed/Embase for "knowledge distillation" AND (missing OR incomplete) AND (clinical OR epidemiolog*); "privileged information" AND health; birth certificate completeness by state (Northam & Knapp; Dietz et al. PRAMS validation) [VERIFY].
