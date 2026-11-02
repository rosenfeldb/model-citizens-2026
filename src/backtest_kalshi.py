"""Backtest: how well-calibrated were Kalshi race markets on Nov 1, 2024?

For every 2024 House/Senate race market on Kalshi we take the Nov 1, 2024
daily close (the same "pulled Nov 1" convention the competition uses) and the
settled result. Output: data/backtest_2024.csv (one row per market).
"""
import csv
import datetime as dt
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.elections.kalshi.com/trade-api/v2/"
# Daily candles end at midnight US Eastern; this window holds the Nov 1 candle.
START = int(dt.datetime(2024, 11, 1, 4, tzinfo=dt.timezone.utc).timestamp())
END = int(dt.datetime(2024, 11, 2, 5, tzinfo=dt.timezone.utc).timestamp())


def get(path):
    for attempt in range(8):
        try:
            with urllib.request.urlopen(API + path, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def nov1_price(ticker):
    d = get(f"historical/markets/{ticker}/candlesticks?start_ts={START}&end_ts={END}&period_interval=1440")
    if not d or not d.get("candlesticks"):
        return None, None, None
    c = d["candlesticks"][-1]
    close = fnum((c.get("price") or {}).get("close"))
    bid = fnum((c.get("yes_bid") or {}).get("close"))
    ask = fnum((c.get("yes_ask") or {}).get("close"))
    return close, bid, ask


def main():
    series = json.load(open(ROOT / "data" / "raw" / "kalshi_series.json"))["series"]
    tick = [s["ticker"] for s in series if re.match(r"^(HOUSE|SENATE)[A-Z]{2}\d*S?$", s["ticker"])]
    with ThreadPoolExecutor(3) as ex:
        lists = list(ex.map(lambda t: get(f"historical/markets?series_ticker={t}&limit=200"), tick))
    markets = [m for d in lists if d for m in d.get("markets", []) if m["event_ticker"].endswith("-24")]
    with ThreadPoolExecutor(3) as ex:
        prices = list(ex.map(lambda m: nov1_price(m["ticker"]), markets))
    rows = []
    for m, (close, bid, ask) in zip(markets, prices):
        rows.append({"event": m["event_ticker"], "ticker": m["ticker"], "candidate": m.get("yes_sub_title"),
                     "result": m.get("result"), "close": close, "bid": bid, "ask": ask,
                     "volume": fnum(m.get("volume_fp"))})
    with open(ROOT / "data" / "backtest_2024.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    priced = sum(r["close"] is not None for r in rows)
    print(f"{len(rows)} markets in {len({r['event'] for r in rows})} races; {priced} with a Nov 1 price")


if __name__ == "__main__":
    main()
