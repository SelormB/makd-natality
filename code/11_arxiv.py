#!/usr/bin/env python3
"""Build the arXiv-format preprint (LaTeX article class, numbered references).

Every number in the paper comes from stats.json, the training/parse logs and the config through
paper/arxiv/numbers.tex and the generated tables; the prose lives in paper/arxiv/main.tex.
Outputs: paper/arxiv/main.pdf, a copy at paper/<run>/MAKD-Natality_preprint.pdf, and an
arXiv source bundle paper/arxiv/arxiv_source.tar.gz (main.tex, .bbl, tables, figures).
Respects MAKD_CONFIG.
"""
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import ROOT, load_config  # noqa: E402

AX = ROOT / "paper" / "arxiv"
LAB = {"T_oracle": "Teacher, full information", "KD_state": "Distilled student, per state",
       "KD_pooled": "Distilled student, pooled", "B3_state": "Non-distilled student, per state (B3)",
       "B3_pooled": "Non-distilled student, pooled (B3)", "B1_teacher_meanimp": "Teacher + mean imputation (B1)",
       "B2_teacher_iterimp": "Teacher + iterative imputation (B2)",
       "B4_logistic_pooled": "Logistic regression + indicators (B4)"}
ORDER = list(LAB)
MECH = {"MCAR": "MCAR", "MAR": "MAR", "MARx5": r"MAR, rates $\times$5"}


def sg(v, nd=2):
    s = f"{v:+.{nd}f}"
    s = s[1:] if float(s) == 0 else s
    return s.replace("-", "$-$")


def mac(name, val):
    return f"\\newcommand{{\\{name}}}{{{val}}}\n"


def numbers(cfg, stats, plog, tlog, sub):
    y, o, nat = cfg["years"], stats["outcomes"], stats["natural"]
    pct = int(round(100 * y.get("holdout_frac", 0.2)))
    tr = [str(t) for t in y["train"]]
    shared = set(y["train"]) & set(y["tune"])
    trtxt = ", ".join(f"{t} ({100 - pct}\\% of records)" if int(t) in shared else t for t in tr[:-1])
    last = tr[-1] + (f" ({100 - pct}\\% of records)" if int(tr[-1]) in shared else "")
    m = ""
    m += mac("TrainYears", f"{trtxt} and {last}")
    m += mac("TuneYear", f"{y['tune'][0]} (held-out {pct}\\%)" if shared else str(y["tune"][0]))
    m += mac("TestYear", str(y["test"][0]))
    m += mac("YearsAll", ", ".join(str(v) for v in sorted(set(y["train"] + y["tune"] + y["test"]))))
    cohort = {int(k): v["steps"]["gest_in_range"] for k, v in plog.items()}
    m += mac("NCohortTotal", f"{sum(cohort.values()):,}")
    m += mac("NCohortTest", f"{cohort[y['test'][0]]:,}")
    m += mac("NTeacher", f"{tlog['teacher_train_n']:,}")
    m += mac("NStudentTrain", f"{cfg['models']['student_train_n']:,}")
    m += mac("NStates", str(stats["n_states"]))
    st = tlog["student_states"]
    m += mac("NStateStudents", str(len(st)))
    m += mac("NTopStates", str(len(st) - 2))
    m += mac("StudentStates", ", ".join(sorted(st)))
    m += mac("EvalN", f"{stats['eval_n_test']:,}")
    m += mac("NaturalN", f"{stats['natural_missing_n_test']:,}")
    m += mac("Kfold", str(cfg["models"]["crossfit_folds"]))
    m += mac("KDalpha", str(cfg["models"]["kd"]["alpha"]))
    m += mac("KDtau", str(cfg["models"]["kd"]["tau"]))
    m += mac("BootB", str(cfg["evaluation"]["bootstrap_B"]))
    m += mac("AlertPct", f"{int(round(100 * cfg['evaluation']['alert_rate']))}\\%")
    m += mac("SensTarget", f"{int(round(100 * cfg['evaluation']['teacher_sensitivity_target']))}\\%")
    lg = cfg["models"]["lgbm"]
    m += mac("LGBMlr", str(lg["learning_rate"])) + mac("LGBMleaves", str(lg["num_leaves"]))
    m += mac("LGBMminleaf", str(lg["min_data_in_leaf"])) + mac("LGBMstop", str(lg["early_stopping_rounds"]))
    mr = {mm["name"]: mm for mm in stats["mechanisms"]}
    m += mac("MARbeta", f"{mr['MAR']['beta']:g}") + mac("MARrho", f"{mr['MAR']['rho']:g}")
    w = cfg["masks"]["mar_weights"] if "masks" in cfg else {}
    for k, v in w.items():
        m += mac("W" + "".join(p.capitalize() for p in k.split("_")).replace("Nh", "Nh"), f"{v:g}".replace("-", "$-$"))
    m += mac("StressMult", f"{mr['MARx5']['rate_multiplier']:g}")
    r = stats["mean_unknown_rate_by_state"]
    m += mac("RateMin", f"{100 * min(r.values()):.1f}\\%") + mac("RateMax", f"{100 * max(r.values()):.1f}\\%")
    for oc in ("LBW", "PTB"):
        mm = o[oc]["mechanisms"]["MAR"]
        m += mac(f"Prev{oc}", f"{100 * o[oc]['prevalence_test']:.1f}\\%")
        m += mac(f"Teacher{oc}Trees", str(tlog[f"T_{oc}"]["trees"]))
        for k, tag in [("KD_state", "KDs"), ("KD_pooled", "KDp"), ("B3_state", "Bthrees"), ("B1_teacher_meanimp", "Bone"),
                       ("B2_teacher_iterimp", "Btwo"), ("B4_logistic_pooled", "Bfour"), ("T_oracle", "T")]:
            x = mm[k]
            m += mac(f"{oc}{tag}Auc", f"{x['auroc']['median']:.3f}")
            m += mac(f"{oc}{tag}Ppv", f"{100 * x['ppv_alert']['median']:.1f}")
            if k != "T_oracle":
                m += mac(f"{oc}{tag}PpvGap", sg(100 * x["ppv_alert"]["gap_median"]))
        c = mm["_kd_vs_b3_state"]
        m += mac(f"{oc}KDhigherAuc", str(c["states_kd_higher_auroc"]))
        m += mac(f"{oc}KDhigherPpv", str(c["states_kd_higher_ppv_alert"]))
        m += mac(f"{oc}KDlowerIci", str(c["states_kd_lower_ici"]))
        e = nat[oc]["MAR"]
        m += mac(f"{oc}NatEvents", f"{e['models']['KD_pooled']['events']:,}")
        m += mac(f"{oc}NatKDAuc", f"{e['models']['KD_pooled']['auroc']:.3f}")
        m += mac(f"{oc}NatKDPpv", f"{100 * e['models']['KD_pooled']['ppv_alert']:.1f}")
        for k, tag in [("B1_teacher_meanimp", "One"), ("B2_teacher_iterimp", "Two"), ("B3_pooled", "Three"),
                       ("B4_logistic_pooled", "Four")]:
            d = e["diffs"][k]
            m += mac(f"{oc}NatAuc{tag}", f"{sg(d['auroc'][0], 3)} to {sg(d['auroc'][1], 3)}")
            m += mac(f"{oc}NatPpv{tag}", f"{sg(100 * d['ppv_alert'][0])} to {sg(100 * d['ppv_alert'][1])}")
    m += mac("NStudentsCompared", str(o["LBW"]["mechanisms"]["MAR"]["_kd_vs_b3_state"]["n_states"]))
    m += mac("SubCells", str(sub["cells"])) + mac("SubTight", str(sub["tight"])) + mac("SubBfourLow", str(sub["b4low"]))
    return m


def subgroup_counts(paper):
    d = pd.read_csv(paper / "tables" / "subgroups.csv")
    d = d[d.mechanism == "MAR"]
    c = {"cells": 0, "tight": 0, "b4low": 0}
    for _, x in d.groupby(["outcome", "subgroup", "level"]):
        x = x.set_index("model").ppv_alert
        c["cells"] += 1
        c["b4low"] += int(x.idxmin() == "B4_logistic_pooled")
        t = x.drop("B4_logistic_pooled", errors="ignore")
        c["tight"] += int((t.max() - t.min()) < 0.01)
    return c


def tab_mar(stats):
    rows = []
    for oc in ("LBW", "PTB"):
        mm = stats["outcomes"][oc]["mechanisms"]["MAR"]
        rows.append(f"\\multicolumn{{7}}{{l}}{{\\textit{{{'Low birthweight' if oc == 'LBW' else 'Preterm birth'}}}}}\\\\")
        for k in ORDER:
            if k not in mm:
                continue
            x, ref = mm[k], k == "T_oracle"
            rows.append(f"\\quad {LAB[k]} & {x['auroc']['median']:.3f} & {100 * x['auprc']['median']:.1f} & "
                        f"{100 * x['ppv_alert']['median']:.1f} & "
                        f"{'--' if ref else sg(100 * x['ppv_alert']['gap_median'])} & "
                        f"{'--' if ref else sg(100 * x['sens_alert']['gap_median'])} & "
                        f"{100 * x['ici']['median']:.2f}\\\\")
        if oc == "LBW":
            rows.append("\\addlinespace")
    return ("\\begin{tabular}{lrrrrrr}\n\\toprule\nModel & AUROC & AUPRC (\\%) & PPV (\\%) & "
            "$\\Delta$PPV & $\\Delta$Sens. & ICI (\\%)\\\\\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_mech(stats):
    mechs = [m["name"] for m in stats["mechanisms"]]
    rows = []
    for oc in ("LBW", "PTB"):
        md = stats["outcomes"][oc]["mechanisms"]
        rows.append(f"\\multicolumn{{{1 + len(mechs)}}}{{l}}{{\\textit{{{'Low birthweight' if oc == 'LBW' else 'Preterm birth'}}}}}\\\\")
        for k in ORDER[1:]:
            if all(k in md[m] for m in mechs):
                rows.append(f"\\quad {LAB[k]} & " + " & ".join(sg(100 * md[m][k]["ppv_alert"]["gap_median"]) for m in mechs) + "\\\\")
        if oc == "LBW":
            rows.append("\\addlinespace")
    return ("\\begin{tabular}{l" + "r" * len(mechs) + "}\n\\toprule\nModel & " + " & ".join(MECH[m] for m in mechs)
            + "\\\\\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_natural(stats):
    rows = []
    for oc in ("LBW", "PTB"):
        e = stats["natural"][oc]["MAR"]
        rows.append(f"\\multicolumn{{5}}{{l}}{{\\textit{{{'Low birthweight' if oc == 'LBW' else 'Preterm birth'}}}}}\\\\")
        for k in ORDER:
            x = e["models"].get(k)
            if not x:
                continue
            ci, d = x["ci"], e["diffs"].get(k)
            rows.append(f"\\quad {LAB[k]} & {x['auroc']:.3f} ({ci['auroc'][0]:.3f}, {ci['auroc'][1]:.3f}) & "
                        f"{100 * x['ppv_alert']:.1f} ({100 * ci['ppv_alert'][0]:.1f}, {100 * ci['ppv_alert'][1]:.1f}) & "
                        + (f"{sg(d['auroc'][0], 3)}, {sg(d['auroc'][1], 3)} & {sg(100 * d['ppv_alert'][0])}, "
                           f"{sg(100 * d['ppv_alert'][1])}\\\\" if d else "-- & --\\\\"))
        if oc == "LBW":
            rows.append("\\addlinespace")
    return ("\\begin{tabular}{lllll}\n\\toprule\n & & & \\multicolumn{2}{c}{Distilled minus comparator (95\\% CI)}\\\\\n"
            "\\cmidrule(lr){4-5}\nModel & AUROC (95\\% CI) & PPV, \\% (95\\% CI) & AUROC & PPV (points)\\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def main():
    cfg = load_config()
    paper = cfg["paths"]["paper"]
    stats = json.loads((paper / "stats.json").read_text())
    plog = json.loads((cfg["paths"]["processed"] / "parse_log.json").read_text())
    tlog = json.loads((cfg["paths"]["processed"] / "models" / "train_log.json").read_text())
    authors = json.loads((ROOT / "AUTHORS.json").read_text())["authors"]
    (AX / "figures").mkdir(parents=True, exist_ok=True)
    for f in (paper / "figures").glob("*.png"):
        shutil.copy(f, AX / "figures" / f.name)
    a = authors[0]
    meta = (mac("AuthorName", a["name"]) + mac("AuthorAff", a["affiliation"]) + mac("AuthorEmail", a["email"])
            + mac("AuthorOrcid", a["orcid"]))
    (AX / "numbers.tex").write_text("% generated by code/11_arxiv.py; do not edit\n" + meta
                                    + numbers(cfg, stats, plog, tlog, subgroup_counts(paper)))
    (AX / "tab_mar.tex").write_text(tab_mar(stats))
    (AX / "tab_mech.tex").write_text(tab_mech(stats))
    (AX / "tab_natural.tex").write_text(tab_natural(stats))
    run = lambda *c: subprocess.run(list(c), cwd=AX, check=True, stdout=subprocess.DEVNULL)  # noqa: E731
    run("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex")
    run("bibtex", "main")
    run("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex")
    run("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex")
    shutil.copy(AX / "main.pdf", paper / "MAKD-Natality_preprint.pdf")
    with tarfile.open(AX / "arxiv_source.tar.gz", "w:gz") as t:
        for n in ["main.tex", "main.bbl", "numbers.tex", "tab_mar.tex", "tab_mech.tex", "tab_natural.tex", "refs.bib"]:
            t.add(AX / n, arcname=n)
        for f in sorted((AX / "figures").glob("*.png")):
            t.add(f, arcname=f"figures/{f.name}")
    print(f"[arxiv] -> {paper / 'MAKD-Natality_preprint.pdf'} and {AX / 'arxiv_source.tar.gz'}")


if __name__ == "__main__":
    main()
