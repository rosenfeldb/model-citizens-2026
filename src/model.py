"""Our probability model: q = P(left-side candidate wins) for every race.

Each race is a two-sided contest. "Left" is the Democrat, or the independent
running in the Democrat's place (Osborn in NE, Bodnar in MT, ...). "Right" is
the Republican, or an independent running against a Democrat (Kiley, CA-06).

q blends three signals in log-odds space (forecast combination):
  1. Kalshi price, normalized, then de-biased for the favorite-longshot bias:
     logit(q_mkt) = LAMBDA * logit(p).  LAMBDA > 1 means longshots are overpriced.
  2. Expert ratings (Cook / Inside Elections / Sabato), mapped to historical
     hit rates of each rating category.
  3. Senate polling averages, mapped through a normal error with sd 6 points.
Missing signals drop out and the remaining weights renormalize.
"""
import re

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.special import expit, logit
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
LAMBDA = 1.10          # longshot de-bias on the market (1.0 = take Kalshi at face value)
WEIGHTS = {"market": 0.60, "ratings": 0.25, "polls": 0.15}
POLL_SD = 6.0          # sd of final-week Senate polling-average error, in margin points
CLIP = (0.001, 0.999)

# Historical share of races won by the party a rating favors (Cook-style
# categories, House and Senate, ~1998-2024; rounded).
RATING_P = {"safe": 0.995, "solid": 0.995, "likely": 0.95, "lean": 0.83, "tilt": 0.65, "toss-up": 0.50, "tossup": 0.50}


def rating_to_pdem(text):
    """'Lean R' -> 0.17, 'Safe D (all raters)' -> 0.995, 'Toss-up' -> 0.5."""
    if not isinstance(text, str) or not text.strip():
        return np.nan
    t = text.strip().lower().replace("toss up", "toss-up")
    if t.startswith("toss"):
        return 0.5
    m = re.match(r"(safe|solid|likely|lean|tilt)\s+(d|r|i)\b", t)
    if not m or m.group(2) == "i":
        return np.nan
    p = RATING_P[m.group(1)]
    return p if m.group(2) == "d" else 1 - p


def all_ratings(row):
    """Every rater's view for one race: the three named columns plus 'Name=Rating;...' pairs."""
    vals = [row.get(c) for c in ("cook", "inside", "sabato")]
    other = row.get("other_rating")
    if isinstance(other, str):
        vals += [part.split("=", 1)[-1] for part in other.split(";")] if "=" in other else [other]
    return [p for p in map(rating_to_pdem, vals) if pd.notna(p)]


def sides(row):
    """Return (left_tag, right_tag) among D/R/I for a race row of market.csv."""
    probs = {t: row.get(f"prob_{t}") for t in "DRI"}
    probs = {t: p for t, p in probs.items() if pd.notna(p)}
    top = sorted(probs, key=probs.get, reverse=True)[:2]
    if "D" in top:
        other = [t for t in top if t != "D"][0]
        return "D", other
    return "I", "R"


def load_ratings():
    out = {}
    for name in ("house_ratings.csv", "senate_ratings.csv"):
        f = ROOT / "data" / "research" / name
        if not f.exists():
            continue
        r = pd.read_csv(f, dtype=str)
        for _, x in r.iterrows():
            ps = all_ratings(x)
            if ps:
                out[str(x["race_id"]).strip()] = float(np.mean(ps))
    return out


def load_polls():
    f = ROOT / "data" / "research" / "senate_polls.csv"
    if not f.exists():
        return {}
    p = pd.read_csv(f)
    p = p.dropna(subset=["margin_dem_minus_rep"])
    # prefer an average row; else mean of listed polls
    out = {}
    for rid, g in p.groupby("race_id"):
        avg = g[g.source.astype(str).str.contains("avg|average|RCP|RealClear|538|FiftyPlusOne|DDHQ|Silver", case=False, regex=True)]
        out[rid] = float((avg if len(avg) else g).margin_dem_minus_rep.astype(float).mean())
    return out


def build(lam=LAMBDA, weights=WEIGHTS):
    m = pd.read_csv(ROOT / "data" / "market.csv")
    ratings, polls = load_ratings(), load_polls()
    rows = []
    for _, r in m.iterrows():
        row = {"race_id": r.race_id, "chamber": r.chamber}
        if not r.has_market:
            fav = r.fav_party
            row.update(left="D", right="R", cand_left="", cand_right="", price_left=float(fav == "D"),
                       price_right=float(fav == "R"), p_mkt=float(fav == "D"), q=float(fav == "D"), fixed=True)
            rows.append(row)
            continue
        L, R = sides(r)
        pl, pr = r[f"prob_{L}"], r[f"prob_{R}"]
        p2 = pl / (pl + pr)
        sig = {"market": lam * logit(np.clip(p2, *CLIP))}
        # Ratings give P(not Republican) and the poll file puts an anti-R
        # independent in the Democratic slot, so both map onto left-vs-right.
        if r.race_id in ratings and pd.notna(ratings[r.race_id]):
            sig["ratings"] = logit(np.clip(ratings[r.race_id], *CLIP))
        if r.race_id in polls and R == "R":
            sig["polls"] = logit(np.clip(norm.cdf(polls[r.race_id] / POLL_SD), *CLIP))
        w = {k: weights[k] for k in sig}
        z = sum(w[k] * sig[k] for k in sig) / sum(w.values())
        row.update(left=L, right=R, cand_left=r.get(f"cand_{L}"), cand_right=r.get(f"cand_{R}"),
                   price_left=r[f"price_{L}"], price_right=r[f"price_{R}"], p_mkt=p2,
                   q=float(expit(z)), fixed=False,
                   p_ratings=ratings.get(r.race_id, np.nan), poll_margin=polls.get(r.race_id, np.nan))
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "output" / "model_probs.csv", index=False)
    return df


if __name__ == "__main__":
    df = build()
    print(f"{len(df)} races; with ratings: {df.p_ratings.notna().sum()}; with polls: {df.poll_margin.notna().sum()}")
    d = df[~df.fixed]
    print("mean |q - p_mkt|:", round((d.q - d.p_mkt).abs().mean(), 4))
    print(d.assign(diff=d.q - d.p_mkt).reindex((d.q - d.p_mkt).abs().sort_values(ascending=False).index)
          [["race_id", "cand_left", "cand_right", "p_mkt", "q", "p_ratings", "poll_margin"]].head(15).to_string())
