"""Characterize current order-dispatch source paths before removing them."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("relative_path", "required_text"),
    [
        ("dashboard/server.py", '"method": "order_send"'),
        ("scripts/daemon_runner.py", '"method": "order_send"'),
        ("scripts/mt5_bridge_server.py", "mt5.order_send("),
        ("core/M1_Pullback_Baseline_EA.mq5", "trade.Buy("),
        ("core/M1_Pullback_Benchmark_EA.mq5", "trade.Sell("),
        ("core/BTCUSD_Pullback_Benchmark_EA.mq5", "trade.Buy("),
        ("core/OptionB_Mitigate_And_Recoup.mq5", "m_trade.Sell("),
        ("core/playbook/Playbook_Scalping_Cockpit_EA.mq5", "trade.Buy("),
    ],
)
def test_live_dispatch_path_currently_exists(relative_path, required_text):
    source_path = ROOT / relative_path

    assert source_path.is_file()
    assert required_text in source_path.read_text(encoding="utf-8")
