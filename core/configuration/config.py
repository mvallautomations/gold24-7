"""
Global configuration for GOLD24-7 Research & Paper Trading Platform.
Enforces that LIVE trading is permanently locked to FALSE.
"""

from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class AppConfig(BaseSettings):
    # Hard Safety Boundary
    ENVIRONMENT: str = Field(default="PAPER", frozen=True)
    ALLOW_LIVE_EXECUTION: bool = Field(default=False, frozen=True)
    IS_SIMULATION_ONLY: bool = Field(default=True, frozen=True)

    # Broker & Symbol Resolver
    DEFAULT_BROKER: str = "XM"
    DEFAULT_SYMBOLS: List[str] = ["XAUUSD", "GAUUSD", "BTCUSD", "ETHUSD"]

    # MT5 / MCP Connection
    MT5_MCP_SERVER_URL: str = "http://172.26.144.1:8080/sse"
    MT5_HOST: str = "172.26.144.1"
    MT5_PORT: int = 8080

    # Hermes 3 LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    HERMES_MODEL: str = "hermes3:8b"
    HERMES_TIMEOUT_SEC: float = 30.0

    # OpenTraderWorld Integration
    OTW_BASE_URL: str = "http://127.0.0.1:5454"
    OTW_DATABASE_URL: str = "postgres://otw:ffec9865bcfd7b23553814d390129df4d7440334657d9b4d@172.28.53.3:5432/opentraderworld"
    OTW_DEFAULT_CATEGORY_ID: str = "e170b267-7875-4afb-9f71-4abbc1f7cd52"

    # Risk Management & Paper Trading
    INITIAL_PAPER_BALANCE: float = 10000.0  # $10,000 USD virtual capital
    RISK_PER_TRADE_PCT: float = 1.0        # 1% per paper trade
    MAX_OPEN_POSITIONS: int = 2
    SLIPPAGE_POINTS_ESTIMATE: float = 2.0

    # Research Dashboard
    DASHBOARD_PORT: int = 8585
    DASHBOARD_HOST: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        extra = "ignore"


# Global singleton instance
config = AppConfig()
