#!/usr/bin/env python3
"""QA report: layout sanity, cohort flow, outcome rates, WONDER coverage and reconciliation.

Writes data/processed/qa_report.txt. Read it before trusting anything downstream.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import load_config  # noqa: E402

# Plausible ranges (from the User Guide value codes). A field outside its range almost always
# means a wrong layout position.
EXPECTED = {"MAGER": (12, 50), "DBWT": (227, 8165), "OEGest_Comb": (17, 47), "BMI": (13, 70),
            "PRECARE": (0, 10), "MEDUC": (1, 8), "PAY_REC": (1, 4), "MRACEHISP": (1, 8),
            "DPLURAL": (1, 5), "RESTATUS": (1, 4), "CIG_0": (0, 98), "M_Ht_In": (30, 78),
            "LBO_REC": (1, 9), "FAGECOMB": (9, 98), "PRIORLIVE": (0, 30), "RF_CESARN": (0, 30)}

# VERIFY (V2): fill from NVSR "Births: Final Data for <year>" (all births; LBW %, PTB % are
# all births, not singletons). The QA compares parsed totals with these.
NVSR_REFERENCE = {y: {"births": None, "lbw_pct_all": None, "ptb_pct_all": None}
                  for y in range(2016, 2025)}

# WONDER item -> national-file raw field, for reconciliation of unknown rates.
RECON = {"precare": "PRECARE", "bmi": "BMI", "wic": "WIC", "cig": "CIG_0", "meduc": "MEDUC",
         "pay": "PAY_REC"}


def main():
    cfg = load_config()
    proc = cfg["paths"]["processed"]
    log = json.loads((proc / "parse_log.json").read_text())
    L = []
    w = L.append
    w("MAKD-Natality QA report" + ("" if cfg["final"] else "  [DRAFT]"))
    w("=" * 72)
    fails = 0

    w("\n1. Layout sanity: parsed values inside documented ranges")
    for y, d in log.items():
        bad = []
        for f, (lo, hi) in EXPECTED.items():
            mn, mx = d["raw_ranges"].get(f, [np.nan, np.nan])
            if not (np.isnan(mn) or (mn >= lo and mx <= hi)):
                bad.append(f"{f} [{mn:g}, {mx:g}] vs [{lo}, {hi}]")
        yrs = list(d["dob_yy_values"])
        if yrs != [str(y)] and yrs != [f"{float(y)}"]:
            bad.append(f"DOB_YY values {yrs}")
        fails += bool(bad)
        w(f"  {y}: {'PASS' if not bad else 'FAIL  ' + '; '.join(bad)}")

    w("\n2. Cohort flow (rows remaining after each step)")
    steps = list(next(iter(log.values()))["steps"])
    w("  year  " + "  ".join(f"{s:>14}" for s in steps))
    for y, d in log.items():
        w(f"  {y}  " + "  ".join(f"{d['steps'][s]:>14,}" for s in steps))

    w("\n3. Outcome rates in cohort (singletons) and parsed totals vs NVSR reference")
    for y, d in log.items():
        ref = NVSR_REFERENCE.get(int(y), {})
        tot = d["steps"]["parsed"]
        refb = ref.get("births")
        cmp = (f"  parsed {tot:,} vs NVSR {refb:,} ({100 * (tot - refb) / refb:+.2f}%)" if refb
               else "  NVSR reference not filled [VERIFY: V2]")
        w(f"  {y}: LBW {100 * d['outcome_rates']['LBW']:.2f}%  PTB {100 * d['outcome_rates']['PTB']:.2f}%{cmp}")

    w("\n4. Item missingness in the national file (raw fields, all records)")
    items = ["PRECARE", "BMI", "WIC", "CIG_0", "MEDUC", "PAY_REC", "PREVIS", "FAGECOMB"]
    w("  year  " + "  ".join(f"{i:>8}" for i in items))
    for y, d in log.items():
        w(f"  {y}  " + "  ".join(f"{100 * d['raw_missing'][i]:7.2f}%" for i in items))

    w("\n5. WONDER state-level unknown rates")
    rp = proc / "state_rates.csv"
    if not rp.exists():
        w("  state_rates.csv missing: run 03_wonder.py")
    else:
        r = pd.read_csv(rp)
        for item, g in r.groupby("item"):
            n_states = g.groupby("year")["state"].nunique()
            w(f"  {item}: states/year {n_states.min()}-{n_states.max()}; "
              f"rate median {100 * g['rate'].median():.2f}%, max {100 * g['rate'].max():.2f}%; "
              f"'Not Available' births {int(g['births_not_available'].sum()):,}; "
              f"suppressed unknown cells {int(g['suppressed_unknown_cells'].sum())} (set to {cfg['wonder']['suppressed_value']})")
        w("\n  Reconciliation: births-weighted WONDER rate vs national-file raw rate")
        w("  (differences beyond ~0.5 points suggest a layout or export problem)")
        for item, g in r.groupby("item"):
            for y, gy in g.groupby("year"):
                if str(y) not in log:
                    continue
                wr = gy["births_unknown"].sum() / gy["births_total"].sum()
                fr = log[str(y)]["raw_missing"][RECON[item]]
                flag = "" if abs(wr - fr) < 0.005 else "  <-- CHECK"
                fails += bool(flag)
                w(f"    {item:7s} {y}: WONDER {100 * wr:6.2f}%  file {100 * fr:6.2f}%{flag}")

        w("\n6. Named spot checks for the author (verify by hand in WONDER)")
        last = r["year"].max()
        for item, g in r[r["year"] == last].groupby("item"):
            g = g.sort_values("rate")
            picks = {"lowest": g.iloc[0], "median": g.iloc[len(g) // 2], "highest": g.iloc[-1]}
            for k, row in picks.items():
                w(f"    {item:7s} {last} {k:7s}: {row['state']:<22s} "
                  f"{int(row['births_unknown']):>7,} / {int(row['births_total']):>9,} = {100 * row['rate']:.2f}%")

    w(f"\nChecks flagged: {fails}")
    (proc / "qa_report.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
