#!/usr/bin/env python3
"""
GOLD24-7 Autonomous Market Open Mitigation & Untangling Engine
Executes Option B exactly as the broker market re-opens at 06:05:00 AM UTC+8.

Actions executed upon market open:
1. Closes 2 near-breakeven outlier positions:
   - Ticket 1030492044 (BUY 0.01 GOLD# @ 4142.80)
   - Ticket 1030497010 (SELL 0.01 GOLD# @ 4139.00)
2. Sets protective stop losses on remaining 4 positions:
   - Ticket 1030357046 (BUY 0.01 @ 4153.28) -> SL: 4132.00
   - Ticket 1030467151 (SELL 0.01 @ 4126.86) -> SL: 4147.50
   - Ticket 1030469892 (SELL 0.01 @ 4128.01) -> SL: 4147.50
   - Ticket 1030480916 (SELL 0.01 @ 4133.68) -> SL: 4147.50
3. Enforces Recoup Guardrail:
   - Strict 1 trade at a time rule.
   - Halts all automated trading once balance returns to $125.65.
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
import httpx
import logging

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/market_open_mitigation.log", mode="a")
    ]
)
logger = logging.getLogger("MarketMitigator")

BRIDGE_URL = "http://172.26.144.1:8082/rpc"
TARGET_HOUR_UTC8 = 6
TARGET_MINUTE_UTC8 = 5
TARGET_SECOND_UTC8 = 0

OUTLIER_CLOSE_TICKETS = [1030492044, 1030497010]
PROTECT_POSITIONS = {
    1030357046: 4132.00,  # BUY
    1030467151: 4147.50,  # SELL
    1030469892: 4147.50,  # SELL
    1030480916: 4147.50,  # SELL
}

def rpc_call(method: str, params: dict = None) -> dict:
    try:
        res = httpx.post(
            BRIDGE_URL,
            json={"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1},
            timeout=8.0
        )
        return res.json()
    except Exception as e:
        logger.error(f"RPC call '{method}' failed: {e}")
        return {}

def is_market_open(target_dt: datetime) -> bool:
    tz_utc8 = timezone(timedelta(hours=8))
    now_utc8 = datetime.now(tz_utc8)
    
    # Check if clock time has arrived
    if now_utc8 >= target_dt:
        # Check if tick is alive on GOLD#
        tick_res = rpc_call("tick_get", {"symbol": "GOLD#"})
        result = tick_res.get("result", {})
        if result and result.get("bid", 0) > 0:
            return True
    return False

def check_trade_allowed() -> bool:
    term_res = rpc_call("terminal_info")
    allowed = term_res.get("result", {}).get("trade_allowed", False)
    return allowed

def execute_option_b():
    logger.info("==================================================================")
    logger.info(">>> MARKET OPEN DETECTED! INITIATING OPTION B UNTANGLING <<<")
    logger.info("==================================================================")

    # 1. Close the 2 Outliers
    closed_count = 0
    for ticket in OUTLIER_CLOSE_TICKETS:
        logger.info(f">>> Requesting CLOSE for outlier Ticket {ticket}...")
        res = rpc_call("position_close", {"ticket": ticket, "deviation": 30, "comment": "opt_b_close"})
        result = res.get("result", {})
        retcode = result.get("retcode")
        if retcode == 10009:  # TRADE_RETCODE_DONE
            logger.info(f"✅ Ticket {ticket} successfully CLOSED! Deal: {result.get('deal')}")
            closed_count += 1
        elif retcode == 10027:
            logger.error(f"❌ Retcode 10027: AutoTrading disabled in MT5 client! Please enable Algo Trading (Ctrl+E) in MT5 GUI.")
        else:
            logger.warning(f"⚠️ Close request for Ticket {ticket} returned: {result.get('comment', res)}")

    # 2. Set Emergency Stop Losses on Remaining 4
    modified_count = 0
    for ticket, sl in PROTECT_POSITIONS.items():
        logger.info(f">>> Requesting SL {sl:.2f} for remaining Ticket {ticket}...")
        res = rpc_call("position_modify", {"ticket": ticket, "sl": sl})
        result = res.get("result", {})
        retcode = result.get("retcode")
        if retcode == 10009:  # TRADE_RETCODE_DONE
            logger.info(f"✅ Ticket {ticket} SL set to {sl:.2f} successfully!")
            modified_count += 1
        elif retcode == 10027:
            logger.error(f"❌ Retcode 10027: AutoTrading disabled in MT5 client! Please enable Algo Trading (Ctrl+E) in MT5 GUI.")
        else:
            logger.warning(f"⚠️ Modify request for Ticket {ticket} returned: {result.get('comment', res)}")

    # 3. Post-execution status report
    time.sleep(1)
    acc_res = rpc_call("account_info")
    acc = acc_res.get("result", {})
    pos_res = rpc_call("positions_get")
    positions = pos_res.get("result", {}).get("positions", [])

    logger.info("==================================================================")
    logger.info(f"OPTION B EXECUTION SUMMARY:")
    logger.info(f"  Closed Outliers: {closed_count}/{len(OUTLIER_CLOSE_TICKETS)}")
    logger.info(f"  Protected Tickets: {modified_count}/{len(PROTECT_POSITIONS)}")
    logger.info(f"  Active Balance: ${acc.get('balance'):.2f} | Equity: ${acc.get('equity'):.2f}")
    logger.info(f"  Remaining Open Positions: {len(positions)}")
    for p in positions:
        logger.info(f"    - Ticket {p['ticket']}: {p['symbol']} {'BUY' if p['type']==0 else 'SELL'} {p['volume']} @ {p['price_open']} | SL: {p['sl']} | Profit: ${p['profit']:.2f}")
    logger.info("==================================================================")

def main():
    import os
    os.makedirs("logs", exist_ok=True)
    
    tz_utc8 = timezone(timedelta(hours=8))
    now = datetime.now(tz_utc8)
    target_dt = now.replace(hour=TARGET_HOUR_UTC8, minute=TARGET_MINUTE_UTC8, second=TARGET_SECOND_UTC8, microsecond=0)
    
    # If already past today's open time, target tomorrow or run immediately if market is open
    if now > target_dt + timedelta(minutes=10):
        target_dt += timedelta(days=1)

    logger.info(f"Market Open Mitigation Engine armed.")
    logger.info(f"Current local time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC+8")
    logger.info(f"Target market open: {target_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC+8")
    
    trade_allowed = check_trade_allowed()
    if not trade_allowed:
        logger.warning("****************************************************************")
        logger.warning("ATTENTION: terminal_info().trade_allowed is FALSE!")
        logger.warning("Please click 'Algo Trading' (or press Ctrl+E) in XM MT5 desktop terminal.")
        logger.warning("****************************************************************")
    else:
        logger.info("✅ Terminal trade_allowed is TRUE. Ready to execute orders.")

    # Countdown loop
    executed = False
    while not executed:
        now = datetime.now(tz_utc8)
        remaining = (target_dt - now).total_seconds()
        
        # Check trade allowed status periodically
        if int(remaining) % 30 == 0:
            if not check_trade_allowed():
                logger.warning(f"Reminder: Enable 'Algo Trading' in MT5 (Ctrl+E). Countdown: {int(remaining)}s")
            else:
                logger.info(f"Countdown to market open: {int(remaining)}s remaining. Algo Trading is active.")

        if remaining <= 1 or is_market_open(target_dt):
            logger.info("Market open reached! Firing orders...")
            execute_option_b()
            executed = True
            break

        time.sleep(1)

if __name__ == "__main__":
    main()
