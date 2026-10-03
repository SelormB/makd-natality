#!/usr/bin/env python3
"""Parse each year's fixed-width file, apply cohort rules, build outcomes and features.

Writes data/processed/cohort_{year}.parquet (features + LBW, PTB) and
data/processed/parse_log.json (row counts per step, raw item-missing rates).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import (add_outcomes, build_cohort, load_config, make_features,  # noqa: E402
                         write_json)


def find_raw(raw: Path, year: int) -> Path:
    for pat in (f"Nat{year}us.zip", f"Nat{year}*.zip", f"Nat{year}*.txt", f"*{year}*.txt"):
        hits = sorted(raw.glob(pat))
        if hits:
            return hits[0]
    raise FileNotFoundError(f"no natality file for {year} in {raw}")


def main():
    cfg = load_config()
    from makd.common import read_natality
    out = cfg["paths"]["processed"]
    out.mkdir(parents=True, exist_ok=True)
    years = cfg["years"]["train"] + cfg["years"]["tune"] + cfg["years"]["test"]
    log = {}
    for y in years:
        src = find_raw(cfg["paths"]["raw"], y)
        print(f"[parse] {y}: {src.name}")
        df = read_natality(src, cfg, y)
        yr_vals = df["DOB_YY"].value_counts().to_dict()
        raw_missing = {c: float(df[c].isna().mean()) for c in df.columns}
        ranges = {c: [float(df[c].min()), float(df[c].max())] for c in df.columns}
        coh, steps = build_cohort(df, cfg)
        coh = add_outcomes(coh, cfg)
        feats = make_features(coh, cfg)
        for o in cfg["outcomes"]:
            feats[o] = coh[o].to_numpy()
        feats.to_parquet(out / f"cohort_{y}.parquet", index=False)
        log[y] = {"file": src.name, "dob_yy_values": {str(k): int(v) for k, v in yr_vals.items()},
                  "steps": steps, "raw_missing": raw_missing, "raw_ranges": ranges,
                  "outcome_rates": {o: float(coh[o].mean()) for o in cfg["outcomes"]},
                  "feature_missing": {c: float(feats[c].isna().mean()) for c in feats.columns}}
    write_json(log, out / "parse_log.json")


if __name__ == "__main__":
    main()
