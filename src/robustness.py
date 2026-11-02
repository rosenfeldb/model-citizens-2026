"""Stress-test strategies when the world differs from our model.

Picks are built from OUR probabilities, then scored in elections simulated
from several "truths":
  ours      - our blended model (market + ratings + polls)
  market    - Kalshi taken at face value (no de-bias, no ratings/polls)
  longshot  - Kalshi with a strong favorite-longshot bias (lambda = 1.3)
  D+2 / R+2 - our model with a 2-point national shift each way
"Credible" strategies may only pick a candidate our model gives at least
5% (or 10%), which keeps the entry from looking like a one-party rule.
Writes output/robustness.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

sys.path.insert(0, str(Path(__file__).parent))
import strategies as st
from simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
N = 20000
J = 30


def truth_variants(races):
    p = races.p_mkt.values.clip(1e-4, 1 - 1e-4)
    out = {"ours": (races, 0.0)}
    out["market"] = (races.assign(q=np.where(races.fixed, races.q, p)), 0.0)
    out["longshot"] = (races.assign(q=np.where(races.fixed, races.q, expit(1.3 * logit(p)))), 0.0)
    out["D+2"] = (races, 2.0)
    out["R+2"] = (races, -2.0)
    return out


def credible_lock(q, floor):
    """Races where the underdog is below the floor: keep the favorite."""
    return np.minimum(q, 1 - q) < floor


def main():
    races = pd.read_csv(ROOT / "output" / "model_probs.csv")
    Ll, Lr = st.points(races)
    q = races.q.values
    fav = (q > 0.5).astype(int)

    # ---- build strategies (optimized ones trained on our model, seed 0)
    W_tr, _ = simulate(races, N, seed=0)
    pool, _ = st.make_pool(races, Ll, Lr, st.FIELDS["mixed"], seed=11)
    fm_tr = st.field_max(st.scores(W_tr, pool, Ll, Lr), J, seed=3)
    strat = {f.__name__: f(q, Ll, Lr) for f in st.baseline_strategies()}
    for floor in (0.05, 0.10):
        lock = credible_lock(q, floor)
        x_ev = st.ev_max(q, Ll, Lr)
        x_ev[lock] = fav[lock]
        strat[f"EV-max credible{int(floor*100)}"] = x_ev
        strat[f"optimized credible{int(floor*100)}"] = st.optimize(x_ev, W_tr, Ll, Lr, fm_tr, locked=lock)
    strat["optimized unconstrained"] = st.optimize(strat["ev_max"], W_tr, Ll, Lr, fm_tr)
    for k, x in strat.items():
        np.save(ROOT / "output" / f"picks_{k.replace(' ', '_').replace('/', '-')}.npy", x)

    # ---- evaluate on fresh elections under each truth and field
    rows = []
    for tname, (tr, shift) in truth_variants(races).items():
        W, _ = simulate(tr, N, seed=99, national_shift=shift)
        fms = {}
        for fname, mix in st.FIELDS.items():
            P, _ = st.make_pool(races, Ll, Lr, mix, seed=hash(fname) % 1000 + 5)
            ps = st.scores(W, P, Ll, Lr)
            for j in (10, 30, 100):
                fms[f"{fname}/{j}"] = st.field_max(ps, j, seed=j)
        for k, x in strat.items():
            s = st.scores(W, x, Ll, Lr)
            row = {"truth": tname, "strategy": k, "underdogs": int((x != fav).sum()),
                   "R_picks": int(((x == 0) & (races.right == "R")).sum()), "mean": s.mean(), "sd": s.std()}
            row.update({f"P(win) {f}": st.p_win(s, v) for f, v in fms.items()})
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "output" / "robustness.csv", index=False)
    cols = ["truth", "strategy", "underdogs", "R_picks", "mean", "P(win) naive/30", "P(win) mixed/30",
            "P(win) savvy/30", "P(win) mixed/10", "P(win) mixed/100"]
    pd.set_option("display.width", 250)
    print(df[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
