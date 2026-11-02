"""Sensitivity of P(win) to the credibility floor, the national-swing size,
and a field that already contains one-party wave bettors.
Writes output/sensitivity.csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import simulate as sm
import strategies as st
from robustness import credible_lock

ROOT = Path(__file__).resolve().parents[1]
N, J = 20000, 30
FIELDS = dict(st.FIELDS)
FIELDS["contrarian"] = {"chalk": 0.40, "upset": 0.20, "ev": 0.20, "under": 0.05, "wave_d": 0.10, "wave_r": 0.05}


def pool_with_waves(races, Ll, Lr, mix, seed):
    base = {k: v for k, v in mix.items() if not k.startswith("wave")}
    tot = sum(base.values())
    m = 800
    n_wave = {k: int(round(m * v)) for k, v in mix.items() if k.startswith("wave")}
    X, _ = st.make_pool(races, Ll, Lr, {k: v / tot for k, v in base.items()}, m=m - sum(n_wave.values()), seed=seed)
    rng = np.random.default_rng(seed + 1)
    q = races.p_mkt.values
    extra = []
    for k, n in n_wave.items():
        for _ in range(n):
            tau = rng.uniform(0.03, 0.2)
            extra.append((q >= tau) if k == "wave_d" else ((1 - q) < tau))
    if extra:
        X = np.hstack([X, np.array(extra, dtype=np.int8).T])
    return X


def main():
    races = pd.read_csv(ROOT / "output" / "model_probs.csv")
    Ll, Lr = st.points(races)
    q = races.q.values
    fav = (q > 0.5).astype(int)
    rows = []
    for sig_n in (2.0, 3.0, 4.0):
        sigma = dict(sm.SIGMA, national=sig_n)
        W_tr, _ = sm.simulate(races, N, seed=0, sigma=sigma)
        W_te, _ = sm.simulate(races, N, seed=99, sigma=sigma)
        for fname, mix in FIELDS.items():
            P = pool_with_waves(races, Ll, Lr, mix, seed=21)
            f_tr = st.field_max(st.scores(W_tr, P, Ll, Lr), J, seed=1)
            f_te = st.field_max(st.scores(W_te, P, Ll, Lr), J, seed=2)
            for floor in (0.0, 0.02, 0.03, 0.05):
                lock = credible_lock(q, floor) if floor else None
                x0 = st.ev_max(q, Ll, Lr)
                if lock is not None:
                    x0[lock] = fav[lock]
                x = st.optimize(x0, W_tr, Ll, Lr, f_tr, locked=lock)
                s = st.scores(W_te, x, Ll, Lr)
                rows.append({"sigma_national": sig_n, "field": fname, "floor": floor,
                             "underdogs": int((x != fav).sum()),
                             "R_underdogs": int(((x != fav) & (x == 0)).sum()),
                             "D_or_I_underdogs": int(((x != fav) & (x == 1)).sum()),
                             "P(win)": st.p_win(s, f_te), "mean": float(s.mean())})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "output" / "sensitivity.csv", index=False)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
