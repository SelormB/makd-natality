#!/usr/bin/env python3
"""Figures for the manuscript, built only from paper/tables/*.csv and data/processed/state_rates.csv.

Fig 1  State unknown rates by item, deployment year (the missingness the students face)
Fig 2  PPV and sensitivity at the 10% alert rate, gap to the full-information teacher,
       against each state's mean unknown rate (small multiples: outcome x mechanism)
Fig 3  Calibration (ICI) across states by model
Fig 4  Subgroup PPV at the alert rate under the national state mixture

Palette validated with the dataviz validator (light surface); two slots sit below 3:1 contrast,
so every series also carries its own marker shape and a legend, and every figure has a CSV table.
Pass --final to remove the DRAFT stamp (only after the verification gate).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from makd.common import load_config  # noqa: E402

SURFACE, INK, INK2, GRID, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0", "#9b9a95"
SERIES = {  # fixed order; color follows the model, never its rank
    "KD_state":           ("Distilled student (state)", "#2a78d6", "o"),
    "B3_state":           ("No distillation (state)",   "#eb6834", "s"),
    "B2_teacher_iterimp": ("Teacher + iterative imp.",  "#1baf7a", "^"),
    "B1_teacher_meanimp": ("Teacher + mean imp.",       "#eda100", "D"),
}
POOLED = {
    "T_oracle":           ("Teacher, full data",        GRAY,      "x"),
    "KD_pooled":          ("Distilled student (pooled)", "#2a78d6", "o"),
    "B3_pooled":          ("No distillation (pooled)",  "#eb6834", "s"),
    "B4_logistic_pooled": ("Logistic + indicators",     "#1baf7a", "^"),
}


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
        "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10, "axes.titlecolor": INK,
        "legend.frameon": False, "lines.linewidth": 2})


PILOT = False   # set in main() from the config's train years


def stamp(fig, final, synthetic):
    if PILOT and not synthetic:
        fig.text(0.005, 0.005, "PILOT: train 2023, test 2024; reduced samples", ha="left",
                 va="bottom", fontsize=7, color="#52514e")
    if synthetic:
        fig.text(0.5, 0.5, "SYNTHETIC TEST DATA", ha="center", va="center", fontsize=28,
                 color="#e34948", alpha=0.18, rotation=25)
    if not final:
        fig.text(0.995, 0.005, "DRAFT", ha="right", va="bottom", fontsize=8, color="#e34948")


def fig1(rates, year, out, final, syn):
    r = rates[rates["year"] == year]
    items = r.groupby("item")["rate"].median().sort_values().index.tolist()
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    rng = np.random.default_rng(0)
    for i, it in enumerate(items):
        v = 100 * r.loc[r["item"] == it, "rate"].to_numpy()
        ax.scatter(v, i + rng.uniform(-0.18, 0.18, len(v)), s=14, color="#2a78d6", alpha=0.75,
                   edgecolor=SURFACE, linewidth=0.5)
        ax.plot([np.median(v)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
    names = {"precare": "Month prenatal care began", "bmi": "Pre-pregnancy BMI", "wic": "WIC",
             "cig": "Smoking", "meduc": "Mother's education", "pay": "Payer"}
    ax.set_yticks(range(len(items)), [names.get(i, i) for i in items])
    ax.set_xscale("symlog", linthresh=1)
    ticks = [0, 0.5, 1, 2, 5, 10, 20, 50, 100]
    ax.set_xlim(0, 100)
    ax.set_xticks(ticks, [f"{t:g}" for t in ticks])
    ax.minorticks_off()
    ax.set_xlabel(f"Births with item unknown or not stated, % (each dot a state, {year}; bar = median)")
    ax.set_title("Item missingness varies widely across states", loc="left")
    stamp(fig, final, syn)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


def fig2(M, out, final, syn):
    raw = M[M["calibration"] == "raw"]
    outs, mechs = sorted(raw["outcome"].unique()), sorted(raw["mechanism"].unique())
    fig, axes = plt.subplots(2, len(outs) * len(mechs), figsize=(10, 5.2), sharex=True)
    axes = np.atleast_2d(axes)
    for j, (o, mch) in enumerate([(o, m) for o in outs for m in mechs]):
        g = raw[(raw["outcome"] == o) & (raw["mechanism"] == mch)]
        T = g[g["model"] == "T_oracle"].set_index("state")
        for row, metric, lab in [(0, "ppv_alert", "PPV"), (1, "sens_alert", "Sensitivity")]:
            ax = axes[row, j]
            ax.axhline(0, color=INK2, lw=1)
            for m, (name, col, mk) in SERIES.items():
                x = g[g["model"] == m].set_index("state")
                if x.empty:
                    continue
                gap = 100 * (x[metric] - T[metric].reindex(x.index))
                ax.scatter(100 * x["state_mean_unknown"], gap, s=16, color=col, marker=mk,
                           edgecolor=SURFACE, linewidth=0.5, label=name)
            if row == 0:
                ax.set_title(f"{o}, {mch}", loc="left")
            if j == 0:
                ax.set_ylabel(f"{lab} at 10% alert rate\nminus teacher (points)")
            if row == 1:
                ax.set_xlabel("State mean unknown rate, %")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.01))
    stamp(fig, final, syn)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out, dpi=300)
    plt.close(fig)


def fig3(M, out, final, syn):
    raw = M[M["calibration"] == "raw"]
    combos = sorted(raw[["outcome", "mechanism"]].drop_duplicates().itertuples(index=False))
    models = list(SERIES) + ["T_oracle"]
    fig, axes = plt.subplots(1, len(combos), figsize=(10, 3.2), sharey=True)
    rng = np.random.default_rng(1)
    for ax, (o, mch) in zip(np.atleast_1d(axes), combos):
        g = raw[(raw["outcome"] == o) & (raw["mechanism"] == mch)]
        for i, m in enumerate(models):
            name, col, mk = SERIES.get(m, ("Teacher, full data", GRAY, "x"))
            v = 100 * g.loc[g["model"] == m, "ici"].to_numpy()
            ax.scatter(v, i + rng.uniform(-0.15, 0.15, len(v)), s=10, color=col, marker=mk, alpha=0.8)
            if len(v):
                ax.plot([np.median(v)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
        ax.set_yticks(range(len(models)), [SERIES.get(m, ("Teacher, full data",))[0] for m in models])
        ax.set_title(f"{o}, {mch}", loc="left")
        ax.set_xlabel("ICI, percentage points")
    stamp(fig, final, syn)
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)


# Display labels. VERIFY: MRACEHISP and PAY_REC code meanings against the User Guide.
LABELS = {
    "mracehisp": {1: "NH White", 2: "NH Black", 3: "NH AIAN", 4: "NH Asian", 5: "NH NHOPI",
                  6: "NH multiracial", 7: "Hispanic"},
    "payer_obs": {1: "Medicaid", 2: "Private", 3: "Self-pay", 4: "Other payer"},
    "foreign_born": {0: "U.S.-born", 1: "Foreign-born"},
}
GROUP_NAME = {"mracehisp": "Race/ethnicity", "mage_band": "Age", "payer_obs": "Payer",
              "foreign_born": "Nativity"}


def _label(sg, lv):
    try:
        lv_key = int(float(lv))
    except ValueError:
        lv_key = lv
    return f"{GROUP_NAME.get(sg, sg)}: {LABELS.get(sg, {}).get(lv_key, lv)}"


def fig4(S, out, final, syn):
    S = S[S["mechanism"] == "MAR"] if "MAR" in set(S["mechanism"]) else S
    outs = sorted(S["outcome"].unique())
    fig, axes = plt.subplots(1, len(outs), figsize=(9, 4.2), sharey=True)
    for ax, o in zip(np.atleast_1d(axes), outs):
        g = S[S["outcome"] == o]
        levels = sorted(set(g[["subgroup", "level"]].itertuples(index=False, name=None)),
                        key=lambda t: (list(GROUP_NAME).index(t[0]) if t[0] in GROUP_NAME else 9, str(t[1])),
                        reverse=True)
        for k, (m, (name, col, mk)) in enumerate(POOLED.items()):
            for i, (sg, lv) in enumerate(levels):
                v = g[(g["model"] == m) & (g["subgroup"] == sg) & (g["level"] == lv)]["ppv_alert"]
                if len(v):
                    ax.scatter(100 * v.iloc[0], i + (k - 1.5) * 0.15, color=col, marker=mk, s=18,
                               label=name if i == 0 else None)
        ax.set_yticks(range(len(levels)), [_label(sg, lv) for sg, lv in levels], fontsize=7)
        ax.set_title("Low birthweight" if o == "LBW" else "Preterm birth" if o == "PTB" else o, loc="left")
        ax.set_xlabel("PPV, %")
    fig.suptitle("PPV at the 10% alert rate by subgroup, births-weighted state mixture (MAR masks)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    h, l = np.atleast_1d(axes)[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4)
    stamp(fig, final, syn)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(out, dpi=300)
    plt.close(fig)


def main():
    cfg = load_config()
    final = cfg["final"] or "--final" in sys.argv
    syn = bool(__import__("os").environ.get("MAKD_SMOKE"))
    global PILOT
    PILOT = set(cfg["years"]["train"]) & set(cfg["years"]["tune"]) != set()
    style()
    tabs, figs = cfg["paths"]["paper"] / "tables", cfg["paths"]["paper"] / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    rates = pd.read_csv(cfg["paths"]["processed"] / "state_rates.csv")
    M = pd.read_csv(tabs / "metrics_by_state.csv")
    S = pd.read_csv(tabs / "subgroups.csv")
    fig1(rates, cfg["years"]["test"][0], figs / "fig1_state_missingness.png", final, syn)
    fig2(M, figs / "fig2_gap_to_teacher.png", final, syn)
    fig3(M, figs / "fig3_calibration_ici.png", final, syn)
    fig4(S, figs / "fig4_subgroups_ppv.png", final, syn)
    print(f"[figures] -> {figs}")


if __name__ == "__main__":
    main()
