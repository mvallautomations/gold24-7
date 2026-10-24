"""
GOLD24-7 to OpenTraderWorld Live Account Synchronizer
Fetches all historical and newly closed trades from the active MetaTrader 5 account
via the Windows MT5 Bridge and syncs them directly into OpenTraderWorld PostgreSQL journal.
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure virtual environment execution
venv_python = ROOT_DIR / ".venv" / "bin" / "python"
if sys.prefix == sys.base_prefix and venv_python.exists():
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

import re
import uuid
import httpx
import logging
import argparse
from datetime import datetime, timezone
from collections import defaultdict
from typing import List, Dict, Any, Optional

import psycopg2
from psycopg2.extras import Json

from core.configuration.config import config
from journal.ingestion.otw_journal_sync import OTWJournalIngestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MT5-OTW-Sync")

NAMESPACE_MT5 = uuid.UUID("33553767-2000-4000-8000-000000000000")


class MT5ToOTWSync:
    def __init__(self, bridge_url: Optional[str] = None):
        self.bridge_url = bridge_url or config.MT5_MCP_SERVER_URL
        self.otw_sync = OTWJournalIngestion()
        self.account_login = None

    def get_account_info(self) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.bridge_url}/health")
                if res.status_code == 200:
                    data = res.json()
                    self.account_login = data.get("login")
                    return data
        except Exception as e:
            logger.warning(f"Could not reach MT5 bridge health endpoint: {e}")
        return {}

    def fetch_deals(self, days_back: int = 365) -> List[Dict[str, Any]]:
        import time
        now_ts = int(time.time())
        from_ts = now_ts - (days_back * 86400)

        payload = {
            "jsonrpc": "2.0",
            "method": "history_deals_get",
            "params": {"date_from": from_ts, "date_to": now_ts + 86400},
            "id": 101
        }
        with httpx.Client(timeout=15.0) as client:
            res = client.post(f"{self.bridge_url}/rpc", json=payload)
            res.raise_for_status()
            data = res.json()
            return data.get("result", {}).get("deals", [])

    def fetch_open_positions(self) -> List[Dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "method": "positions_get",
            "params": {},
            "id": 102
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(f"{self.bridge_url}/rpc", json=payload)
                if res.status_code == 200:
                    return res.json().get("result", {}).get("positions", [])
        except Exception as e:
            logger.warning(f"Error fetching open positions: {e}")
        return []

    def get_live_positions_formatted(self) -> List[Dict[str, Any]]:
        raw = self.fetch_open_positions()
        formatted = []
        for p in raw:
            side_str = "BUY" if p.get("type") == 0 else "SELL"
            ts = p.get("time", 0)
            t_dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
            formatted.append({
                "id": p.get("ticket"),
                "ticket": p.get("ticket"),
                "symbol": p.get("symbol"),
                "side": side_str,
                "lots": p.get("volume", 0.0),
                "quantity_lots": p.get("volume", 0.0),
                "entry_price": p.get("price_open", 0.0),
                "current_price": p.get("price_current", 0.0),
                "stop_loss": p.get("sl", 0.0),
                "take_profit": p.get("tp", 0.0),
                "unrealized_pnl": round(p.get("profit", 0.0), 2),
                "opened_at": t_dt.strftime("%H:%M:%S"),
                "comment": p.get("comment", "")
            })
        return formatted

    def get_live_closed_trades_formatted(self, limit: int = 50) -> List[Dict[str, Any]]:
        query = """
        SELECT id, ticker, side, entry_price, exit_price, quantity, fees,
               fields->>'realized_pnl', exit_at, fields->>'comment',
               fields->>'position_id', stop_price, brackets, signal_name
        FROM journal_trades
        WHERE fields->>'environment' = 'LIVE_ACCOUNT'
        ORDER BY exit_at DESC
        LIMIT %s;
        """
        try:
            with self.otw_sync.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (limit,))
                    rows = cur.fetchall()
                    results = []
                    for r in rows:
                        results.append({
                            "id": r[0],
                            "symbol": r[1],
                            "side": r[2].upper(),
                            "entry_price": r[3],
                            "exit_price": r[4],
                            "quantity_lots": r[5],
                            "fees": r[6],
                            "realized_pnl": float(r[7]) if r[7] is not None else round((r[4] - r[3]) * r[5] * 100.0, 2),
                            "exit_at": r[8].strftime("%b %d %H:%M:%S") if r[8] else "",
                            "comment": r[9] or "",
                            "position_id": r[10] or "",
                            "stop_loss": r[11] or 0.0,
                            "brackets": r[12] or [],
                            "signal_name": r[13] or "XM_LIVE"
                        })
                    return results
        except Exception as e:
            logger.error(f"Error fetching live closed trades from OTW: {e}")
            return []

    def get_account_stats(self) -> Dict[str, Any]:
        acc = self.get_account_info()
        closed = self.get_live_closed_trades_formatted(limit=500)
        open_pos = self.get_live_positions_formatted()

        total_trades = len(closed)
        winning_trades = [t for t in closed if t.get("realized_pnl", 0) > 0]
        losing_trades = [t for t in closed if t.get("realized_pnl", 0) < 0]
        win_rate = (len(winning_trades) / total_trades * 100.0) if total_trades > 0 else 0.0
        gross_profit = sum(t.get("realized_pnl", 0) for t in winning_trades)
        gross_loss = abs(sum(t.get("realized_pnl", 0) for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)
        unrealized_pnl = sum(p.get("unrealized_pnl", 0) for p in open_pos)

        return {
            "account_login": acc.get("login", 335537672),
            "server": acc.get("server", "XMGlobal-MT5 9"),
            "company": acc.get("company", "XM Global Limited"),
            "leverage": acc.get("leverage", 1000),
            "currency": acc.get("currency", "USD"),
            "balance": acc.get("balance", 87.09),
            "equity": acc.get("equity", 61.55),
            "total_closed_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "open_positions_count": len(open_pos),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "is_live_account": True
        }

    def parse_closed_trades(self, deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        positions = defaultdict(list)
        for d in deals:
            pos_id = d.get("position_id")
            if pos_id:
                positions[pos_id].append(d)

        closed_trades = []
        for pos_id, p_deals in positions.items():
            p_deals.sort(key=lambda x: (x.get("time", 0), x.get("time_msc", 0)))
            in_deals = [d for d in p_deals if d.get("entry") in (0, 2)]
            out_deals = [d for d in p_deals if d.get("entry") in (1, 3)]

            # A closed trade requires at least one entry deal and one exit deal
            if not in_deals or not out_deals:
                continue

            symbol = in_deals[0].get("symbol", "GOLD#")
            # Deal type: 0 = DEAL_TYPE_BUY -> Long, 1 = DEAL_TYPE_SELL -> Short
            side = "long" if in_deals[0].get("type") == 0 else "short"
            entry_time = datetime.fromtimestamp(in_deals[0].get("time"), tz=timezone.utc)
            exit_time = datetime.fromtimestamp(out_deals[-1].get("time"), tz=timezone.utc)

            # Weighted average price
            total_in_vol = sum(d.get("volume", 0.0) for d in in_deals)
            entry_price = sum(d.get("price", 0.0) * d.get("volume", 0.0) for d in in_deals) / (total_in_vol or 1.0)

            total_out_vol = sum(d.get("volume", 0.0) for d in out_deals)
            exit_price = sum(d.get("price", 0.0) * d.get("volume", 0.0) for d in out_deals) / (total_out_vol or 1.0)

            total_profit = sum(d.get("profit", 0.0) for d in p_deals)
            total_commission = sum(d.get("commission", 0.0) for d in p_deals)
            total_swap = sum(d.get("swap", 0.0) for d in p_deals)
            total_fees = abs(total_commission) + abs(total_swap)
            net_pnl = total_profit + total_commission + total_swap

            comment = out_deals[-1].get("comment", "") or in_deals[0].get("comment", "")

            # Parse SL and TP from comments if present (e.g. "[tp 4138.00]" or "[sl 85327.06]")
            brackets = []
            stop_price = None
            tp_match = re.search(r"\[tp\s+([\d\.]+)\]", comment, re.IGNORECASE)
            sl_match = re.search(r"\[sl\s+([\d\.]+)\]", comment, re.IGNORECASE)
            if tp_match:
                tp_val = float(tp_match.group(1))
                brackets.append({"type": "take_profit", "price": tp_val})
            if sl_match:
                sl_val = float(sl_match.group(1))
                stop_price = sl_val
                brackets.append({"type": "stop_loss", "price": sl_val})

            asset_class = "crypto" if "BTC" in symbol or "ETH" in symbol else (
                "commodity" if "GOLD" in symbol or "XAU" in symbol or "GAU" in symbol or "SILVER" in symbol else "forex"
            )
            multiplier = 100.0 if asset_class == "commodity" else (1.0 if asset_class == "crypto" else 1.0)

            closed_trades.append({
                "position_id": pos_id,
                "symbol": symbol,
                "asset_class": asset_class,
                "side": side,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": total_out_vol,
                "fees": total_fees,
                "net_pnl": net_pnl,
                "multiplier": multiplier,
                "comment": comment,
                "brackets": brackets,
                "stop_price": stop_price,
                "exit_reason": "TP_HIT" if tp_match else ("SL_HIT" if sl_match else "MANUAL_CLOSE")
            })

        closed_trades.sort(key=lambda x: x["exit_time"])
        return closed_trades

    def sync_to_otw(self, closed_trades: List[Dict[str, Any]], category_id: Optional[str] = None) -> Dict[str, int]:
        cat_id = category_id or self.otw_sync.category_id

        # Insert SQL with ON CONFLICT / duplicate detection
        check_query = "SELECT id, import_row_hash FROM journal_trades WHERE import_row_hash IS NOT NULL"
        insert_query = """
        INSERT INTO journal_trades (
            id, category_id, ticker, asset_class, side,
            entry_at, exit_at, entry_price, exit_price, quantity,
            fees, leverage, multiplier, signal_name, feedback,
            currency, unit_type, stop_price, brackets, entries, exits, fields,
            import_row_hash, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        );
        """

        stats = {"total": len(closed_trades), "inserted": 0, "skipped": 0, "errors": 0}

        with self.otw_sync.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(check_query)
                existing_hashes = {r[1] for r in cur.fetchall()}

                for t in closed_trades:
                    row_hash = f"xm_mt5_{t['position_id']}"
                    if row_hash in existing_hashes:
                        stats["skipped"] += 1
                        continue

                    trade_uuid = str(uuid.uuid5(NAMESPACE_MT5, str(t["position_id"])))

                    entries = [{
                        "price": t["entry_price"],
                        "quantity": t["quantity"],
                        "time": t["entry_time"].isoformat()
                    }]
                    exits = [{
                        "price": t["exit_price"],
                        "quantity": t["quantity"],
                        "time": t["exit_time"].isoformat(),
                        "reason": t["exit_reason"]
                    }]
                    fields = {
                        "environment": "LIVE_ACCOUNT",
                        "broker": "XM Global",
                        "account_id": str(self.account_login or "335537672"),
                        "position_id": t["position_id"],
                        "realized_pnl": t["net_pnl"],
                        "net_pnl": t["net_pnl"],
                        "comment": t["comment"],
                        "exit_reason": t["exit_reason"],
                        "tags": ["XM-Live", t["symbol"], t["exit_reason"]],
                        "platform": "XM MetaTrader 5"
                    }
                    feedback = f"XM MT5 Execution (Position #{t['position_id']}). Realized PnL: {'+$' if t['net_pnl'] >= 0 else '-$'}{abs(t['net_pnl']):.2f}. Comment: '{t['comment']}'"

                    try:
                        cur.execute(insert_query, (
                            trade_uuid,
                            cat_id,
                            t["symbol"],
                            t["asset_class"],
                            t["side"],
                            t["entry_time"],
                            t["exit_time"],
                            t["entry_price"],
                            t["exit_price"],
                            t["quantity"],
                            t["fees"],
                            1000.0,
                            t["multiplier"],
                            "XM_MANUAL" if not t["comment"] else "XM_TP_SL",
                            feedback,
                            "USD",
                            "lot",
                            t["stop_price"],
                            Json(t["brackets"]),
                            Json(entries),
                            Json(exits),
                            Json(fields),
                            row_hash,
                            t["exit_time"],  # created_at matched to execution time
                            datetime.now(timezone.utc)
                        ))
                        existing_hashes.add(row_hash)
                        stats["inserted"] += 1
                    except Exception as e:
                        logger.error(f"Failed to insert position #{t['position_id']}: {e}")
                        stats["errors"] += 1

            conn.commit()

        return stats


def main():
    parser = argparse.ArgumentParser(description="Sync live XM MT5 account trades into OpenTraderWorld journal")
    parser.add_argument("--days", type=int, default=365, help="Number of past days to sync")
    args = parser.parse_args()

    print("======================================================================")
    print("  XM MetaTrader 5 -> OpenTraderWorld Journal Trade Synchronizer")
    print("======================================================================")

    syncer = MT5ToOTWSync()
    acc = syncer.get_account_info()
    if not acc or not acc.get("connected"):
        print("[ERROR] Cannot reach MT5 Bridge on port 8082 or MT5 is disconnected.")
        sys.exit(1)

    print(f"Connected Account: {acc.get('login')} ({acc.get('server')}, {acc.get('company')})")
    print(f"Current Balance: ${acc.get('balance'):.2f} | Equity: ${acc.get('equity'):.2f}")

    print("\n[1/3] Fetching historical deals from MT5...")
    deals = syncer.fetch_deals(days_back=args.days)
    print(f"  Retrieved {len(deals)} raw deal records.")

    print("\n[2/3] Reconstructing round-trip closed trades...")
    closed_trades = syncer.parse_closed_trades(deals)
    print(f"  Parsed {len(closed_trades)} completed trades.")

    print("\n[3/3] Synchronizing into OpenTraderWorld PostgreSQL database...")
    stats = syncer.sync_to_otw(closed_trades)
    print("======================================================================")
    print(f"  Sync Summary:")
    print(f"    - Total Trades Found:   {stats['total']}")
    print(f"    - Newly Ingested:       {stats['inserted']}")
    print(f"    - Already Synced:       {stats['skipped']}")
    print(f"    - Errors:               {stats['errors']}")
    print("======================================================================")
    print("  Open OpenTraderWorld Journal at: http://localhost:5454/journal")


if __name__ == "__main__":
    main()
