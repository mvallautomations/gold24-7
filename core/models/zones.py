"""
Support & Resistance Zone models representing candidate price clusters
rather than naive, brittle single-price points.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field
from core.models.candle import Timeframe


class ZoneType(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"


class SRZone(BaseModel):
    type: ZoneType
    timeframe: Timeframe
    low: float = Field(..., description="Bottom edge of price zone")
    high: float = Field(..., description="Top edge of price zone")
    strength: float = Field(default=1.0, description="Normalized strength score 0.0 - 5.0")
    touches: int = Field(default=1, description="Number of times price tested this zone")
    source: str = Field(default="swing", description="Method used to detect zone (e.g. swing, order_block, volume)")
    created_at_price: float = Field(default=0.0)

    @property
    def mid_price(self) -> float:
        return (self.low + self.high) / 2.0

    @property
    def zone_width(self) -> float:
        return self.high - self.low

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high

    def distance_to(self, price: float) -> float:
        if self.contains(price):
            return 0.0
        if price > self.high:
            return price - self.high
        return self.low - price
