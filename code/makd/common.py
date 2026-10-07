"""Shared utilities: config, fixed-width parsing, cohort and feature construction."""
from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | os.PathLike | None = None) -> dict:
    path = Path(path or os.environ.get("MAKD_CONFIG") or ROOT / "config.yaml")
    if not path.is_absolute():
        path = ROOT / path
    with open(path) as f:
        cfg = yaml.safe_load(f)
    for k, v in cfg["paths"].items():
        p = Path(v)
        cfg["paths"][k] = p if p.is_absolute() else ROOT / p
    if os.environ.get("MAKD_SMOKE"):          # tiny settings for the synthetic test run
        m, e = cfg["models"], cfg["evaluation"]
        m.update(teacher_train_n=60000, student_train_n=40000, iterative_imputer_n=20000)
        m["lgbm"].update(num_boost_round=300, min_data_in_leaf=100)
        e.update(eval_n=30000, bootstrap_B=30, ici_max_n=4000)
    return cfg


def layout_for_year(cfg: dict, year: int) -> dict:
    lay = dict(cfg["layout"])
    lay.update(cfg.get("layout_overrides", {}).get(year, {}) or {})
    return lay


# ---------------------------------------------------------------- fixed-width parsing
def _iter_record_chunks(fh, reclen: int, chunk_records: int):
    """Yield uint8 arrays of shape (n, reclen). Handles \\n and \\r\\n line endings."""
    buf = []
    for line in fh:
        line = line.rstrip(b"\r\n")
        if not line:
            continue
        if len(line) < reclen:                 # pad short records (trailing blanks trimmed)
            line = line.ljust(reclen)
        buf.append(line[:reclen])
        if len(buf) == chunk_records:
            yield np.frombuffer(b"".join(buf), dtype=np.uint8).reshape(-1, reclen)
            buf = []
    if buf:
        yield np.frombuffer(b"".join(buf), dtype=np.uint8).reshape(-1, reclen)


def _decode(block: np.ndarray, spec: dict) -> pd.Series:
    a, b = spec["start"] - 1, spec["end"]
    w = b - a
    raw = np.ascontiguousarray(block[:, a:b]).view(f"S{w}").ravel()
    s = pd.Series(raw).str.decode("ascii", errors="replace").str.strip()
    t = spec["type"]
    if t == "yn":
        return s.map({"Y": 1.0, "N": 0.0}).astype("float32")   # U / X / blank -> NaN
    v = pd.to_numeric(s, errors="coerce")
    for na in spec.get("na", []):
        v = v.mask(np.isclose(v, na))
    return v.astype("float32")


def read_natality(path: str | os.PathLike, cfg: dict, year: int,
                  chunk_records: int = 500_000) -> pd.DataFrame:
    """Parse one NCHS natality public-use file (.zip or .txt) into the configured fields."""
    lay = layout_for_year(cfg, year)
    reclen = cfg["source"]["record_length"]
    path = Path(path)
    frames = []

    def _consume(fh):
        for block in _iter_record_chunks(fh, reclen, chunk_records):
            frames.append(pd.DataFrame({k: _decode(block, v) for k, v in lay.items()}))

    if path.suffix.lower() == ".zip":
        # NCHS zips use Deflate64 (method 9), which the standard zipfile module cannot read.
        # Stream through Info-ZIP `unzip -p` when available; else use zipfile-deflate64.
        import shutil
        import subprocess
        if shutil.which("unzip"):
            proc = subprocess.Popen(["unzip", "-p", str(path)], stdout=subprocess.PIPE, bufsize=1 << 24)
            try:
                _consume(proc.stdout)
            finally:
                proc.stdout.close()
                if proc.wait() != 0:
                    raise RuntimeError(f"unzip failed on {path}")
        else:
            try:
                import zipfile_deflate64 as zf
            except ImportError:
                zf = zipfile
            with zf.ZipFile(path) as z:
                name = max(z.namelist(), key=lambda n: z.getinfo(n).file_size)
                with z.open(name) as fh:
                    _consume(io.BufferedReader(fh, buffer_size=1 << 24))
    else:
        with open(path, "rb") as fh:
            _consume(fh)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------- cohort, outcomes, features
def build_cohort(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Apply cohort rules; return the cohort and a dict of row counts at each step."""
    c = cfg["cohort"]
    steps = {"parsed": len(df)}
    if c["singleton_only"]:
        df = df[df["DPLURAL"] == 1]
        steps["singleton"] = len(df)
    df = df[df["RESTATUS"].isin(c["restatus_keep"])]
    steps["us_resident"] = len(df)
    df = df[df["DBWT"].notna() & df["OEGest_Comb"].notna()]
    steps["outcome_known"] = len(df)
    df = df[df["OEGest_Comb"].between(c["gest_min"], c["gest_max"])]
    steps["gest_in_range"] = len(df)
    return df.reset_index(drop=True), steps


def add_outcomes(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    for name, o in cfg["outcomes"].items():
        assert o["rule"] == "lt"
        df[name] = (df[o["field"]] < o["value"]).astype("int8")
    return df


def make_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Model features. Masked items keep NaN where the item is missing in the source."""
    f = pd.DataFrame(index=df.index)
    f["mage"] = df["MAGER"]
    f["mracehisp"] = df["MRACEHISP"]
    f["foreign_born"] = (df["MBSTATE_REC"] == 2).astype("float32").where(df["MBSTATE_REC"].notna())
    f["unmarried"] = (df["DMAR"] == 2).astype("float32").where(df["DMAR"].notna())
    f["fage_reported"] = df["FAGECOMB"].notna().astype("float32")
    f["lbo"] = df["LBO_REC"]
    f["priorlive"] = df["PRIORLIVE"]
    f["priordead"] = df["PRIORDEAD"]
    for k in ["RF_PDIAB", "RF_PHYPE", "RF_PPTERM", "RF_INFTR"]:
        f[k.lower()] = df[k]
    f["rf_cesarn"] = df["RF_CESARN"]
    f["birth_year"] = df["DOB_YY"]
    # masked items
    f["precare_month"] = df["PRECARE"]
    f["bmi"] = df["BMI"]
    f["wic"] = df["WIC"]
    f["cig_pre"] = df["CIG_0"]
    f["meduc"] = df["MEDUC"]
    f["payer"] = df["PAY_REC"]
    if cfg["features"]["include_prenatal_visits"]:
        f["prenatal_visits"] = df["PREVIS"]
    return f.astype("float32")


def feature_names(cfg: dict) -> list[str]:
    names = list(cfg["features"]["always_observed"])
    names += [v["feature"] for v in cfg["masked_items"].values()]
    if cfg["features"]["include_prenatal_visits"]:
        names.append("prenatal_visits")
    return names


def masked_features(cfg: dict) -> list[str]:
    return [v["feature"] for v in cfg["masked_items"].values()]


def write_json(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
