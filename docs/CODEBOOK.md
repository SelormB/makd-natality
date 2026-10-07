# Codebook — model features and outcomes (DRAFT)

Source fields are NCHS public-use names (User Guide 2024). Positions are in `config.yaml`, checked against each year's guide by `code/00_check_layout.py`. Records are 1,345 characters plus CRLF; zips are Deflate64-compressed. Missing codes become NaN.

State-level missingness for each masked item comes from CDC WONDER (Natality, 2016–2024 expanded): Month Prenatal Care Began; Mother's Pre-pregnancy BMI; WIC; Number of Cigarettes Before Pregnancy Recode; Mother's Education; Source of Payment for Delivery. "Unknown or Not Stated" and "Not Reported" count as missing.

| Feature | Source field | Definition / transformation | Masked? |
|---|---|---|---|
| mage | MAGER | Mother's age, single years | no |
| mracehisp | MRACEHISP | Mother's race/Hispanic origin recode (categorical; 8 = unknown → NaN) | no |
| foreign_born | MBSTATE_REC | 1 if born outside the U.S. (code 2); 3 = unknown → NaN | no |
| unmarried | DMAR | 1 if unmarried (code 2); 9 → NaN | no |
| fage_reported | FAGECOMB | 1 if father's age is stated (proxy for paternal information on the record); values outside the documented 9–98 range are treated as not stated (one 2017 record has age 1) | no |
| lbo | LBO_REC | Live birth order recode; 9 → NaN | no |
| priorlive | PRIORLIVE | Prior births now living; 99 → NaN | no |
| priordead | PRIORDEAD | Prior births now dead; 99 → NaN | no |
| rf_pdiab, rf_phype, rf_ppterm, rf_inftr | RF_PDIAB, RF_PHYPE, RF_PPTERM, RF_INFTR | Pre-pregnancy diabetes, pre-pregnancy hypertension, previous preterm birth, infertility treatment: Y = 1, N = 0, U → NaN | no |
| rf_cesarn | RF_CESARN | Number of previous cesareans; 99 → NaN | no |
| birth_year | DOB_YY | Year of birth | no |
| precare_month | PRECARE | Month prenatal care began, 0 = none, 1–10; 99 → NaN | **yes** |
| bmi | BMI | Pre-pregnancy BMI, 13.0–69.9; 99.9 → NaN | **yes** |
| wic | WIC | WIC during pregnancy: Y = 1, N = 0, U → NaN | **yes** |
| cig_pre | CIG_0 | Cigarettes per day, 3 months before pregnancy; 99 → NaN | **yes** |
| meduc | MEDUC | Mother's education, 1–8; 9 → NaN | **yes** |
| payer | PAY_REC | Payment source recode (1 Medicaid, 2 private, 3 self-pay, 4 other); 9 → NaN | **yes** |
| miss_<feature> | derived | 1 if the masked feature is missing (students and B3/B4 only) | — |
| prenatal_visits | PREVIS | Excluded by default (`features.include_prenatal_visits`), see V3 | — |

| Outcome | Definition |
|---|---|
| LBW | DBWT < 2,500 g |
| PTB | OEGest_Comb < 37 completed weeks (obstetric estimate) |

Cohort: DPLURAL = 1; RESTATUS 1–3; DBWT and OEGest_Comb stated; OEGest_Comb 20–44.

Tables (`paper/tables/`): `metrics_by_state.csv` (one row per outcome × mechanism × state × model × calibration variant), `bootstrap_selected_states.csv`, `subgroups.csv`, `natural_missingness.csv`. Column meanings: auroc, auprc; sens/ppv/rate at the 10% alert threshold (`_alert`) and at the threshold giving 80% sensitivity in the tune year (`_s80`); cal_intercept (calibration-in-the-large), cal_slope; ici (integrated calibration index); brier; thr_* thresholds fixed on the tune year.
