"""Loading cohorts, state patterns, and masked design matrices."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import feature_names, masked_features
from .masks import add_indicators, apply_mask, draw_mask


def load_years(cfg: dict, years: list[int], n: int | None, rng: np.random.Generator,
               complete_only: bool = False) -> pd.DataFrame:
    """Concatenate cohort years; optionally keep records complete on masked items; sample n."""
    mf = masked_features(cfg)
    frames = []
    for y in years:
        d = pd.read_parquet(cfg["paths"]["processed"] / f"cohort_{y}.parquet")
        if complete_only:
            d = d[d[mf].notna().all(axis=1)]
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    if n is not None and len(df) > n:
        df = df.iloc[rng.choice(len(df), n, replace=False)].reset_index(drop=True)
    return df


def state_patterns(cfg: dict) -> tuple[dict, pd.Series]:
    """{state: {item: rate}} for the deployment (test) year, and births weights by state."""
    r = pd.read_csv(cfg["paths"]["processed"] / "state_rates.csv")
    target = cfg["years"]["test"][0]
    year = target if target in set(r["year"]) else int(r["year"].max())
    r = r[r["year"] == year]
    pats = {s: dict(zip(g["item"], g["rate"].fillna(0.0))) for s, g in r.groupby("state")}
    births = r.groupby("state")["births_total"].max()
    return pats, births / births.sum()


def masked_design(f: pd.DataFrame, cfg: dict, pattern: dict, mech: dict,
                  rng: np.random.Generator) -> pd.DataFrame:
    """Apply one state's mask (one mechanism) and add missingness indicators."""
    m = draw_mask(f, pattern, cfg["masked_items"], mech["beta"], mech["rho"],
                  cfg["masks"]["mar_weights"], rng)
    X = apply_mask(f[feature_names(cfg)], m)
    return add_indicators(X, masked_features(cfg))


def pooled_masked_design(f: pd.DataFrame, cfg: dict, patterns: dict, weights: pd.Series,
                         mech: dict, rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """Assign each record a state by births weight, mask with that state's pattern."""
    states = rng.choice(weights.index.to_numpy(), size=len(f), p=weights.to_numpy())
    parts = []
    for s in np.unique(states):
        idx = np.flatnonzero(states == s)
        parts.append(masked_design(f.iloc[idx], cfg, patterns[s], mech, rng))
    X = pd.concat(parts).loc[f.index]
    return X, states


def state_rng(cfg: dict, state: str, stream: int) -> np.random.Generator:
    """Reproducible per-state generator (stream 1 = training masks, 2 = tune, 3 = test)."""
    import zlib
    return np.random.default_rng([cfg["masks"]["seed"], zlib.crc32(state.encode()), stream])


def full_design(f: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    return f[feature_names(cfg)]
