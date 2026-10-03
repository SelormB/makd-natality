#!/usr/bin/env python3
"""Parse CDC WONDER Natality (Expanded) exports into state x year x item unknown rates.

Input: data/wonder/wonder_<item>.txt, one per masked item, each exported with
  Group By: State of Residence, Year, <item variable>   (see docs/WONDER_EXPORT_GUIDE.md)
Output: data/processed/state_rates.csv with columns state, state_code, year, item,
  births_total, births_unknown, births_not_available, rate, suppressed_cells
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import load_config  # noqa: E402


def read_wonder_export(path: Path) -> pd.DataFrame:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    body = []
    for ln in lines:
        if ln.startswith('"---"'):
            break
        body.append(ln)
    from io import StringIO
    return pd.read_csv(StringIO("\n".join(body)), sep="\t", dtype=str).dropna(how="all")


def parse_item(path: Path, item: str, unknown_re: re.Pattern, suppressed_value: float) -> pd.DataFrame:
    df = read_wonder_export(path)
    notes = df["Notes"] if "Notes" in df.columns else pd.Series("", index=df.index)
    cols = [c for c in df.columns if c != "Notes"]
    state = next(c for c in cols if c.startswith("State") and not c.endswith("Code"))
    state_code = next((c for c in cols if c.startswith("State") and c.endswith("Code")), None)
    year = next(c for c in cols if c == "Year")
    births = next(c for c in cols if c == "Births")
    label = next(c for c in cols if c not in (state, state_code, year, births)
                 and not c.endswith("Code"))
    num = pd.to_numeric(df[births].str.replace(",", ""), errors="coerce")
    is_total = notes.fillna("").str.strip().eq("Total") & df[label].isna()
    # state-year denominators from WONDER's own Total rows (not affected by cell suppression)
    tot = (df[is_total & df[state].notna() & df[year].notna()]
           .assign(_b=num).groupby([df[state], df[year]])["_b"].first())
    d = df[~notes.fillna("").str.strip().eq("Total") & df[label].notna()].copy()
    d["_births"] = num.loc[d.index]
    d["_supp"] = d[births].str.contains("Suppressed", case=False, na=False)
    d["_unk"] = d[label].str.contains(unknown_re)
    d["_na"] = d[label].str.contains("not available", case=False)
    # suppressed unknown cells hold 1-9 births; use the configured value and count them
    d.loc[d["_supp"], "_births"] = suppressed_value
    g = d.groupby([state, year])
    out = pd.DataFrame({
        "births_unknown": g.apply(lambda x: x.loc[x["_unk"], "_births"].sum(), include_groups=False),
        "births_not_available": g.apply(lambda x: x.loc[x["_na"], "_births"].sum(), include_groups=False),
        "suppressed_unknown_cells": g.apply(lambda x: int((x["_supp"] & x["_unk"]).sum()), include_groups=False),
        "suppressed_cells": g["_supp"].sum(),
        "births_sum_cells": g["_births"].sum(),
    })
    out["births_total"] = tot.reindex(out.index)
    out["births_total"] = out["births_total"].fillna(out["births_sum_cells"])
    out = out.reset_index().rename(columns={state: "state", year: "year"})
    if state_code:
        codes = d.drop_duplicates(state).set_index(state)[state_code]
        out["state_code"] = out["state"].map(codes)
    out["year"] = out["year"].astype(int)
    out["item"] = item
    out["wonder_label_column"] = label
    out["rate"] = out["births_unknown"] / out["births_total"]
    return out


def main():
    cfg = load_config()
    rx = re.compile(cfg["wonder"]["unknown_regex"], re.I)
    frames = []
    for item, spec in cfg["masked_items"].items():
        p = cfg["paths"]["wonder"] / spec["wonder_file"]
        if not p.exists():
            sys.exit(f"missing WONDER export: {p} (see docs/WONDER_EXPORT_GUIDE.md)")
        frames.append(parse_item(p, item, rx, cfg["wonder"]["suppressed_value"]))
    rates = pd.concat(frames, ignore_index=True)
    out = cfg["paths"]["processed"] / "state_rates.csv"
    rates.to_csv(out, index=False)
    print(f"[wonder] {len(rates)} state-year-item rows -> {out}")


if __name__ == "__main__":
    main()
