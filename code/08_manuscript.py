#!/usr/bin/env python3
"""Fill paper/manuscript_template.md from paper/stats.json and AUTHORS.json.

Every number in the manuscript comes from stats.json; nothing is typed by hand.
Output: paper/manuscript.md. Placeholders that cannot be resolved stay visible as [MISSING:key],
which the publish gate treats as a blocker.
"""
import json
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
    "f3": lambda v: f"{v:.3f}",
    "int": lambda v: f"{int(v):,}",
}


def lookup(d, dotted):
    for k in dotted.split("."):
        d = d[k]
    return d


def results_paragraphs(stats):
    out = []
    for o, od in stats["outcomes"].items():
        for mech, md in od["mechanisms"].items():
            T = md.get("T_oracle", {})
            parts = [f"**{o}, {mech}.** Full-information teacher: median AUROC across states "
                     f"{T['auroc']['median']:.3f}, PPV at 10% alert {100 * T['ppv_alert']['median']:.1f}%."]
            for m, lab in [("KD_state", "state-distilled student"), ("B3_state", "non-distilled state model"),
                           ("B2_teacher_iterimp", "teacher with iterative imputation"),
                           ("B1_teacher_meanimp", "teacher with mean imputation")]:
                if m in md:
                    x = md[m]
                    parts.append(f"{lab.capitalize()}: AUROC {x['auroc']['median']:.3f} "
                                 f"(range {x['auroc']['min']:.3f}–{x['auroc']['max']:.3f}); PPV gap "
                                 f"{signed(100 * x['ppv_alert']['gap_median'])} points; sensitivity gap "
                                 f"{signed(100 * x['sens_alert']['gap_median'])} points; median ICI "
                                 f"{100 * x['ici']['median']:.2f}.")
            c = md.get("_kd_vs_b3_state")
            if c:
                parts.append(f"The distilled student had higher PPV than the non-distilled model in "
                             f"{c['states_kd_higher_ppv_alert']} of {c['n_states']} states and lower ICI "
                             f"in {c['states_kd_lower_ici']}.")
            out.append(" ".join(parts))
    return "\n\n".join(out)


def main():
    cfg = load_config()
    paper = cfg["paths"]["paper"]
    stats = json.loads((paper / "stats.json").read_text())
    authors = json.loads((ROOT / "AUTHORS.json").read_text())["authors"]
    y = cfg["years"]
    ctx = {
        "banner": ("" if cfg["final"] else "> **DRAFT — not for circulation. Numbers below are "
                   + ("from SYNTHETIC test data and are meaningless.**" if stats.get("synthetic")
                      else "from the PILOT run (train 80% of 2023, tune 20% of 2023, test 2024; reduced "
                           "samples). Feasibility only: do not quote. The main design trains on 2016-2022.**"
                      if stats.get("pilot")
                      else "unverified until the author completes docs/VERIFY_CHECKLIST.md.**")),
        "author_block": "\n".join(f"{a['name']}, {a['affiliation']}. ORCID {a['orcid']}. {a['email']}"
                                  for a in authors),
        "years_span": f"{y['train'][0]}–{y['test'][-1]}",
        "train_years": (f"{y['train'][0]}–{y['train'][-1]}" if not stats.get("pilot")
                        else f"{y['train'][0]} ({100 - int(100 * y.get('holdout_frac', 0.2))}% of records)"),
        "tune_year": (str(y["tune"][0]) if not stats.get("pilot")
                      else f"{y['tune'][0]} (held-out {int(100 * y.get('holdout_frac', 0.2))}%)"),
        "test_year": str(y["test"][0]), "K": str(cfg["models"]["crossfit_folds"]),
        "alpha": str(cfg["models"]["kd"]["alpha"]), "tau": str(cfg["models"]["kd"]["tau"]),
        "B": str(cfg["evaluation"]["bootstrap_B"]), "n_states": str(stats["n_states"]),
        "eval_n_test": f"{stats['eval_n_test']:,}",
        "natural_missing_n_test": f"{stats['natural_missing_n_test']:,}",
        "code_doi": "[DOI: Zenodo, after release]",
        "results_paragraphs": results_paragraphs(stats),
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

    text = re.sub(r"\{\{([^}]+)\}\}", sub, (paper / "manuscript_template.md").read_text())
    (paper / "manuscript.md").write_text(text)
    print(f"[manuscript] -> {paper / 'manuscript.md'}")


if __name__ == "__main__":
    main()
