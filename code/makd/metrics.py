"""Discrimination, operating-point, and calibration metrics for rare binary outcomes."""
from __future__ import annotations

import numpy as np
from scipy.special import logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from statsmodels.nonparametric.smoothers_lowess import lowess

EPS = 1e-6


def _lp(p):
    return logit(np.clip(p, EPS, 1 - EPS))


def calibration_intercept_slope(y, p):
    lp = _lp(p)
    slope = LogisticRegression(C=1e6, max_iter=200).fit(lp[:, None], y).coef_[0, 0]
    # calibration-in-the-large: intercept of logistic model with lp as fixed offset (Newton steps)
    a = 0.0
    for _ in range(25):
        m = 1 / (1 + np.exp(-(a + lp)))
        g, h = np.sum(y - m), np.sum(m * (1 - m))
        a += g / h
        if abs(g / h) < 1e-8:
            break
    return float(a), float(slope)


def ici(y, p, max_n=50000, seed=0):
    """Integrated calibration index (Austin & Steyerberg 2019): mean |lowess(y~p) - p|."""
    rng = np.random.default_rng(seed)
    if len(p) > max_n:
        idx = rng.choice(len(p), max_n, replace=False)
        y, p = y[idx], p[idx]
    # delta: interpolate within 0.1% of the prediction range (same ICI to ~1e-7, ~30x faster)
    sm = lowess(y, p, frac=2 / 3, it=0, return_sorted=False, delta=0.001 * float(np.ptp(p)))
    return float(np.mean(np.abs(sm - p)))


def threshold_for_sensitivity(y, p, target):
    """Largest threshold whose sensitivity >= target."""
    pos = np.sort(p[y == 1])[::-1]
    k = int(np.ceil(target * len(pos))) - 1
    return float(pos[max(k, 0)])


def at_threshold(y, p, thr):
    flag = p >= thr
    tp = np.sum(flag & (y == 1))
    sens = tp / max(np.sum(y == 1), 1)
    ppv = tp / max(np.sum(flag), 1)
    return float(sens), float(ppv), float(flag.mean())


ICI_MAX_N = 20000


def all_metrics(y, p, thr_alert, thr_sens):
    a, s = calibration_intercept_slope(y, p)
    sa, pa, ra = at_threshold(y, p, thr_alert)
    ss, ps, rs = at_threshold(y, p, thr_sens)
    return {
        "n": int(len(y)), "events": int(y.sum()), "prevalence": float(y.mean()),
        "auroc": float(roc_auc_score(y, p)), "auprc": float(average_precision_score(y, p)),
        "sens_alert": sa, "ppv_alert": pa, "rate_alert": ra,
        "sens_s80": ss, "ppv_s80": ps, "rate_s80": rs,
        "cal_intercept": a, "cal_slope": s, "ici": ici(y, p, max_n=ICI_MAX_N), "brier": float(brier_score_loss(y, p)),
        "mean_pred": float(p.mean()),
    }


def bootstrap(y, p, fn, B, seed):
    """Percentile CI, resampling events and non-events separately."""
    rng = np.random.default_rng(seed)
    i1, i0 = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    vals = []
    for _ in range(B):
        idx = np.concatenate([rng.choice(i1, len(i1)), rng.choice(i0, len(i0))])
        vals.append(fn(y[idx], p[idx]))
    vals = np.asarray(vals)
    return np.percentile(vals, [2.5, 97.5], axis=0)


def recalibrate(y_tune, p_tune):
    """Logistic recalibration fitted on tune-year predictions; returns a function."""
    lr = LogisticRegression(C=1e6, max_iter=200).fit(_lp(p_tune)[:, None], y_tune)
    return lambda p: lr.predict_proba(_lp(p)[:, None])[:, 1]
