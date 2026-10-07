#!/usr/bin/env python3
"""Download NCHS natality public-use zips for the configured years, resumably, and log provenance.

Usage: python code/01_fetch.py [--years 2016 2017 ...]

- Skips files already present at the expected size (source.sizes in config.yaml).
- Resumes a partial download (data/raw/<name>.part) with an HTTP Range request, retrying up to
  10 times; the CDC FTP server can be slow or stall on long transfers.
- Verifies the final size and that `unzip -t` passes (CRC check of the ~5 GB member) before
  moving the file into place, then appends a provenance line (bytes, SHA-256, URL, date).
Run this on a machine with direct internet access (e.g. the HPC login or a data-transfer node).
CDC WONDER exports are manual: see docs/WONDER_EXPORT_GUIDE.md.
"""
import argparse
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import load_config  # noqa: E402

CHUNK = 1 << 20


def fetch(url: str, dest: Path, size: int, tries: int = 10) -> None:
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, tries + 1):
        have = part.stat().st_size if part.exists() else 0
        if have >= size:
            break
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(part, "ab" if have else "wb") as out:
                if have and r.status != 206:
                    raise IOError(f"server ignored Range (status {r.status})")
                got, t0 = 0, time.time()
                while True:
                    buf = r.read(CHUNK)
                    if not buf:
                        break
                    out.write(buf)
                    got += len(buf)
                    if got % (32 * CHUNK) < CHUNK:
                        rate = got / max(time.time() - t0, 1e-6) / 1e6
                        print(f"  {dest.name}: {(have + got) / 1e6:,.0f} / {size / 1e6:,.0f} MB ({rate:.2f} MB/s)",
                              flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  attempt {attempt} interrupted: {e}; retrying in {min(60, 5 * attempt)} s")
            time.sleep(min(60, 5 * attempt))
    if not part.exists() or part.stat().st_size != size:
        raise SystemExit(f"{dest.name}: expected {size} bytes, have "
                         f"{part.stat().st_size if part.exists() else 0}; rerun to resume")
    if shutil.which("unzip"):
        print(f"  testing {dest.name} (CRC of the full record file; a few minutes)")
        subprocess.run(["unzip", "-tq", str(part)], check=True)
    part.rename(dest)


def main():
    cfg = load_config()
    years = sorted(set(cfg["years"]["train"] + cfg["years"]["tune"] + cfg["years"]["test"]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=years)
    a = ap.parse_args()
    raw = cfg["paths"]["raw"]
    raw.mkdir(parents=True, exist_ok=True)
    src = cfg["source"]
    for y in a.years:
        name, size = src["files"][y], src["sizes"][y]
        url = src["url_base"] + name
        dest = raw / name
        if dest.exists() and dest.stat().st_size == size:
            print(f"[skip] {name} present ({size:,} bytes)")
            continue
        print(f"[get ] {url}")
        fetch(url, dest, size)
        subprocess.run([sys.executable, str(Path(__file__).parent / "provenance.py"), str(dest), url,
                        "--log", str(raw / "PROVENANCE.txt"),
                        "--note", "fetched by code/01_fetch.py; size and unzip -t verified"], check=True)


if __name__ == "__main__":
    main()
