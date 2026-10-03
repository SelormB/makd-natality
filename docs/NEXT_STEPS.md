# Next steps after v0.1

1. **Real-data run (October 2026).** Fetch 2016–2024, WONDER exports, QA, first real teacher. Check V1/V2 before training anything.
2. **Restricted-use extension (journal version).** Apply to NCHS for state-identified natality files; replace simulated masks with each state's observed records and compare to the semi-synthetic results. Code paths are the same; only the mask step changes.
3. **MNAR sensitivity.** Add a mechanism where missingness depends on the outcome (delta-adjusted), to bound how far conclusions move.
4. **Second learner.** MLP teacher/student to show the result is not specific to trees.
5. **Missingness-shift baseline.** Add the Zhou et al. (2023) adaptation approach or MIRRAMS as a comparator.
6. **Hyperparameter sensitivity.** Grid over α ∈ {0, 0.3, 0.7, 1} and τ ∈ {1, 2} on the tune year; α = 1 is identical to B3, which makes the ablation explicit.
7. **Decision curves.** Net benefit across alert rates for the manuscript supplement.
