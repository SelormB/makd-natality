# Limitations (DRAFT; the Discussion may not claim more than this file allows)

1. **Semi-synthetic missingness.** State missingness is simulated from WONDER marginal rates; real records from a high-missingness state are never observed with a state label. Results show how methods behave under each state's *rates*, not under its true joint, outcome-related missingness.
2. **MCAR and MAR only.** If items are left blank more often for births that end badly (MNAR, e.g. late or no prenatal care recorded as unknown), simulated masks understate the problem. The natural-missingness analysis is the only real-data check, and it is national, not state-specific.
3. **Within-record dependence is assumed.** The copula correlation ρ is a modeling choice, not estimated from data; state reports blank whole sections together more than independently, so ρ = 0 likely understates and the chosen ρ must be justified (V5).
4. **Teacher population is selected.** The teacher learns from records complete on all items; these differ from incomplete records. The student inherits that selection.
5. **WONDER suppression.** Cells of 1–9 births are suppressed and set to 5; small states' rates for rare-unknown items are imprecise (count reported in the QA report).
6. **"Not Available" items.** Where a state did not collect an item, it is treated as missing for all its births; for those states the student never sees the item, which is the intended scenario but limits comparison.
7. **Completeness is not accuracy.** Birth-certificate items can be complete and wrong (e.g. self-reported BMI, WIC, smoking); see the 2003-revision quality literature.
8. **Antenatal predictors on a delivery record.** All predictors are recorded at or after delivery, even those describing earlier events; a prospective tool would see some of them differently.
9. **Temporal validation only.** Training 2016–2022, testing 2024, including the COVID-19 period in training; no external (non-U.S.) validation.
10. **Single learner family.** Teacher and student are gradient-boosted trees; results may not transfer to other learners.
11. **Fairness measures are descriptive.** Subgroup metrics are reported, not corrected; small subgroups are suppressed below the event minimum (V8).
12. **Synthetic test data.** Any number produced by `tests/run_smoke.sh` is meaningless and stamped as such.
