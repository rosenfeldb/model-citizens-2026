"""Rebuild the competition's race list (same rows and order as the official template)."""
import csv
from pathlib import Path

SENATE = ["AK", "AL", "AR", "CO", "DE", "FL", "GA", "IA", "ID", "IL", "KS", "KY", "LA", "MA",
          "ME", "MI", "MN", "MS", "MT", "NC", "NE", "NH", "NJ", "NM", "OH", "OK", "OR", "RI",
          "SC", "SD", "TN", "TX", "VA", "WV", "WY"]
# 2020 apportionment
SEATS = {"AK": 1, "AL": 7, "AR": 4, "AZ": 9, "CA": 52, "CO": 8, "CT": 5, "DE": 1, "FL": 28,
         "GA": 14, "HI": 2, "IA": 4, "ID": 2, "IL": 17, "IN": 9, "KS": 4, "KY": 6, "LA": 6,
         "MA": 9, "MD": 8, "ME": 2, "MI": 13, "MN": 8, "MO": 8, "MS": 4, "MT": 2, "NC": 14,
         "ND": 1, "NE": 3, "NH": 2, "NJ": 12, "NM": 3, "NV": 4, "NY": 26, "OH": 15, "OK": 5,
         "OR": 6, "PA": 17, "RI": 2, "SC": 7, "SD": 1, "TN": 9, "TX": 38, "UT": 4, "VA": 11,
         "VT": 1, "WA": 10, "WI": 8, "WV": 2, "WY": 1}


def races():
    rows = [(f"{s}-SEN", "Senate") for s in SENATE]
    for st in sorted(SEATS):
        n = SEATS[st]
        rows += [(f"{st}-AL", "House")] if n == 1 else [(f"{st}-{d:02d}", "House") for d in range(1, n + 1)]
    return rows


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "template.csv"
    rows = races()
    assert len(rows) == 470, len(rows)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["race_id", "chamber", "predicted_winner_party", "candidate_name", "win_probability"])
        for r in rows:
            w.writerow([*r, "", "", ""])
    print(f"wrote {len(rows)} races to {out}")
