"""Score every strategy against simulated elections and simulated rival fields.

Writes output/strategy_table.csv and output/optimized_picks_<field>.npy.
Train and test use different random elections, so optimized picks are judged
on elections they never saw.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import strategies as st
from simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
N_SIMS = 20000
RIVALS = (10, 30, 100)


def summarize(name, x, W, Ll, Lr, fmaxes):
    s = st.scores(W, x, Ll, Lr)
    row = {"strategy": name, "underdog_picks": None, "mean": s.mean(), "sd": s.std(),
           "p10": np.percentile(s, 10), "p50": np.median(s), "p90": np.percentile(s, 90)}
    for key, f in fmaxes.items():
        row[f"P(win) {key}"] = st.p_win(s, f)
    return row


def main(q_file=ROOT / "output" / "model_probs.csv", tag=""):
    races = pd.read_csv(q_file)
    Ll, Lr = st.points(races)
    q = races.q.values
    W_tr, _ = simulate(races, N_SIMS, seed=0)
    W_te, _ = simulate(races, N_SIMS, seed=99)

    pools, fm_tr, fm_te = {}, {}, {}
    for fname, mix in st.FIELDS.items():
        X, _ = st.make_pool(races, Ll, Lr, mix, seed=hash(fname) % 1000)
        pools[fname] = X
        ps_tr, ps_te = st.scores(W_tr, X, Ll, Lr), st.scores(W_te, X, Ll, Lr)
        for J in RIVALS:
            fm_tr[f"{fname}/{J}"] = st.field_max(ps_tr, J, seed=J)
            fm_te[f"{fname}/{J}"] = st.field_max(ps_te, J, seed=J + 7)

    fav = (q > 0.5).astype(int)
    rows, picks = [], {}
    for f in st.baseline_strategies():
        x = f(q, Ll, Lr)
        picks[f.__name__] = x
        r = summarize(f.__name__, x, W_te, Ll, Lr, fm_te)
        r["underdog_picks"] = int((x != fav).sum())
        rows.append(r)

    # Optimize against each field (30 rivals), from the best baseline for that field.
    for fname in st.FIELDS:
        key = f"{fname}/30"
        base = max(picks, key=lambda k: st.p_win(st.scores(W_tr, picks[k], Ll, Lr), fm_tr[key]))
        x = st.optimize(picks[base], W_tr, Ll, Lr, fm_tr[key])
        name = f"optimized vs {fname} field (from {base})"
        picks[name] = x
        np.save(ROOT / "output" / f"optimized_picks_{fname}{tag}.npy", x)
        r = summarize(name, x, W_te, Ll, Lr, fm_te)
        r["underdog_picks"] = int((x != fav).sum())
        rows.append(r)

    table = pd.DataFrame(rows)
    table.to_csv(ROOT / "output" / f"strategy_table{tag}.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(table.round(3).to_string(index=False))
    return races, picks, table


if __name__ == "__main__":
    main()
