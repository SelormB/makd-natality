#!/usr/bin/env python3
"""Generate SYNTHETIC natality files in the exact NCHS fixed-width layout, plus matching
CDC WONDER exports, so the full pipeline can be tested without the real data.

Nothing produced here is real. Output goes to data/raw/ and data/wonder/ ONLY when run with
--into-project (used by tests/run_smoke.sh on a scratch copy of the repository).

Usage: python tests/make_synthetic.py --root <repo copy> [--n-per-year 60000]
"""
import argparse
import sys
import zipfile
from pathlib import Path

import numpy as np
import yaml

STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
          "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
          "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
          "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
          "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
          "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
          "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
          "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]
ITEM_FIELD = {"precare": "PRECARE", "bmi": "BMI", "wic": "WIC", "cig": "CIG_0", "meduc": "MEDUC",
              "pay": "PAY_REC"}
ITEM_LABEL = {"precare": "Month Prenatal Care Began", "bmi": "Mother's Pre-pregnancy BMI",
              "wic": "WIC", "cig": "Tobacco Use", "meduc": "Mother's Education",
              "pay": "Source of Payment for Delivery"}


def gen_year(year, n, rng, state_rates):
    st = rng.integers(0, len(STATES), n)
    r = {}
    r["DOB_YY"] = np.full(n, year)
    r["MAGER"] = np.clip(np.round(rng.normal(29, 6, n)), 13, 50).astype(int)
    r["MBSTATE_REC"] = rng.choice([1, 2, 3], n, p=[0.76, 0.235, 0.005])
    r["RESTATUS"] = rng.choice([1, 2, 3, 4], n, p=[0.75, 0.22, 0.027, 0.003])
    r["MRACEHISP"] = rng.choice(range(1, 9), n, p=[0.50, 0.14, 0.008, 0.06, 0.003, 0.03, 0.24, 0.019])
    teen = r["MAGER"] < 20
    r["DMAR"] = np.where(rng.random(n) < 0.40 + 0.4 * teen, 2, 1)
    r["MEDUC"] = rng.choice(range(1, 9), n, p=[0.03, 0.08, 0.25, 0.20, 0.09, 0.22, 0.10, 0.03])
    r["FAGECOMB"] = np.where(rng.random(n) < 0.1 + 0.2 * (r["DMAR"] == 2), 99,
                             np.clip(r["MAGER"] + rng.integers(-2, 8, n), 15, 70))
    r["PRIORLIVE"] = rng.poisson(1.0, n)
    r["PRIORDEAD"] = (rng.random(n) < 0.01).astype(int)
    r["LBO_REC"] = np.clip(r["PRIORLIVE"] + 1, 1, 8)
    payer = rng.choice([1, 2, 3, 4], n, p=[0.41, 0.50, 0.04, 0.05])
    r["PAY_REC"] = payer
    late = rng.random(n) < 0.15 + 0.1 * (payer == 1)
    r["PRECARE"] = np.where(late, rng.integers(4, 10, n), rng.integers(1, 4, n))
    r["PRECARE"][rng.random(n) < 0.015] = 0
    r["PREVIS"] = np.clip(rng.poisson(11, n), 0, 98)
    r["WIC"] = np.where(rng.random(n) < 0.15 + 0.35 * (payer == 1), "Y", "N")
    smoke = rng.random(n) < 0.06 + 0.06 * (payer == 1)
    r["CIG_0"] = np.where(smoke, rng.integers(1, 30, n), 0)
    r["M_Ht_In"] = np.clip(np.round(rng.normal(64, 3, n)), 50, 78).astype(int)
    bmi = np.clip(rng.lognormal(np.log(26), 0.22, n), 14, 69.9)
    r["BMI"] = np.round(bmi, 1)
    rf = {k: rng.random(n) < p for k, p in
          {"RF_PDIAB": 0.01, "RF_PHYPE": 0.025, "RF_PPTERM": 0.03, "RF_INFTR": 0.02}.items()}
    for k, v in rf.items():
        r[k] = np.where(v, "Y", "N")
    r["RF_CESARN"] = np.where(rng.random(n) < 0.15, rng.integers(1, 4, n), 0)
    r["DPLURAL"] = rng.choice([1, 2], n, p=[0.968, 0.032])
    # outcomes
    lp = (-2.7 + 1.3 * rf["RF_PPTERM"] + 0.5 * smoke + 0.4 * (bmi > 35) + 0.25 * teen
          + 0.45 * (r["MRACEHISP"] == 2) + 0.6 * rf["RF_PHYPE"] + 0.5 * rf["RF_PDIAB"]
          + 0.35 * (r["PRECARE"] >= 7) + 0.4 * (r["PRECARE"] == 0) + 0.15 * (payer == 1)
          + 0.3 * rf["RF_INFTR"] + 0.02 * (r["MAGER"] - 29) ** 2 / 10 + 1.6 * (r["DPLURAL"] == 2))
    ptb = rng.random(n) < 1 / (1 + np.exp(-lp))
    gest = np.where(ptb, rng.integers(24, 37, n), rng.integers(37, 42, n))
    lbw_lp = -3.6 + 3.2 * ptb + 0.6 * smoke + 0.5 * (bmi < 18.5) + 0.45 * (r["MRACEHISP"] == 2) \
        + 0.25 * (r["WIC"] == "Y") + 0.3 * (r["MEDUC"] <= 2)
    lbw = rng.random(n) < 1 / (1 + np.exp(-lbw_lp))
    r["DBWT"] = np.where(lbw, rng.integers(500, 2500, n), rng.integers(2500, 4600, n))
    r["OEGest_Comb"] = gest
    r["DBWT"][rng.random(n) < 0.001] = 9999
    # natural item missingness from each record's (hidden) state rate
    item_missing = {}
    for item, field in ITEM_FIELD.items():
        p = np.array([state_rates[STATES[s]][item] for s in st])
        item_missing[item] = rng.random(n) < p
    return r, st, item_missing


def encode(r, i, lay, item_missing, reclen=1345):
    rec = bytearray(b" " * reclen)
    missing_fields = {ITEM_FIELD[k] for k, v in item_missing.items() if v[i]}
    for name, spec in lay.items():
        a, b = spec["start"] - 1, spec["end"]
        w = b - a
        if name not in r:
            continue
        v = r[name][i]
        if name in missing_fields:
            if spec["type"] == "yn":
                s = "U"
            elif spec["type"] == "float":
                s = "99.9"
            else:
                s = str(spec["na"][0]).zfill(w)
        elif spec["type"] == "yn":
            s = str(v)
        elif spec["type"] == "float":
            s = f"{v:4.1f}"
        else:
            s = str(int(v)).zfill(w)
        rec[a:b] = s.rjust(w)[:w].encode()
    return bytes(rec)


def wonder_export(item, year_data, path):
    lab = ITEM_LABEL[item]
    head = ['"Notes"', '"State of Residence"', '"State of Residence Code"', '"Year"', '"Year Code"',
            f'"{lab}"', f'"{lab} Code"', '"Births"']
    lines = ["\t".join(head)]
    for year, (r, st, miss) in sorted(year_data.items()):
        res = r["RESTATUS"] != 4
        for si, s in enumerate(STATES):
            m = (st == si) & res
            unk = int((miss[item] & m).sum())
            tot = int(m.sum())
            na_label = item == "cig" and s == "California" and year <= 2017
            rows = [("Known", tot - unk), ("Not Available" if na_label else "Unknown or Not Stated", unk)]
            for lbl, cnt in rows:
                cell = str(cnt) if cnt >= 10 or cnt == 0 else "Suppressed"
                lines.append("\t".join(["", f'"{s}"', f'"{si + 1:02d}"', f'"{year}"', f'"{year}"',
                                        f'"{lbl}"', f'"{lbl[:2]}"', cell]))
            lines.append("\t".join(['"Total"', f'"{s}"', f'"{si + 1:02d}"', f'"{year}"', f'"{year}"',
                                    "", "", str(tot)]))
    lines += ['"---"', '"Dataset: Natality, 2016-2024 expanded (SYNTHETIC TEST FILE)"', '"---"']
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--n-per-year", type=int, default=60000)
    a = ap.parse_args()
    root = Path(a.root)
    cfg = yaml.safe_load((root / "config.yaml").read_text())
    rng = np.random.default_rng(42)
    base = {"precare": 0.02, "bmi": 0.03, "wic": 0.01, "cig": 0.005, "meduc": 0.015, "pay": 0.004}
    state_rates = {s: {k: float(min(0.6, v * rng.lognormal(0, 1.0))) for k, v in base.items()}
                   for s in STATES}
    state_rates["Hawaii"]["bmi"] = 0.35        # a few states with heavy missingness
    state_rates["Arizona"]["wic"] = 0.20
    state_rates["Wyoming"]["precare"] = 0.25
    years = cfg["years"]["train"] + cfg["years"]["tune"] + cfg["years"]["test"]
    (root / "data/raw").mkdir(parents=True, exist_ok=True)
    (root / "data/wonder").mkdir(parents=True, exist_ok=True)
    year_data = {}
    for y in years:
        r, st, miss = gen_year(y, a.n_per_year, rng, state_rates)
        year_data[y] = (r, st, miss)
        body = b"\n".join(encode(r, i, cfg["layout"], miss, cfg["source"]["record_length"]) for i in range(a.n_per_year)) + b"\n"
        with zipfile.ZipFile(root / f"data/raw/Nat{y}us.zip", "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"Nat{y}PublicUS.SYNTHETIC.txt", body)
        print(f"[synthetic] {y}: {a.n_per_year:,} records")
    for item, spec in cfg["masked_items"].items():
        wonder_export(item, year_data, root / "data/wonder" / spec["wonder_file"])
    print("[synthetic] WONDER exports written")


if __name__ == "__main__":
    sys.exit(main())
