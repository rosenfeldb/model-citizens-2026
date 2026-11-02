"""Two-panel figure for the README: output/strategy_chart.png
Left:  how often each strategy's score lands where (20,000 simulated elections).
Right: chance to beat 30 rivals when Democrats beat (or miss) their polls by X points.
Also writes output/pwin_by_polling_error.csv.
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
          ("recommended", "Recommended (GOP beats polls)", "#1baf7a"), ("aggressive", "Aggressive", "#eda100"),
          ("dem_wave", "Dem wave (Dems beat polls)", "#e87ba4")]
SHIFTS = np.arange(-4, 7)


def main():
    races = pd.read_csv(ROOT / "output" / "model_probs.csv")
    Ll, Lr = st.points(races)
    pool, _ = st.make_pool(races, Ll, Lr, st.FIELDS["mixed"], seed=11)
    picks = {}
    for key, _, _ in SERIES:
        d = pd.read_csv(ROOT / "output" / f"detail_{key}.csv")
        picks[key] = (d.predicted_winner_party.values == races.left.values).astype(int)

    W, _ = simulate(races, 20000, seed=99)
    fmax = st.field_max(st.scores(W, pool, Ll, Lr), 30, seed=3)
    by_shift = {k: [] for k in picks}
    for shift in SHIFTS:
        Ws, _ = simulate(races, 20000, seed=7, national_shift=float(shift))
        fs = st.field_max(st.scores(Ws, pool, Ll, Lr), 30, seed=5)
        for k, x in picks.items():
            by_shift[k].append(st.p_win(st.scores(Ws, x, Ll, Lr), fs))
    pd.DataFrame({"dem_beat_polls_by": SHIFTS, **by_shift}).round(3).to_csv(
        ROOT / "output" / "pwin_by_polling_error.csv", index=False)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8), facecolor=SURFACE)
    bins = np.arange(0, 181, 4)
    for key, label, color in SERIES:
        s = st.scores(W, picks[key], Ll, Lr)
        h, _ = np.histogram(s, bins=bins, density=True)
        a.step(bins[:-1], h, where="post", color=color, lw=2, label=f"{label} - {st.p_win(s, fmax):.0%}")
        b.plot(SHIFTS, np.array(by_shift[key]) * 100, color=color, lw=2, marker="o", ms=4, label=label)
    hf, _ = np.histogram(fmax, bins=bins, density=True)
    a.step(bins[:-1], hf, where="post", color=INK2, lw=1.5, ls="--", label="Best of 30 rivals")
    a.legend(frameon=False, fontsize=8.5, loc="upper right", title="P(win) vs 30 simulated rivals", title_fontsize=9)

    a.set(title="Score distribution, 20,000 simulated elections", xlabel="Total points", ylabel="Share of simulations")
    b.set(title="Chance to finish first vs. polling error", ylabel="P(win) vs 30 rivals (%)",
          xlabel="Democrats beat their polls by (points; negative = Republicans do)")
    for ax in (a, b):
        ax.set_facecolor(SURFACE)
        ax.grid(color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.title.set_color(INK)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    a.set_yticklabels([])
    b.axvline(0, color=INK2, lw=0.8)
    b.set_ylim(bottom=0)
    b.legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(ROOT / "output" / "strategy_chart.png", dpi=160, facecolor=SURFACE)
    print("wrote output/strategy_chart.png and output/pwin_by_polling_error.csv")


if __name__ == "__main__":
    main()
