"""Pull Kalshi prices for every race in the template.

Kalshi lists 2026 races under two series families:
  * KXHOUSERACE-{ST}{NN}-26           (most House races)
  * HOUSE{ST}{N}-26 / SENATE{ST}-26   (older series, mostly competitive races)
We fetch every candidate ticker and keep all markets found, so later steps can
pick the series the organizers most likely used.

Output: data/raw/kalshi_<date>.json  and  data/kalshi_prices.csv
"""
import csv
import datetime as dt
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.elections.kalshi.com/trade-api/v2/events/{}?with_nested_markets=true"

# Senate tickers that do not follow SENATE{ST}-26.
SENATE_OVERRIDES = {
    "FL": ["SENATEFLS-26"],          # Florida special (Moody seat)
    "OH": ["SENATEOHS-26"],          # Ohio special (Husted seat)
    "KY": ["SENATELA-26"],           # Kalshi mislabels the Kentucky event ticker
    "LA": ["KXSENATELA-26NOV"],
}


def candidate_tickers(race_id):
    st, part = race_id.split("-")
    if part == "SEN":
        return SENATE_OVERRIDES.get(st, [f"SENATE{st}-26"])
    if part == "AL":
        return [f"KXHOUSERACE-{st}AL-26", f"HOUSE{st}AL-26"]
    n = int(part)
    # Newly drawn districts have one-off series such as KXHOUSETX9 or KXHOUSEUT01.
    return [f"KXHOUSERACE-{st}{n:02d}-26", f"HOUSE{st}{n}-26",
            f"KXHOUSE{st}{n}-26", f"KXHOUSE{st}{n:02d}-26"] if n < 10 else \
           [f"KXHOUSERACE-{st}{n:02d}-26", f"HOUSE{st}{n}-26", f"KXHOUSE{st}{n}-26"]


def get_event(ticker):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(API.format(ticker), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


def party_of(m):
    suffix = m["ticker"].rsplit("-", 1)[-1].upper()
    suffix = {"DEM": "D", "GOP": "R", "REP": "R", "IND": "I"}.get(suffix, suffix)
    if suffix in ("D", "R", "I", "L", "G"):
        return suffix
    sub = (m.get("subtitle") or "").lower()
    for word, p in (("democrat", "D"), ("republican", "R"), ("independent", "I")):
        if word in sub:
            return p
    return suffix


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    races = [r["race_id"] for r in csv.DictReader(open(ROOT / "data" / "template.csv"))]
    jobs = [(rid, t) for rid in races for t in candidate_tickers(rid)]
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(lambda j: (j[0], j[1], get_event(j[1])), jobs))

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%MZ")
    raw = {f"{rid}|{t}": d for rid, t, d in results if d}
    (ROOT / "data" / "raw").mkdir(parents=True, exist_ok=True)
    json.dump(raw, open(ROOT / "data" / "raw" / f"kalshi_{stamp}.json", "w"))

    rows = []
    for rid, t, d in results:
        if not d:
            continue
        markets = d.get("markets") or (d.get("event") or {}).get("markets") or []
        for m in markets:
            bid, ask, last = fnum(m.get("yes_bid_dollars")), fnum(m.get("yes_ask_dollars")), fnum(m.get("last_price_dollars"))
            rows.append({
                "race_id": rid, "event": t, "ticker": m["ticker"], "party": party_of(m),
                "candidate": m.get("yes_sub_title", ""), "bid": bid, "ask": ask, "last": last,
                "volume": fnum(m.get("volume_fp")), "status": m.get("status"), "pulled_utc": stamp,
            })
    with open(ROOT / "data" / "kalshi_prices.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    covered = {r["race_id"] for r in rows}
    missing = [r for r in races if r not in covered]
    print(f"{len(rows)} markets across {len(covered)}/{len(races)} races; missing: {missing}")


if __name__ == "__main__":
    main()
