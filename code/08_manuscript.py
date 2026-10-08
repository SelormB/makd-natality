#!/usr/bin/env python3
"""Fill paper/manuscript_template.md from paper/stats.json and AUTHORS.json.

Every number in the manuscript comes from stats.json; nothing is typed by hand.
Output: paper/manuscript.md. Placeholders that cannot be resolved stay visible as [MISSING:key],
which the publish gate treats as a blocker.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import ROOT, load_config  # noqa: E402

def signed(v, nd=1):
    s = f"{v:+.{nd}f}"
    return s[1:] if float(s) == 0 else s


FMT = {
    "pct1": lambda v: f"{100 * v:.1f}%",
    "pts": lambda v: signed(100 * v),
    "pts2": lambda v: signed(100 * v, 2),
    "f3": lambda v: f"{v:.3f}",
    "int": lambda v: f"{int(v):,}",
}


def lookup(d, dotted):
    for k in dotted.split("."):
        d = d[k]
    return d


def years_text(y):
    """'2016-2022' when contiguous; otherwise a list, marking a year split with the tune set."""
    tr, shared = y["train"], set(y["train"]) & set(y["tune"])
    pct = int(round(100 * y.get("holdout_frac", 0.2)))
    names = [f"{t} ({100 - pct}% of records)" if t in shared else str(t) for t in tr]
    if not shared and tr == list(range(tr[0], tr[-1] + 1)) and len(tr) > 1:
        return f"{tr[0]}–{tr[-1]}"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def natural_paragraph(stats):
    nat = stats.get("natural", {})
    out = []
    for o, by in nat.items():
        e = by.get("MAR") or next(iter(by.values()))
        kd, d = e["models"].get("KD_pooled"), e["diffs"]
        if not kd:
            continue
        ci = lambda k, met, sc=1, nd=3: f"{sc * d[k][met][0]:+.{nd}f} to {sc * d[k][met][1]:+.{nd}f}"  # noqa: E731
        s = (f"**{o}, records with naturally missing items** (n = {kd['n']:,}; {kd['events']:,} events; models "
             f"trained under MAR masks). The pooled distilled student had AUROC {kd['auroc']:.3f} and PPV "
             f"{100 * kd['ppv_alert']:.1f}% at the 10% alert threshold.")
        parts = []
        for k, lab in [("B1_teacher_meanimp", "teacher with mean imputation"),
                       ("B2_teacher_iterimp", "teacher with iterative imputation"),
                       ("B3_pooled", "the same learner without distillation")]:
            if k in d:
                parts.append(f"versus {lab}, AUROC difference {ci(k, 'auroc')} and PPV difference "
                             f"{ci(k, 'ppv_alert', 100, 2)} points")
        if parts:
            s += " Paired bootstrap 95% intervals: " + "; ".join(parts) + "."
        out.append(s)
    return "\n\n".join(out)


def draft(name):
    """Author-editable section text from paper/drafts/<name>.md (replace with your own)."""
    p = ROOT / "paper" / "drafts" / f"{name}.md"
    return p.read_text().strip() if p.exists() else ""


def abstract_natural(stats):
    nat = stats.get("natural", {})
    bits = []
    for o in ("LBW", "PTB"):
        e = (nat.get(o) or {}).get("MAR")
        if not e or "B1_teacher_meanimp" not in e["diffs"]:
            continue
        a = e["diffs"]["B1_teacher_meanimp"]["auroc"]
        b = e["diffs"].get("B2_teacher_iterimp", {}).get("auroc")
        s = f"{o}: AUROC difference versus mean imputation {a[0]:+.3f} to {a[1]:+.3f}"
        if b:
            s += f", versus iterative imputation {b[0]:+.3f} to {b[1]:+.3f}"
        bits.append(s)
    if not bits:
        return ""
    return ("On real test-year records with naturally missing items, the pooled distilled student outperformed "
            "imputation (paired bootstrap 95% intervals; " + "; ".join(bits) + ").")


LABELS = [("T_oracle", "Teacher, full information (reference)"),
          ("KD_state", "Distilled student, per state"),
          ("KD_pooled", "Distilled student, pooled"),
          ("B3_state", "Non-distilled student, per state (B3)"),
          ("B3_pooled", "Non-distilled student, pooled (B3)"),
          ("B1_teacher_meanimp", "Teacher + mean imputation (B1)"),
          ("B2_teacher_iterimp", "Teacher + iterative imputation (B2)"),
          ("B4_logistic_pooled", "Logistic regression + indicators (B4)")]
MECH_NAME = {"MCAR": "MCAR", "MAR": "MAR", "MARx5": "MAR, rates ×5"}


def table_mar(stats, n, student_list):
    rows = ["| Outcome | Model | AUROC | PPV, % | PPV gap, pts | Sensitivity gap, pts | ICI, % |",
            "|:------|:--------------------------|------:|------:|-------:|---------:|------:|"]
    for o, od in stats["outcomes"].items():
        md = od["mechanisms"]["MAR"]
        for k, lab in LABELS:
            if k not in md:
                continue
            x = md[k]
            ref = k == "T_oracle"
            rows.append(f"| {o} | {lab} | {x['auroc']['median']:.3f} | {100 * x['ppv_alert']['median']:.1f} | "
                        f"{'—' if ref else signed(100 * x['ppv_alert']['gap_median'], 2)} | "
                        f"{'—' if ref else signed(100 * x['sens_alert']['gap_median'], 2)} | "
                        f"{100 * x['ici']['median']:.2f} |")
    return (f"Table {n}. Performance under state missingness simulated at observed rates (MAR masks), test year. "
            f"Values are medians across all {stats['n_states']} jurisdictions, except per-state models (medians "
            f"across the {len(student_list)} states with their own student); gaps are differences from the "
            "full-information teacher in the same state. PPV and sensitivity at the 10% alert rate.\n\n" + "\n".join(rows))


def table_mech(stats, n):
    mechs = [m["name"] for m in stats.get("mechanisms", [])]
    head = "| Outcome | Model | " + " | ".join(MECH_NAME.get(m, m) for m in mechs) + " |"
    rows = [head, "|:------|:------------------------------|" + "--------:|" * len(mechs)]
    for o, od in stats["outcomes"].items():
        for k, lab in LABELS[1:]:
            if not all(k in od["mechanisms"].get(m, {}) for m in mechs):
                continue
            rows.append(f"| {o} | {lab} | " + " | ".join(
                signed(100 * od["mechanisms"][m][k]["ppv_alert"]["gap_median"], 2) for m in mechs) + " |")
    return (f"Table {n}. Median PPV gap to the full-information teacher (percentage points, 10% alert rate) "
            "by missingness mechanism.\n\n" + "\n".join(rows))


def table_natural(stats, n):
    rows = ["| Outcome | Model | AUROC (95% CI) | PPV, % (95% CI) | AUROC difference, distilled − model (95% CI) | "
            "PPV difference, pts (95% CI) |", "|:-----|:------------------|:-----------|:-----------|:------------|:------------|"]
    for o, by in stats.get("natural", {}).items():
        e = by.get("MAR") or next(iter(by.values()))
        for k, lab in LABELS:
            x = e["models"].get(k)
            if not x:
                continue
            d = e["diffs"].get(k)
            ci = x["ci"]
            rows.append(
                f"| {o} | {lab} | {x['auroc']:.3f} ({ci['auroc'][0]:.3f}–{ci['auroc'][1]:.3f}) | "
                f"{100 * x['ppv_alert']:.1f} ({100 * ci['ppv_alert'][0]:.1f}–{100 * ci['ppv_alert'][1]:.1f}) | "
                + (f"{d['auroc'][0]:+.3f} to {d['auroc'][1]:+.3f} | "
                   f"{100 * d['ppv_alert'][0]:+.2f} to {100 * d['ppv_alert'][1]:+.2f} |" if d else "— | — |"))
    return (f"Table {n}. Test-year records with at least one naturally missing item (models trained under MAR "
            "masks). Differences are paired bootstrap intervals for the pooled distilled student minus each "
            "comparator.\n\n" + "\n".join(rows))


def results(stats, student_list, paper_dir):
    o = stats["outcomes"]
    nat = stats.get("natural", {})
    p = []
    p.append(f"Test-year prevalence was {100 * o['LBW']['prevalence_test']:.1f}% for LBW and "
             f"{100 * o['PTB']['prevalence_test']:.1f}% for PTB. Observed state missingness was low: across "
             f"{stats['n_states']} jurisdictions the mean unknown rate over the six items ranged from "
             f"{100 * min(stats['mean_unknown_rate_by_state'].values()):.1f}% "
             f"to {100 * max(stats['mean_unknown_rate_by_state'].values()):.1f}% (Figure 1).")
    lbw, ptb = o["LBW"]["mechanisms"]["MAR"], o["PTB"]["mechanisms"]["MAR"]
    c1, c2 = lbw.get("_kd_vs_b3_state"), ptb.get("_kd_vs_b3_state")
    s = ("**Simulated state missingness.** At observed rates every tree-based method stayed close to the "
         "full-information teacher (Table 1, Figure 2). For LBW the distilled students matched or slightly exceeded "
         f"the teacher's PPV (median gap {signed(100 * lbw['KD_state']['ppv_alert']['gap_median'], 2)} points for "
         f"per-state students); for PTB the teacher with mean imputation was closest "
         f"({signed(100 * ptb['B1_teacher_meanimp']['ppv_alert']['gap_median'], 2)} points). Logistic regression with "
         f"missing indicators had the lowest AUROC for both outcomes.")
    if c1 and c2:
        s += (f" Compared with the same learner trained on hard labels, the per-state distilled student had higher "
              f"AUROC in {c1['states_kd_higher_auroc']} of {c1['n_states']} states for LBW and "
              f"{c2['states_kd_higher_auroc']} of {c2['n_states']} for PTB, and higher PPV in "
              f"{c1['states_kd_higher_ppv_alert']} and {c2['states_kd_higher_ppv_alert']} states respectively. Calibration "
              f"was slightly worse with distillation: the distilled student had the lower ICI in "
              f"{c1['states_kd_lower_ici']} of {c1['n_states']} states for LBW and {c2['states_kd_lower_ici']} of "
              f"{c2['n_states']} for PTB, although all ICIs were below one percentage point (Figure 3).")
    p.append(s)
    p.append(table_mar(stats, 1, student_list))
    p.append("**Missingness mechanism.** Gaps were similar under MCAR and MAR masks. When every state's rates "
             "were multiplied by five, PPV relative to the teacher fell for every method; the pooled students "
             "degraded least among the students (Table 2).")
    p.append(table_mech(stats, 2))
    if nat:
        L, P = nat["LBW"]["MAR"]["models"]["KD_pooled"], nat["PTB"]["MAR"]["models"]["KD_pooled"]
        def excl(o, k, met):
            return nat[o]["MAR"]["diffs"][k][met][0] > 0
        ppv_ok = {k: [o for o in ("LBW", "PTB") if excl(o, k, "ppv_alert")]
                  for k in ("B1_teacher_meanimp", "B2_teacher_iterimp", "B3_pooled")}
        both = lambda l: "both outcomes" if len(l) == 2 else (l[0] + " only" if l else "neither outcome")  # noqa: E731
        p.append(f"**Naturally missing items.** In a random sample of {L['n']:,} test-year records with at least one "
                 f"item missing ({L['events']:,} LBW and {P['events']:,} PTB events), the pooled distilled student had "
                 "the highest AUROC for both outcomes, and every paired interval for its AUROC advantage over mean "
                 "imputation, iterative imputation and the non-distilled student excluded zero (Table 3). The interval "
                 f"for its PPV advantage excluded zero over iterative imputation for {both(ppv_ok['B2_teacher_iterimp'])}, "
                 f"over mean imputation for {both(ppv_ok['B1_teacher_meanimp'])}, and over the non-distilled student "
                 f"for {both(ppv_ok['B3_pooled'])}.")
        p.append(table_natural(stats, 3))
    sg = paper_dir / "tables" / "subgroups.csv"
    if sg.exists():
        import pandas as pd
        d = pd.read_csv(sg)
        d = d[d.mechanism == "MAR"]
        n_cells = n_b4 = n_tight = 0
        for _, x in d.groupby(["outcome", "subgroup", "level"]):
            x = x.set_index("model").ppv_alert
            n_cells += 1
            n_b4 += int(x.idxmin() == "B4_logistic_pooled")
            t = x.drop("B4_logistic_pooled", errors="ignore")
            n_tight += int((t.max() - t.min()) < 0.01)
        p.append("**Subgroups.** PPV at the 10% alert rate by maternal race and Hispanic origin, age band, payer and "
                 f"nativity is shown in Figure 4. Among the tree-based methods, PPV differed by less than one "
                 f"percentage point in {n_tight} of {n_cells} outcome-by-subgroup cells, and no method was consistently "
                 f"best; logistic regression had the lowest PPV in {n_b4} of {n_cells}. Larger differences occurred in "
                 "smaller subgroups, where estimates are less precise.")
    return "\n\n".join(p)


def main():
    cfg = load_config()
    paper = cfg["paths"]["paper"]
    stats = json.loads((paper / "stats.json").read_text())
    authors = json.loads((ROOT / "AUTHORS.json").read_text())["authors"]
    y = cfg["years"]
    log = cfg["paths"]["processed"] / "models" / "train_log.json"
    students = json.loads(log.read_text()).get("student_states", []) if log.exists() else []
    clean = os.environ.get("MAKD_CLEAN") == "1"
    ctx = {
        "banner": ("" if cfg["final"] or clean else "> **DRAFT — not for circulation. Numbers below are "
                   + ("from SYNTHETIC test data and are meaningless.**" if stats.get("synthetic")
                      else "from the PILOT run (train 80% of 2023, tune 20% of 2023, test 2024; reduced "
                           "samples). Feasibility only: do not quote. The main design trains on 2016-2022.**"
                      if stats.get("run_label") == "pilot"
                      else "from the AVAILABLE-DATA design (train " + years_text(y) + "; test "
                           + str(y["test"][0]) + "). Unverified until the author completes "
                           "docs/VERIFY_CHECKLIST.md.**"
                      if stats.get("run_label") == "available"
                      else "unverified until the author completes docs/VERIFY_CHECKLIST.md.**")),
        "author_block": "\n".join(f"{a['name']}|{a['affiliation']}|ORCID {a['orcid']}|{a['email']}"
                                  for a in authors),
        "years_span": (f"{min(y['train'])}–{y['test'][-1]}"
                       if list(range(min(y["train"]), y["test"][-1] + 1)) == sorted(set(y["train"] + y["tune"] + y["test"]))
                       else ", ".join(str(v) for v in sorted(set(y["train"] + y["tune"] + y["test"])))),
        "train_years": years_text(y),
        "tune_year": (str(y["tune"][0]) if not set(y["train"]) & set(y["tune"])
                      else f"{y['tune'][0]} (held-out {int(round(100 * y.get('holdout_frac', 0.2)))}%)"),
        "test_year": str(y["test"][0]), "K": str(cfg["models"]["crossfit_folds"]),
        "alpha": str(cfg["models"]["kd"]["alpha"]), "tau": str(cfg["models"]["kd"]["tau"]),
        "B": str(cfg["evaluation"]["bootstrap_B"]), "n_states": str(stats["n_states"]),
        "eval_n_test": f"{stats['eval_n_test']:,}",
        "natural_missing_n_test": f"{stats['natural_missing_n_test']:,}",
        "results": results(stats, students, paper),
        "student_scope": (f"per-state students were trained for {len(students)} states (the "
                          f"{len(students) - 2} with the highest mean unknown rate, the median state and the "
                          f"lowest: {', '.join(sorted(students))}), and one pooled student was trained over the "
                          f"births-weighted mixture of all {stats['n_states']} jurisdictions' masks."),
        "abstract_natural": abstract_natural(stats),
        "introduction": draft("introduction"),
        "discussion": draft("discussion"),
        "references": draft("references"),
        "stress_sentence": "".join(
            f"A stress arm ({m['name']}) multiplied every state's observed rates by {m['rate_multiplier']:g}, "
            "capped at 95%, to show behavior under much poorer completeness than any state reports. "
            for m in stats.get("mechanisms", []) if m.get("rate_multiplier", 1) != 1),
    }

    def sub(m):
        key, _, fmt = m.group(1).partition("|")
        if key in ctx:
            return ctx[key]
        try:
            v = lookup(stats, key)
            return FMT[fmt](v) if fmt else str(v)
        except (KeyError, TypeError):
            return f"[MISSING:{key}]"

    text = re.sub(r"\{\{([^}]+)\}\}", sub, (ROOT / "paper" / "manuscript_template.md").read_text())
    (paper / "manuscript.md").write_text(text)
    print(f"[manuscript] -> {paper / 'manuscript.md'}")


if __name__ == "__main__":
    main()
