"""
OpenTraderWorld Journal Ingestion: Ingests paper trades and simulation signals
directly into the local OpenTraderWorld PostgreSQL database and journal ledger.
"""

import time
from typing import Optional, Dict, Any, List
import uuid
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, timezone
import logging

from core.models.trade import PaperPosition, PositionSide
from core.configuration.config import config

logger = logging.getLogger(__name__)


class OTWJournalIngestion:
    """
    Synchronizes paper trade executions and Hermes coaching feedback
    into OpenTraderWorld's institutional trading journal tables.
    """

    _last_failed_time: float = 0.0

    def __init__(
        self,
        db_url: Optional[str] = None,
        category_id: Optional[str] = None
    ):
        self.db_url = db_url or config.OTW_DATABASE_URL
        self.category_id = category_id or config.OTW_DEFAULT_CATEGORY_ID

    def get_connection(self):
        if time.time() - OTWJournalIngestion._last_failed_time < 30.0:
            raise ConnectionError("OTW Database offline (cached)")
        try:
            return psycopg2.connect(self.db_url, connect_timeout=1)
        except Exception:
            if "172.28.53.2" in self.db_url:
                alt = self.db_url.replace("172.28.53.2", "172.28.53.3")
                try:
                    return psycopg2.connect(alt, connect_timeout=1)
                except Exception:
                    OTWJournalIngestion._last_failed_time = time.time()
                    raise
            elif "172.28.53.3" in self.db_url:
                alt = self.db_url.replace("172.28.53.3", "172.28.53.2")
                try:
                    return psycopg2.connect(alt, connect_timeout=1)
                except Exception:
                    OTWJournalIngestion._last_failed_time = time.time()
                    raise
            OTWJournalIngestion._last_failed_time = time.time()
            raise

    def ingest_closed_trade(self, position: PaperPosition, coach_feedback: str = "") -> Optional[str]:
        """
        Record a closed paper trade into OpenTraderWorld public.journal_trades.
        """
        trade_id = str(uuid.uuid4())
        asset_class = "crypto" if "BTC" in position.symbol or "ETH" in position.symbol else (
            "commodity" if "XAU" in position.symbol or "GAU" in position.symbol or "GOLD" in position.symbol else "forex"
        )
        side = position.side.value  # 'long' or 'short'

        brackets = [
            {"type": "take_profit", "price": position.take_profit},
            {"type": "stop_loss", "price": position.stop_loss}
        ]
        entries = [
            {"price": position.entry_price, "quantity": position.quantity_lots, "time": position.opened_at.isoformat()}
        ]
        exits = [
            {"price": position.exit_price or position.current_price, "quantity": position.quantity_lots, "time": (position.closed_at or datetime.now(timezone.utc)).isoformat(), "reason": position.exit_reason or "MANUAL"}
        ]
        fields = {
            "environment": "PAPER",
            "slippage_points": position.slippage_points,
            "realized_pnl": position.realized_pnl,
            "exit_reason": position.exit_reason,
            "tags": position.tags,
            "platform": "GOLD24-7 Research & Paper Engine"
        }

        query = """
        INSERT INTO journal_trades (
            id, category_id, ticker, asset_class, side,
            entry_at, exit_at, entry_price, exit_price, quantity,
            fees, leverage, multiplier, signal_name, feedback,
            currency, unit_type, stop_price, brackets, entries, exits, fields,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            NOW(), NOW()
        );
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        trade_id,
                        self.category_id,
                        position.symbol,
                        asset_class,
                        side,
                        position.opened_at,
                        position.closed_at or datetime.now(timezone.utc),
                        position.entry_price,
                        position.exit_price or position.current_price,
                        position.quantity_lots,
                        position.fees,
                        1.0,
                        100.0 if asset_class == "commodity" else 1.0,
                        position.tags[0] if position.tags else "SIMULATION_PULLBACK",
                        coach_feedback,
                        "USD",
                        "lot",
                        position.stop_loss,
                        Json(brackets),
                        Json(entries),
                        Json(exits),
                        Json(fields)
                    ))
                conn.commit()
            logger.info(f"Successfully ingested trade {trade_id} into OpenTraderWorld DB ({position.symbol} {pnl_str(position.realized_pnl)})")
            return trade_id
        except Exception as e:
            logger.warning(f"Could not connect to OpenTraderWorld PostgreSQL database ({e}). Trade logged locally.")
            return None


def pnl_str(val: float) -> str:
    return f"+${val:.2f}" if val >= 0 else f"-${abs(val):.2f}"
