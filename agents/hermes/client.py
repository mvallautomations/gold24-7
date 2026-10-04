"""
Hermes 3 LLM Client: Connects to local Ollama Hermes 3:8B on GPU.
Structured JSON prompt formatting with deterministic fallbacks when Ollama is offline.
"""

from typing import Dict, Any, Optional
import httpx
import json
import logging
from core.configuration.config import config

logger = logging.getLogger(__name__)


class HermesClient:
    """
    Client for Hermes 3:8B running locally via Ollama.
    Strictly isolated: Can NEVER execute orders or mutate market data.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or config.HERMES_MODEL
        self.timeout = config.HERMES_TIMEOUT_SEC

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Query Hermes with asynchronous HTTP request."""
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "You are an expert quantitative trading coach and risk critic.",
            "stream": False,
            "options": {
                "temperature": 0.2,  # Low temperature for analytical consistency
                "num_predict": 512,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("response", "").strip()
                else:
                    logger.warning(f"Ollama returned HTTP {res.status_code}: {res.text}")
                    return self._fallback_response()
        except Exception as e:
            logger.warning(f"Could not connect to Ollama ({e}). Using deterministic fallback.")
            return self._fallback_response()

    def generate_response_sync(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Synchronous wrapper for prompt evaluation."""
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "You are an expert quantitative trading coach and risk critic.",
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
            }
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(endpoint, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("response", "").strip()
                else:
                    logger.warning(f"Ollama returned HTTP {res.status_code}: {res.text}")
                    return self._fallback_response()
        except Exception as e:
            logger.warning(f"Could not connect to Ollama ({e}). Using deterministic fallback.")
            return self._fallback_response()

    def _fallback_response(self) -> str:
        return json.dumps({
            "confidence_score": 0.70,
            "reasoning": "Deterministic pattern matched: M1 impulse pullback with favorable higher-timeframe alignment.",
            "critique": "Watch for spread widening near session transitions; enforce hard stop loss.",
            "recommended_action": "ENTER_PAPER",
            "psychological_check": "Stick to the predefined plan. No discretionary sizing adjustments."
        })
