#!/usr/bin/env python3
"""
GOLD24-7: 1-Minute Scalping Playbook Multi-Timeframe Trial Simulation Runner
Runs mechanical diagnostic and walk-forward simulation across M15, M5, and M1 timeframes.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.playbook.scalping_playbook import run_trial_simulation
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="1-Minute Scalping Playbook Trial Simulation HUD")
    parser.add_argument("symbol_pos", nargs="?", default=None, help="Target symbol (e.g. GOLD, BTCUSD#)")
    parser.add_argument("--symbol", "-s", default="GOLD", help="Target symbol (default: GOLD)")
    parser.add_argument("--lookback", "-l", type=int, default=80, help="Lookback 1M bars (default: 80)")
    parser.add_argument("--grade", "-g", default="B", choices=["A+", "B", "ALL"], help="Minimum setup grade (default: B)")
    args = parser.parse_args()

    target_sym = (args.symbol_pos or args.symbol).upper()
    run_trial_simulation(symbol=target_sym, lookback=args.lookback, min_grade=args.grade)
