#!/usr/bin/env python3
"""Train the teacher, distilled students, and baselines for each outcome and mask mechanism.

Teacher: LightGBM on train-year records complete on all masked items (cross-fitted, so the
soft targets used for distillation are out-of-fold). Students and baselines are trained on the
same student sample, masked with state-calibrated patterns.

Saves to data/processed/models/: boosters (.txt), imputers and logistic models (.joblib),
and train_log.json (sizes, best iterations, prevalence).
"""
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import feature_names, load_config, masked_features, write_json  # noqa: E402
from makd.data import (full_design, load_years, masked_design, pooled_masked_design,  # noqa: E402
                       state_patterns, state_rng, student_states)
from makd.models import (IterImputer, LogisticMI, MeanModeImputer, crossfit_teacher,  # noqa: E402
                         fit_lgbm, soft_targets)


def main():
    cfg = load_config()
    rng = np.random.default_rng(cfg["masks"]["seed"])
    M = cfg["models"]
    md = cfg["paths"]["models"]
    md.mkdir(parents=True, exist_ok=True)
    feats, mf = feature_names(cfg), masked_features(cfg)
    patterns, weights = state_patterns(cfg)
    log = {"n_states": len(patterns), "student_states": student_states(cfg, patterns)}

    train = load_years(cfg, cfg["years"]["train"], M["teacher_train_n"], rng, complete_only=True,
                       part="train")
    tune_c = load_years(cfg, cfg["years"]["tune"], 500_000, rng, complete_only=True, part="tune")
    tune_all = load_years(cfg, cfg["years"]["tune"], 500_000, rng, part="tune")
    log["teacher_train_n"], log["tune_complete_n"] = len(train), len(tune_c)
    stu_idx = rng.choice(len(train), min(M["student_train_n"], len(train)), replace=False)

    # Imputation baseline B1 is fitted on complete training data (what a deployer would have).
    joblib.dump(MeanModeImputer(mf, cfg["features"]["categorical"]).fit(train[feats]),
                md / "B1_meanmode.joblib")

    for outcome in cfg["outcomes"]:
        y, yv = train[outcome].to_numpy(), tune_c[outcome].to_numpy()
        print(f"[teacher] {outcome}: n={len(train):,}, prevalence={y.mean():.4f}")
        teacher, oof = crossfit_teacher(full_design(train, cfg), y, full_design(tune_c, cfg), yv,
                                        cfg, rng)
        teacher.save_model(md / f"T_{outcome}.txt")
        log[f"T_{outcome}"] = {"best_iter": teacher.best_iteration, "prevalence": float(y.mean())}

        S = train.iloc[stu_idx].reset_index(drop=True)
        yS = y[stu_idx]
        q = soft_targets(yS, oof[stu_idx], M["kd"]["alpha"], M["kd"]["tau"])
        log[f"soft_{outcome}"] = {"mean_q": float(q.mean()), "mean_y": float(yS.mean())}

        for mech in cfg["masks"]["mechanisms"]:
            tag = f"{outcome}_{mech['name']}"
            XS, _ = pooled_masked_design(S, cfg, patterns, weights, mech, rng)
            XV, _ = pooled_masked_design(tune_all, cfg, patterns, weights, mech, rng)
            yV = tune_all[outcome].to_numpy()

            print(f"[pooled] {tag}")
            fit_lgbm(XS, yS, XV, yV, cfg, "binary").save_model(md / f"B3_{tag}_pooled.txt")
            fit_lgbm(XS, q, XV, yV, cfg, "cross_entropy").save_model(md / f"KD_{tag}_pooled.txt")
            joblib.dump(LogisticMI(cfg).fit(XS, yS), md / f"B4_{tag}_pooled.joblib")
            if outcome == list(cfg["outcomes"])[0]:   # imputer is outcome-free; fit once per mech
                n_imp = min(M["iterative_imputer_n"], len(XS))
                joblib.dump(IterImputer(feats, cfg["masks"]["seed"]).fit(XS.iloc[:n_imp][feats]),
                            md / f"B2_iter_{mech['name']}.joblib")

            if M["per_state_students"]:
                for s in student_states(cfg, patterns):
                    pat = patterns[s]
                    srng = state_rng(cfg, s, stream=1)
                    XSs = masked_design(S, cfg, pat, mech, srng)
                    XVs = masked_design(tune_all, cfg, pat, mech, srng)
                    safe = s.replace(" ", "_")
                    fit_lgbm(XSs, yS, XVs, yV, cfg, "binary").save_model(md / f"B3_{tag}_{safe}.txt")
                    fit_lgbm(XSs, q, XVs, yV, cfg, "cross_entropy").save_model(
                        md / f"KD_{tag}_{safe}.txt")
                print(f"[state ] {tag}: {len(student_states(cfg, patterns))} state students done")
    write_json(log, md / "train_log.json")


if __name__ == "__main__":
    main()
