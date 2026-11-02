"""Score the four submission files on fresh simulated elections under each
"truth" and rival field. Writes output/final_eval.csv."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import strategies as st
from robustness import truth_variants
from simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["chalk", "ev_credible", "recommended", "aggressive"]


def main():
    races = pd.read_csv(ROOT / "output" / "model_probs.csv")
    Ll, Lr = st.points(races)
    picks = {k: (pd.read_csv(ROOT / "output" / f"detail_{k}.csv").predicted_winner_party.values
                 == races.left.values).astype(int) for k in KEYS}
    rows = []
    for tname, (tr, shift) in truth_variants(races).items():
        W, _ = simulate(tr, 20000, seed=123, national_shift=shift)
        fms = {}
        for fname, mix in st.FIELDS.items():
            P, _ = st.make_pool(races, Ll, Lr, mix, seed=hash(fname) % 1000 + 9)
            ps = st.scores(W, P, Ll, Lr)
            for j in (10, 30, 100):
                fms[f"{fname}/{j}"] = st.field_max(ps, j, seed=j + 1)
        for k, x in picks.items():
            s = st.scores(W, x, Ll, Lr)
            row = {"truth": tname, "strategy": k, "mean": round(float(s.mean()), 1)}
            row.update({f: round(st.p_win(s, v), 3) for f, v in fms.items()})
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "output" / "final_eval.csv", index=False)
    pd.set_option("display.width", 250)
    print(df[["truth", "strategy", "mean", "naive/30", "mixed/30", "savvy/30", "mixed/10", "mixed/100"]].to_string(index=False))


if __name__ == "__main__":
    main()
