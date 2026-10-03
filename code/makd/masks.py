"""State-calibrated missingness masks.

For record i and item j in state s:
    P(M_ij = 1 | z_i) = sigmoid(c_sj + beta * z_i)
where z_i is a standardized score of always-observed covariates (MAR; beta = 0 gives MCAR)
and c_sj is solved so that the mean of P over the masked sample equals the state's WONDER
unknown rate r_sj. Within-record dependence between items uses a one-factor Gaussian copula
with correlation rho, which leaves every item's marginal P(M_ij=1 | z_i) unchanged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm


def mar_score(f: pd.DataFrame, weights: dict) -> np.ndarray:
    parts = {
        "teen": (f["mage"] < 20).astype(float),
        "unmarried": f["unmarried"].fillna(0),
        "foreign_born": f["foreign_born"].fillna(0),
        "nh_white": (f["mracehisp"] == 1).astype(float),
        "high_parity": (f["lbo"] >= 4).astype(float),
    }
    z = sum(w * parts[k].to_numpy() for k, w in weights.items())
    sd = z.std()
    return (z - z.mean()) / sd if sd > 0 else np.zeros(len(f))


def solve_intercept(z: np.ndarray, beta: float, r: float, tol: float = 1e-7) -> float:
    if r <= 0:
        return -np.inf
    if r >= 1:
        return np.inf
    if beta == 0:
        return float(np.log(r / (1 - r)))
    lo, hi = -30.0, 30.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if expit(mid + beta * z).mean() < r:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def draw_mask(f: pd.DataFrame, rates: dict, items: dict, beta: float, rho: float,
              weights: dict, rng: np.random.Generator) -> pd.DataFrame:
    """Return a boolean DataFrame (columns = masked feature names), True = set to missing.

    rates: {item_key: unknown rate in [0, 1]} for one state.
    items: cfg['masked_items'].
    """
    n = len(f)
    z = mar_score(f, weights) if beta != 0 else np.zeros(n)
    common = rng.standard_normal(n)
    out = {}
    for key, spec in items.items():
        r = float(rates.get(key, 0.0) or 0.0)
        c = solve_intercept(z, beta, r)
        p = expit(c + beta * z) if np.isfinite(c) else np.full(n, float(c > 0))
        u = np.sqrt(rho) * common + np.sqrt(1 - rho) * rng.standard_normal(n)
        out[spec["feature"]] = norm.cdf(u) < p
    return pd.DataFrame(out, index=f.index)


def apply_mask(f: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    g = f.copy()
    for col in mask.columns:
        g.loc[mask[col].to_numpy(), col] = np.nan
    return g


def add_indicators(f: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    g = f.copy()
    for c in cols:
        g[f"miss_{c}"] = g[c].isna().astype("float32")
    return g
