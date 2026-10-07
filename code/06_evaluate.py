#!/usr/bin/env python3
"""Evaluate every model under every state's missingness pattern in the test year.

Thresholds (top-alert-rate and 80%-sensitivity) and the optional logistic recalibration are
fixed on the tune year under the same state pattern, then applied to the test year.

Writes paper/tables/: metrics_by_state.csv, bootstrap_selected_states.csv,
subgroups.csv, natural_missingness.csv; and paper/stats.json (headline numbers for the text).
"""
import sys
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import feature_names, load_config, masked_features, write_json  # noqa: E402
from makd.data import (full_design, load_years, masked_design, pooled_masked_design,  # noqa: E402
                       state_patterns, state_rng)
from makd.masks import add_indicators  # noqa: E402
from makd.metrics import (all_metrics, at_threshold, bootstrap, recalibrate,  # noqa: E402
                          threshold_for_sensitivity)

from joblib import Parallel, delayed  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

MODELS = ["T_oracle", "B1_teacher_meanimp", "B2_teacher_iterimp", "B3_pooled", "B3_state",
          "B4_logistic_pooled", "KD_pooled", "KD_state"]


class Bank:
    def __init__(self, cfg, outcome, mech):
        md = cfg["paths"]["models"]
        self.md, self.tag, self.cfg = md, f"{outcome}_{mech}", cfg
        self.T = lgb.Booster(model_file=str(md / f"T_{outcome}.txt"))
        self.B1 = joblib.load(md / "B1_meanmode.joblib")
        self.B2 = joblib.load(md / f"B2_iter_{mech}.joblib")
        self.B3p = lgb.Booster(model_file=str(md / f"B3_{self.tag}_pooled.txt"))
        self.KDp = lgb.Booster(model_file=str(md / f"KD_{self.tag}_pooled.txt"))
        self.B4 = joblib.load(md / f"B4_{self.tag}_pooled.joblib")
        self.feats = feature_names(cfg)

    def state_model(self, kind, state):
        p = self.md / f"{kind}_{self.tag}_{state.replace(' ', '_')}.txt"
        return lgb.Booster(model_file=str(p)) if p.exists() else None

    @staticmethod
    def _p(b, X):
        return b.predict(X[b.feature_name()])

    def predict(self, X, state=None):
        f = self.feats
        out = {"B1_teacher_meanimp": self._p(self.T, self.B1.transform(X[f])),
               "B2_teacher_iterimp": self._p(self.T, self.B2.transform(X[f])),
               "B3_pooled": self._p(self.B3p, X), "KD_pooled": self._p(self.KDp, X),
               "B4_logistic_pooled": self.B4.predict(X)}
        if state is not None:
            for kind in ("B3", "KD"):
                b = self.state_model(kind, state)
                if b is not None:
                    out[f"{kind}_state"] = self._p(b, X)
        return out


def evaluate_set(y_tu, P_tu, y_te, P_te, ev, recal):
    """Fix thresholds (and recalibration) on tune, compute metrics on test."""
    rows = {}
    for m, pte in P_te.items():
        ptu = P_tu[m]
        variants = [("raw", ptu, pte)]
        if recal:
            f = recalibrate(y_tu, ptu)
            variants.append(("recal", f(ptu), f(pte)))
        for v, a, b in variants:
            thr_a = float(np.quantile(a, 1 - ev["alert_rate"]))
            thr_s = threshold_for_sensitivity(y_tu, a, ev["teacher_sensitivity_target"])
            rows[(m, v)] = (all_metrics(y_te, b, thr_a, thr_s), thr_a, thr_s, b)
    return rows


_BANKS = {}


def _bank(cfg, outcome, mech_name):
    key = (outcome, mech_name)
    if key not in _BANKS:
        _BANKS[key] = Bank(cfg, outcome, mech_name)
    return _BANKS[key]


def eval_state(cfg, outcome, mech, s, pat, test, tune, pT_te, pT_tu, mean_unknown, do_boot):
    """All models under one state's pattern. Returns (metric rows, bootstrap rows)."""
    import makd.metrics as _m
    ev = cfg["evaluation"]
    _m.ICI_MAX_N = ev["ici_max_n"]
    bank = _bank(cfg, outcome, mech["name"])
    y_te, y_tu = test[outcome].to_numpy(), tune[outcome].to_numpy()
    Xte = masked_design(test, cfg, pat, mech, state_rng(cfg, s, 3))
    Xtu = masked_design(tune, cfg, pat, mech, state_rng(cfg, s, 2))
    P_te = {"T_oracle": pT_te, **bank.predict(Xte, s)}
    P_tu = {"T_oracle": pT_tu, **bank.predict(Xtu, s)}
    res = evaluate_set(y_tu, P_tu, y_te, P_te, ev, ev["recalibrate_on_tune"])
    rows, boots = [], []
    for (m, v), (met, ta, ts, p) in res.items():
        rows.append({"outcome": outcome, "mechanism": mech["name"], "state": s,
                     "state_mean_unknown": mean_unknown, "model": m, "calibration": v,
                     "thr_alert": ta, "thr_s80": ts, **met})
    if not do_boot:
        return rows, boots
    for m in P_te:
        _, ta, _, p = res[(m, "raw")]

        def fn(yy, pp, ta=ta):
            se, pv, _ = at_threshold(yy, pp, ta)
            return [roc_auc_score(yy, pp), se, pv]
        lo, hi = bootstrap(y_te, p, fn, ev["bootstrap_B"], seed=11)
        boots.append({"outcome": outcome, "mechanism": mech["name"], "state": s, "model": m,
                      "auroc_lo": lo[0], "auroc_hi": hi[0], "sens_alert_lo": lo[1],
                      "sens_alert_hi": hi[1], "ppv_alert_lo": lo[2], "ppv_alert_hi": hi[2]})
    if "KD_state" in P_te and "B3_state" in P_te:     # paired difference KD_state - B3_state
        ta_k, ta_b = res[("KD_state", "raw")][1], res[("B3_state", "raw")][1]
        rng = np.random.default_rng(12)
        i1, i0 = np.flatnonzero(y_te == 1), np.flatnonzero(y_te == 0)
        d = []
        for _ in range(ev["bootstrap_B"]):
            ii = np.concatenate([rng.choice(i1, len(i1)), rng.choice(i0, len(i0))])
            yy, k, b = y_te[ii], P_te["KD_state"][ii], P_te["B3_state"][ii]
            d.append([roc_auc_score(yy, k) - roc_auc_score(yy, b),
                      at_threshold(yy, k, ta_k)[1] - at_threshold(yy, b, ta_b)[1]])
        lo, hi = np.percentile(np.asarray(d), [2.5, 97.5], axis=0)
        boots.append({"outcome": outcome, "mechanism": mech["name"], "state": s,
                      "model": "DIFF_KDstate_minus_B3state", "auroc_lo": lo[0], "auroc_hi": hi[0],
                      "ppv_alert_lo": lo[1], "ppv_alert_hi": hi[1]})
    return rows, boots


def main():
    cfg = load_config()
    ev = cfg["evaluation"]
    import makd.metrics as _m
    _m.ICI_MAX_N = ev["ici_max_n"]
    rng = np.random.default_rng(cfg["masks"]["seed"] + 7)
    patterns, weights = state_patterns(cfg)
    mf = masked_features(cfg)
    tabs = cfg["paths"]["paper"] / "tables"
    tabs.mkdir(parents=True, exist_ok=True)
    cache = tabs / "_cache"          # per (outcome, mechanism) checkpoints; delete to recompute
    cache.mkdir(exist_ok=True)

    test = load_years(cfg, cfg["years"]["test"], ev["eval_n"], rng, complete_only=True)
    tune = load_years(cfg, cfg["years"]["tune"], ev["eval_n"], rng, complete_only=True, part="tune")
    test_all = load_years(cfg, cfg["years"]["test"], None, rng)
    natural = test_all[test_all[mf].isna().any(axis=1)]
    natural = natural.sample(min(len(natural), ev["eval_n"]), random_state=1).reset_index(drop=True)
    tune_all = load_years(cfg, cfg["years"]["tune"], None, rng, part="tune")
    nat_tune = tune_all[tune_all[mf].isna().any(axis=1)]
    nat_tune = nat_tune.sample(min(len(nat_tune), ev["eval_n"]), random_state=2).reset_index(drop=True)
    del test_all, tune_all

    # states for bootstrap: highest / median / lowest mean unknown rate across items
    mean_rate = pd.Series({s: np.mean(list(p.values())) for s, p in patterns.items()}).sort_values()
    pick = {"lowest": mean_rate.index[0], "median": mean_rate.index[len(mean_rate) // 2],
            "highest": mean_rate.index[-1]}
    boot_states = {pick[k] for k in ev["bootstrap_states"] if k in pick}

    rows, boots, subs, nat_rows = [], [], [], []
    stats = {"n_states": len(patterns), "eval_n_test": len(test), "eval_n_tune": len(tune),
             "natural_missing_n_test": len(natural), "states_picked": pick,
             "mean_unknown_rate_by_state": mean_rate.round(5).to_dict(), "outcomes": {}}

    for outcome in cfg["outcomes"]:
        y_te, y_tu = test[outcome].to_numpy(), tune[outcome].to_numpy()
        stats["outcomes"][outcome] = {"prevalence_test": float(y_te.mean()), "mechanisms": {}}
        T = lgb.Booster(model_file=str(cfg["paths"]["models"] / f"T_{outcome}.txt"))
        pT_te, pT_tu = T.predict(full_design(test, cfg)), T.predict(full_design(tune, cfg))

        for mech in cfg["masks"]["mechanisms"]:
            ck = cache / f"{outcome}_{mech['name']}.pkl"
            if ck.exists():
                r_, b_, s_ = pd.read_pickle(ck)
                rows += r_; boots += b_; subs += s_
                print(f"[eval] {outcome} {mech['name']}: cached", flush=True)
                continue
            t0 = time.time()
            r_blk, b_blk, s_blk = [], [], []
            bank = Bank(cfg, outcome, mech["name"])
            jobs = Parallel(n_jobs=ev["n_jobs"], verbose=0)(
                delayed(eval_state)(cfg, outcome, mech, st, pat, test, tune, pT_te, pT_tu,
                                    float(mean_rate[st]), st in boot_states)
                for st, pat in patterns.items())
            for r_, b_ in jobs:
                r_blk += r_
                b_blk += b_

            # national deployment (births-weighted state mixture) for subgroup analysis
            mrng = np.random.default_rng([cfg["masks"]["seed"], 4])
            Xte, _ = pooled_masked_design(test, cfg, patterns, weights, mech, mrng)
            Xtu, _ = pooled_masked_design(tune, cfg, patterns, weights, mech, mrng)
            P_te = {"T_oracle": pT_te, **bank.predict(Xte)}
            P_tu = {"T_oracle": pT_tu, **bank.predict(Xtu)}
            res = evaluate_set(y_tu, P_tu, y_te, P_te, ev, False)
            groups = {
                "mracehisp": test["mracehisp"],
                "mage_band": pd.cut(test["mage"], [0, 19, 34, 99], labels=["<20", "20-34", "35+"]),
                "payer_obs": test["payer"], "foreign_born": test["foreign_born"]}
            for gname in ev["subgroups"]:
                gv = groups[gname]
                for level in pd.Series(gv).dropna().unique():
                    msk = (pd.Series(gv) == level).to_numpy()
                    if y_te[msk].sum() < ev["min_subgroup_events"] or y_te[msk].sum() == msk.sum():
                        continue
                    for (m, _), (_, ta, ts, p) in res.items():
                        met = all_metrics(y_te[msk], p[msk], ta, ts)
                        s_blk.append({"outcome": outcome, "mechanism": mech["name"], "subgroup": gname,
                                     "level": str(level), "model": m, **met})


            pd.to_pickle((r_blk, b_blk, s_blk), ck)
            rows += r_blk; boots += b_blk; subs += s_blk
            print(f"[eval] {outcome} {mech['name']}: {len(patterns)} states in {time.time() - t0:.0f} s", flush=True)

        # natural missingness: real incomplete records, pooled models trained under each mechanism
        ckn = cache / f"{outcome}_natural.pkl"
        if ckn.exists():
            nat_rows += pd.read_pickle(ckn)
            continue
        n_before = len(nat_rows)
        Xn, Xnt = add_indicators(natural[feature_names(cfg)], mf), add_indicators(nat_tune[feature_names(cfg)], mf)
        y_n, y_nt = natural[outcome].to_numpy(), nat_tune[outcome].to_numpy()
        for mech in cfg["masks"]["mechanisms"]:
            bank = Bank(cfg, outcome, mech["name"])
            res = evaluate_set(y_nt, bank.predict(Xnt), y_n, bank.predict(Xn), ev, False)
            for (m, v), (met, ta, ts, _) in res.items():
                nat_rows.append({"outcome": outcome, "trained_under": mech["name"], "model": m,
                                 "calibration": v, **met})
        pd.to_pickle(nat_rows[n_before:], ckn)

    M = pd.DataFrame(rows)
    M.to_csv(tabs / "metrics_by_state.csv", index=False)
    pd.DataFrame(boots).to_csv(tabs / "bootstrap_selected_states.csv", index=False)
    pd.DataFrame(subs).to_csv(tabs / "subgroups.csv", index=False)
    pd.DataFrame(nat_rows).to_csv(tabs / "natural_missingness.csv", index=False)

    # headline numbers: gap to the oracle teacher, summarized across states
    raw = M[M["calibration"] == "raw"]
    keys = ["auroc", "auprc", "sens_alert", "ppv_alert", "sens_s80", "ppv_s80", "cal_slope",
            "cal_intercept", "ici", "brier"]
    for (o, mech), g in raw.groupby(["outcome", "mechanism"]):
        base = g[g["model"] == "T_oracle"].set_index("state")[keys]
        summ = {}
        for m, gm in g.groupby("model"):
            x = gm.set_index("state")[keys]
            gap = x - base
            summ[m] = {k: {"median": float(x[k].median()), "min": float(x[k].min()),
                           "max": float(x[k].max()), "gap_median": float(gap[k].median())}
                       for k in keys}
        if {"KD_state", "B3_state"} <= set(g["model"]):
            kd = g[g["model"] == "KD_state"].set_index("state")
            b3 = g[g["model"] == "B3_state"].set_index("state")
            summ["_kd_vs_b3_state"] = {
                "states_kd_higher_ppv_alert": int((kd["ppv_alert"] > b3["ppv_alert"]).sum()),
                "states_kd_higher_auroc": int((kd["auroc"] > b3["auroc"]).sum()),
                "states_kd_lower_ici": int((kd["ici"] < b3["ici"]).sum()),
                "n_states": int(len(kd))}
        stats["outcomes"][o]["mechanisms"][mech] = summ
    stats["synthetic"] = bool(__import__("os").environ.get("MAKD_SMOKE"))
    stats["pilot"] = bool(set(cfg["years"]["train"]) & set(cfg["years"]["tune"]))
    stats["years"] = cfg["years"]
    stats["mechanisms"] = cfg["masks"]["mechanisms"]
    write_json(stats, cfg["paths"]["paper"] / "stats.json")
    print(f"[eval] {len(M)} metric rows; stats -> paper/stats.json")


if __name__ == "__main__":
    main()
