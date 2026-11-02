"""Turn raw Kalshi quotes into one row per race.

For each candidate we estimate the price the organizers will score against:
  * the bid/ask midpoint when the spread is tight (<= 6 cents),
  * else the last trade, clipped into [bid, ask] when both exist.
Scoring floors every probability at 1%, so points = -log2(max(price, 0.01)).
We also store probabilities normalized to sum to 1 for modeling.

Races with no Kalshi market are same-party top-two contests (California),
so the winning party is certain.
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOOR = 0.01
SAME_PARTY = {  # race_id -> party guaranteed to win (no Kalshi market exists)
    "CA-04": "D", "CA-07": "D", "CA-11": "D", "CA-12": "D", "CA-14": "D",
    "CA-29": "D", "CA-34": "D", "CA-37": "D", "CA-40": "R",
}


def score_price(r):
    bid, ask, last = r.bid, r.ask, r.last
    if pd.notna(bid) and pd.notna(ask) and ask - bid <= 0.06 and ask > 0:
        return (bid + ask) / 2
    if pd.notna(last):
        if pd.notna(bid) and pd.notna(ask) and ask > 0:
            return float(np.clip(last, bid, ask))
        return last
    return np.nanmean([bid, ask])


def points(p):
    return -np.log2(np.maximum(p, FLOOR))


def build():
    k = pd.read_csv(ROOT / "data" / "kalshi_prices.csv")
    k["price"] = k.apply(score_price, axis=1)
    k["prob"] = k.price / k.groupby("race_id").price.transform("sum")
    k["pts"] = points(k.price)
    tmpl = pd.read_csv(ROOT / "data" / "template.csv")[["race_id", "chamber"]]
    rows = []
    for rid, chamber in tmpl.itertuples(index=False):
        g = k[k.race_id == rid]
        row = {"race_id": rid, "chamber": chamber, "has_market": len(g) > 0}
        if len(g) == 0:
            row.update(fav_party=SAME_PARTY.get(rid, "D"), p_dem=float(SAME_PARTY.get(rid) == "D"))
            rows.append(row)
            continue
        for _, m in g.iterrows():
            tag = m.party if m.party in ("D", "R") else "I"
            # keep the strongest independent if several
            if tag == "I" and f"price_I" in row and row["price_I"] >= m.price:
                continue
            row.update({f"cand_{tag}": m.candidate, f"price_{tag}": m.price,
                        f"prob_{tag}": m.prob, f"pts_{tag}": m.pts, f"vol_{tag}": m.volume})
        probs = {t: row.get(f"prob_{t}", 0) for t in "DRI"}
        row["fav_party"] = max(probs, key=probs.get)
        row["p_dem"] = probs["D"]
        row["p_fav"] = probs[row["fav_party"]]
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "market.csv", index=False)
    return df


if __name__ == "__main__":
    df = build()
    m = df[df.has_market]
    bins = pd.cut(m.p_fav, [0, .6, .75, .9, .95, .98, 1.0])
    print(m.groupby([bins, "chamber"], observed=True).size().unstack(fill_value=0))
    print("expected D House seats (sum of p_dem):", round(df[df.chamber == "House"].p_dem.sum(), 1))
    print("expected D Senate seats up (sum of p_dem):", round(df[df.chamber == "Senate"].p_dem.sum(), 1))
