#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$PROJECT_DIR/.venv/bin/activate"
export PYTHONPATH="$PROJECT_DIR"

echo "======================================================================"
echo "  Starting GOLD24-7 Research & Paper-Trading Dashboard"
echo "  Dashboard URL: http://localhost:8585"
echo "  Safety Boundary: SIMULATION_ONLY | LIVE ORDERS STRICTLY DISABLED"
echo "======================================================================"

python3 "$PROJECT_DIR/dashboard/server.py"
