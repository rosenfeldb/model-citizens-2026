"""Build submission CSVs for each strategy.

  recommended  P(win)-optimized against a simulated field of 30 rivals, but
               only picks candidates our model gives >= 3% (FLOOR)
  aggressive   the same optimizer with no floor (highest simulated P(win),
               but the picks look like "always pick the Republican")
  ev_credible  maximize expected points; only candidates our model gives >= 5%
  chalk        pick our model's favorite everywhere

Writes output/picks_<name>.csv (template format) and output/detail_<name>.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import strategies as st
from robustness import credible_lock
from simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
FLOOR = 0.03
N, J = 20000, 30

# Same-party contests have no Kalshi market; name the incumbent or frontrunner.
SAME_PARTY_NAMES = {
    "CA-04": "Mike Thompson", "CA-07": "Doris Matsui", "CA-11": "Scott Wiener", "CA-12": "Lateefah Simon",
    "CA-14": "Aisha Wahab", "CA-29": "Luz Rivas", "CA-34": "Jimmy Gomez", "CA-37": "Sydney Kamlager-Dove",
    "CA-40": "Young Kim",
}


def research_names():
    names = {}
    for f in ("house_ratings.csv", "senate_ratings.csv"):
        p = ROOT / "data" / "research" / f
        if p.exists():
            for _, r in pd.read_csv(p, dtype=str).iterrows():
                names[r.race_id] = {"D": r.get("dem_candidate"), "R": r.get("rep_candidate")}
    return names


def candidate(race, side, names):
    tag = race[side]
    name = race[f"cand_{side}"]
    if not isinstance(name, str) or not name or "party" in name.lower():
        alt = names.get(race.race_id, {}).get(tag)
        name = alt if isinstance(alt, str) and alt else name
    return name


def build_all():
    races = pd.read_csv(ROOT / "output" / "model_probs.csv")
    Ll, Lr = st.points(races)
    q = races.q.values
    fav = (q > 0.5).astype(int)
    W, _ = simulate(races, N, seed=0)
    pool, _ = st.make_pool(races, Ll, Lr, st.FIELDS["mixed"], seed=11)
    fmax = st.field_max(st.scores(W, pool, Ll, Lr), J, seed=3)

    lock3, lock5 = credible_lock(q, FLOOR), credible_lock(q, 0.05)
    ev = st.ev_max(q, Ll, Lr)
    ev3, ev5 = ev.copy(), ev.copy()
    ev3[lock3], ev5[lock5] = fav[lock3], fav[lock5]
    picks = {
        "recommended": st.optimize(ev3, W, Ll, Lr, fmax, locked=lock3),
        "aggressive": st.optimize(ev, W, Ll, Lr, fmax),
        "ev_credible": ev5,
        "chalk": fav,
    }

    names = research_names()
    tmpl = pd.read_csv(ROOT / "data" / "template.csv")
    for key, x in picks.items():
        out, det = [], []
        for i, r in races.iterrows():
            side = "left" if x[i] == 1 else "right"
            party = r[side]
            name = SAME_PARTY_NAMES.get(r.race_id) if r.fixed else candidate(r, side, names)
            qp = q[i] if side == "left" else 1 - q[i]
            price = r[f"price_{side}"]
            out.append({"race_id": r.race_id, "chamber": r.chamber, "predicted_winner_party": party,
                        "candidate_name": name, "win_probability": round(float(qp), 4)})
            det.append({**out[-1], "kalshi_price": price, "points_if_right": 0.0 if r.fixed else
                        round(float(-np.log2(max(price, 0.01))), 3), "underdog_pick": bool(x[i] != fav[i]),
                        "model_q_left": round(float(q[i]), 4), "market_p_left": round(float(r.p_mkt), 4)})
        df = pd.DataFrame(out)
        assert list(df.race_id) == list(tmpl.race_id)
        df.to_csv(ROOT / "output" / f"picks_{key}.csv", index=False)
        pd.DataFrame(det).to_csv(ROOT / "output" / f"detail_{key}.csv", index=False)
        s = st.scores(W, x, Ll, Lr)
        print(f"{key:12s} underdog picks={int((x != fav).sum()):3d}  parties={df.predicted_winner_party.value_counts().to_dict()}  "
              f"mean={s.mean():.1f}  P(win vs 30, train sims)={st.p_win(s, fmax):.3f}")
    return picks


if __name__ == "__main__":
    build_all()
