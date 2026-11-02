#!/usr/bin/env bash
# Rebuild everything from fresh Kalshi prices. About 3 minutes.
set -euo pipefail
cd "$(dirname "$0")"
python3 src/make_template.py
python3 src/fetch_kalshi.py
python3 src/market.py
python3 src/model.py
python3 src/make_picks.py
python3 src/evaluate.py
python3 src/chart.py
# Slower studies (run on demand):
#   python3 src/backtest_kalshi.py   # 2024 calibration data
#   python3 src/tournament.py        # baseline strategy table
#   python3 src/robustness.py        # strategies under alternative truths
#   python3 src/sensitivity.py       # floor / swing size / field sweep (~6 min)
