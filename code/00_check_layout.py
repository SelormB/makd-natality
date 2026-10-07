#!/usr/bin/env python3
"""Check every field position in config.yaml against each year's NCHS User Guide (verify point V1).

For each year, finds the User Guide PDF in docs/sources/user_guides/ (UserGuide<year>*.pdf),
extracts its text with `pdftotext -layout`, and looks for the line that defines each field:
"<start>-<end> <width> <FIELD_NAME>" (or "<pos> 1 <FIELD_NAME>" for one-byte fields).
Field names are matched with spaces removed, because the PDFs sometimes split names
("RF_P DIAB", "O EGest_Comb").

Writes data/processed/layout_check.csv and prints a summary. Exit code 1 if any configured
field is found at a different position in any guide; fields not found are listed for a manual look.

Usage: python code/00_check_layout.py
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import layout_for_year, load_config  # noqa: E402

ROW = re.compile(r"^\s*(\d{1,4})(?:\s*-\s*(\d{1,4}))?\s+(\d{1,3})\s+(\S+)(?:\s(\S+))?")


def guide_for(year: int, folder: Path):
    hits = sorted(folder.glob(f"*UserGuide{year}*.pdf"))
    return hits[0] if hits else None


def positions_in_guide(pdf: Path) -> dict:
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                         text=True, check=True).stdout
    found = {}
    for line in txt.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        # The name is the first token, or the first two tokens joined when the PDF split it
        # ("RF_P DIAB", "O EGest_Comb").
        t1 = m.group(4).upper()
        found.setdefault(t1, (start, end))
        if m.group(5):
            found.setdefault(t1 + m.group(5).upper(), (start, end))
    return found


def main():
    cfg = load_config()
    root = Path(__file__).resolve().parents[1]
    folder = root / "docs/sources/user_guides"
    years = cfg["years"]["train"] + cfg["years"]["tune"] + cfg["years"]["test"]
    rows, bad, missing_guides = [], 0, []
    for y in years:
        pdf = guide_for(y, folder)
        if pdf is None:
            missing_guides.append(y)
            continue
        found = positions_in_guide(pdf)
        for field, spec in layout_for_year(cfg, y).items():
            key = field.upper()
            got = found.get(key)
            status = "not_found" if got is None else ("ok" if got == (spec["start"], spec["end"]) else "MISMATCH")
            bad += status == "MISMATCH"
            rows.append({"year": y, "guide": pdf.name, "field": field, "config_start": spec["start"],
                         "config_end": spec["end"], "guide_start": got[0] if got else "",
                         "guide_end": got[1] if got else "", "status": status})
    out = cfg["paths"]["processed"] / "layout_check.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["year"])
        w.writeheader()
        w.writerows(rows)
    by_year = {}
    for r in rows:
        by_year.setdefault(r["year"], {}).setdefault(r["status"], []).append(r["field"])
    for y, d in by_year.items():
        print(f"{y}: ok {len(d.get('ok', []))}"
              + (f"; MISMATCH {d['MISMATCH']}" if d.get("MISMATCH") else "")
              + (f"; not found in guide text {d['not_found']}" if d.get("not_found") else ""))
    if missing_guides:
        print(f"no User Guide PDF for: {missing_guides} (put UserGuide<year>.pdf in {folder})")
    print(f"-> {out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
