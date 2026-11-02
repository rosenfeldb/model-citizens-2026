"""Two-panel figure for the README: output/strategy_chart.png
Left:  how often each strategy's score lands where (20,000 simulated elections).
Right: average score vs the simulated national polling error.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import strategies as st
from simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
SERIES = [("chalk", "Chalk (favorites)", "#2a78d6"), ("ev_credible", "EV-max", "#eb6834"),
          ("recommended", "Recommended", "#1baf7a"), ("aggressive", "Aggressive", "#eda100")]


def main():
    races = pd.read_csv(ROOT / "output" / "model_probs.csv")
    Ll, Lr = st.points(races)
    W, N = simulate(races, 20000, seed=99)
    pool, _ = st.make_pool(races, Ll, Lr, st.FIELDS["mixed"], seed=11)
    fmax = st.field_max(st.scores(W, pool, Ll, Lr), 30, seed=3)
    picks = {}
    for key, _, _ in SERIES:
        d = pd.read_csv(ROOT / "output" / f"detail_{key}.csv")
        picks[key] = (d.predicted_winner_party.values == races.left.values).astype(int)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), facecolor=SURFACE)
    bins = np.arange(0, 181, 4)
    swing_bins = np.arange(-8, 8.1, 1.0)
    mids = (swing_bins[:-1] + swing_bins[1:]) / 2
    # national swing is in Democratic-margin points; plot as R-ward error to the right
    rward = -N
    for key, label, color in SERIES:
        s = st.scores(W, picks[key], Ll, Lr)
        h, _ = np.histogram(s, bins=bins, density=True)
        a.step(bins[:-1], h, where="post", color=color, lw=2, label=f"{label} - P(win) {st.p_win(s, fmax):.0%}")
        means = [s[(rward >= lo) & (rward < hi)].mean() for lo, hi in zip(swing_bins[:-1], swing_bins[1:])]
        b.plot(mids, means, color=color, lw=2, label=label)
    hf, _ = np.histogram(fmax, bins=bins, density=True)
    a.step(bins[:-1], hf, where="post", color=INK2, lw=1.5, ls="--", label="Best of 30 rivals")
    a.legend(frameon=False, fontsize=9, loc="upper right", title="P(win) vs 30 simulated rivals", title_fontsize=9)
    fm = [fmax[(rward >= lo) & (rward < hi)].mean() for lo, hi in zip(swing_bins[:-1], swing_bins[1:])]
    b.plot(mids, fm, color=INK2, lw=1.5, ls="--", label="Best of 30 rivals")

    a.set(title="Score distribution, 20,000 simulated elections", xlabel="Total points", ylabel="Share of simulations")
    b.set(title="Average score vs. national polling error", xlabel="Polling error (points toward Republicans)",
          ylabel="Total points")
    for ax in (a, b):
        ax.set_facecolor(SURFACE)
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.title.set_color(INK)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    a.set_yticklabels([])
    b.axvline(0, color=INK2, lw=0.8)
    b.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(ROOT / "output" / "strategy_chart.png", dpi=160, facecolor=SURFACE)
    print("wrote output/strategy_chart.png")


if __name__ == "__main__":
    main()
