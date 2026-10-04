"""
Paper trade models and OpenTraderWorld ingestion structures.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field
from core.models.signal import SignalDirection, SetupType


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaperOrder(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str
    symbol: str
    side: PositionSide
    setup: SetupType
    quantity_lots: float
    entry_price: float
    stop_loss: float
    take_profit: float
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "PENDING"


class PaperPosition(BaseModel):
    position_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    signal_id: str
    symbol: str
    side: PositionSide
    entry_price: float
    current_price: float
    quantity_lots: float
    stop_loss: float
    take_profit: float
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    exit_reason: Optional[str] = None  # TP_HIT, SL_HIT, MANUAL_CLOSE, TIME_EXPIRY
    fees: float = 0.0
    slippage_points: float = 0.0
    tags: List[str] = Field(default_factory=list)
