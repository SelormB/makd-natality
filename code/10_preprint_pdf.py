#!/usr/bin/env python3
"""Build a preprint-style PDF from paper/<run>/manuscript.md with pandoc + XeLaTeX.

Output: paper/<run>/MAKD-Natality_preprint_<label>.pdf. While config `final` is false the PDF
carries a DRAFT watermark and line numbers (for review). Respects MAKD_CONFIG.
Requires pandoc and a TeX distribution with xelatex, draftwatermark, lineno, fancyhdr.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import load_config  # noqa: E402


def main():
    cfg = load_config()
    paper = cfg["paths"]["paper"]
    label = cfg.get("run_label", "main")
    md = (paper / "manuscript.md").read_text()
    # title from the first H1; author line from the first line after it
    title = re.search(r"^# (.+)$", md, re.M).group(1)
    body = md.split(f"# {title}", 1)[1].lstrip("\n")
    author_line, body = body.split("\n", 1)
    banner = re.match(r"^> \*\*(.+?)\*\*", md)
    clean = os.environ.get("MAKD_CLEAN") == "1"
    draft = not (cfg["final"] or clean)
    header = [
        r"\usepackage{fancyhdr}", r"\pagestyle{fancy}", r"\fancyhf{}",
        r"\fancyhead[L]{\small MAKD-Natality}", r"\fancyhead[R]{\small " + ("Draft, not for circulation" if draft else "Preprint") + "}",
        r"\fancyfoot[C]{\thepage}", r"\renewcommand{\headrulewidth}{0.4pt}",
        r"\usepackage{float}", r"\floatplacement{figure}{H}",
        r"\usepackage{etoolbox}", r"\AtBeginEnvironment{longtable}{\footnotesize}",
    ]
    if draft:
        header += [r"\usepackage[firstpageonly=false]{draftwatermark}", r"\SetWatermarkText{DRAFT}",
                   r"\SetWatermarkScale{1.2}", r"\SetWatermarkLightness{0.92}",
                   r"\usepackage{lineno}", r"\linenumbers"]
    meta = ["---", f'title: "{title}"', "author: |"] + [f"  | {l}" for l in author_line.strip().split("|")] + [
            f'date: "{("Draft generated " if draft else "")}' + (lambda d: f"{d:%B} {d.day}, {d.year}")(__import__("datetime").date.today()) + '"',
            "header-includes:"] + [f"  - '{h}'" for h in header] + ["---", ""]
    if banner and draft:
        body = md[:md.index("\n#")].strip() + "\n\n" + body
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "preprint.md"
        src.write_text("\n".join(meta) + body)
        out = paper / ("MAKD-Natality_preprint.pdf" if clean else f"MAKD-Natality_preprint_{label}.pdf")
        cmd = ["pandoc", str(src), "-o", str(out), "--pdf-engine=xelatex",
               f"--resource-path={paper}", "-V", "geometry:margin=1in", "-V", "fontsize=11pt",
               "-V", "mainfont=DejaVu Serif", "-V", "linestretch=1.25", "-V", "colorlinks=true"]
        env = dict(__import__("os").environ)
        # some minimal TeX installs lack lmodern.sty, which pandoc's template requests;
        # a stub in tests/tex satisfies it (the font is DejaVu Serif via fontspec)
        env["TEXINPUTS"] = str(Path(__file__).resolve().parents[1] / "tests" / "tex") + "//:" + env.get("TEXINPUTS", "")
        subprocess.run(cmd, check=True, env=env)
    print(f"[preprint] -> {out}")


if __name__ == "__main__":
    main()
