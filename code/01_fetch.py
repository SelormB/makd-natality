#!/usr/bin/env python3
"""Download NCHS natality public-use zips for the configured years and log provenance.

Usage: python code/01_fetch.py [--years 2016 2017 ...]
Skips files already present. Each download appends a line to data/raw/PROVENANCE.txt
(file, bytes, SHA-256, URL, date). CDC WONDER exports are manual: see docs/WONDER_EXPORT_GUIDE.md.
"""
import argparse
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import load_config  # noqa: E402


def main():
    cfg = load_config()
    years = cfg["years"]["train"] + cfg["years"]["tune"] + cfg["years"]["test"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=years)
    a = ap.parse_args()
    raw = cfg["paths"]["raw"]
    raw.mkdir(parents=True, exist_ok=True)
    for y in a.years:
        name = cfg["source"]["files"][y]
        url = cfg["source"]["url_base"] + name
        dest = raw / name
        if dest.exists():
            print(f"[skip] {dest.name} exists")
            continue
        print(f"[get ] {url}")
        tmp = dest.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(dest)
        subprocess.run([sys.executable, str(Path(__file__).parent / "provenance.py"), str(dest), url,
                        "--log", str(raw / "PROVENANCE.txt"),
                        "--note", "NCHS natality public-use file; filename from the NCHS FTP directory listing"],
                       check=True)


if __name__ == "__main__":
    main()
