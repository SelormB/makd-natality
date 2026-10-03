"""Teacher, distilled student, and baselines."""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

EPS = 1e-6


def _params(cfg: dict, objective: str) -> dict:
    p = dict(cfg["models"]["lgbm"])
    for k in ("num_boost_round", "early_stopping_rounds"):
        p.pop(k)
    p.update(objective=objective, verbose=-1, num_threads=cfg["models"]["n_threads"],
             seed=cfg["masks"]["seed"], deterministic=True, force_col_wise=True)
    return p


def fit_lgbm(X: pd.DataFrame, target: np.ndarray, Xval: pd.DataFrame, yval: np.ndarray,
             cfg: dict, objective: str = "binary") -> lgb.Booster:
    """objective='binary' for hard labels; 'cross_entropy' accepts soft labels in [0, 1]."""
    cats = [c for c in cfg["features"]["categorical"] if c in X.columns]
    dtr = lgb.Dataset(X, label=target, categorical_feature=cats, free_raw_data=False)
    dva = lgb.Dataset(Xval, label=yval, categorical_feature=cats, reference=dtr)
    m = cfg["models"]["lgbm"]
    return lgb.train(_params(cfg, objective), dtr, num_boost_round=m["num_boost_round"],
                     valid_sets=[dva],
                     callbacks=[lgb.early_stopping(m["early_stopping_rounds"], verbose=False)])


def crossfit_teacher(X: pd.DataFrame, y: np.ndarray, Xval: pd.DataFrame, yval: np.ndarray,
                     cfg: dict, rng: np.random.Generator):
    """Out-of-fold teacher predictions (honest soft targets) plus a teacher fit on all rows."""
    K = cfg["models"]["crossfit_folds"]
    oof = np.full(len(X), np.nan)
    fold = rng.integers(0, K, len(X))
    for k in range(K):
        tr, te = fold != k, fold == k
        b = fit_lgbm(X[tr], y[tr], Xval, yval, cfg)
        oof[te] = b.predict(X[te])
    full = fit_lgbm(X, y, Xval, yval, cfg)
    return full, oof


def soft_targets(y: np.ndarray, p_teacher: np.ndarray, alpha: float, tau: float) -> np.ndarray:
    pt = expit(logit(np.clip(p_teacher, EPS, 1 - EPS)) / tau)
    return alpha * y + (1 - alpha) * pt


# ------------------------------------------------------------------ imputation baselines
class MeanModeImputer:
    def __init__(self, cols: list[str], categorical: list[str]):
        self.cols, self.categorical, self.values = cols, set(categorical), {}

    def fit(self, X: pd.DataFrame):
        for c in self.cols:
            s = X[c].dropna()
            binary = set(np.unique(s)) <= {0.0, 1.0}
            self.values[c] = s.mode().iloc[0] if (c in self.categorical or binary) else s.mean()
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.fillna(self.values)


class IterImputer:
    """MICE-style chained regression imputation (single draw of the conditional mean)."""

    def __init__(self, cols: list[str], seed: int):
        self.cols = cols
        self.imp = IterativeImputer(max_iter=10, random_state=seed, sample_posterior=False)

    def fit(self, X: pd.DataFrame):
        self.imp.fit(X[self.cols])
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        g = X.copy()
        g[self.cols] = self.imp.transform(X[self.cols])
        for c in ("mracehisp", "payer", "meduc", "wic"):   # keep codes on their support
            if c in g:
                g[c] = g[c].round().clip(X[c].min(), X[c].max())
        return g


class LogisticMI:
    """Logistic regression with mean imputation + missing indicators (indicators already in X).
    Categorical features are one-hot encoded with 'missing' as its own level."""

    def __init__(self, cfg: dict):
        self.cats = list(cfg["features"]["categorical"])

    def _prep(self, X):
        Z = X.copy()
        for c in self.cats:
            Z[c] = Z[c].fillna(-1)
        return self.mi.transform(Z)

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        self.cats = [c for c in self.cats if c in X.columns]
        nums = [c for c in X.columns if c not in self.cats]
        Z = X.copy()
        for c in self.cats:
            Z[c] = Z[c].fillna(-1)
        self.mi = MeanModeImputer(nums, []).fit(Z)
        pre = ColumnTransformer([("num", StandardScaler(), nums),
                                 ("cat", OneHotEncoder(handle_unknown="ignore"), self.cats)])
        self.pipe = make_pipeline(pre, LogisticRegression(max_iter=1000, C=1.0))
        self.pipe.fit(self._prep(X), y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.pipe.predict_proba(self._prep(X))[:, 1]
