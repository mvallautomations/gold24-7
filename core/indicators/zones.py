"""
Deterministic Support & Resistance Candidate Zones Engine.
Extracts empirical price clusters, test touches, and zone strengths from swing structures.
"""

from typing import List, Tuple, Optional
import numpy as np
from core.models.candle import Bar, Timeframe
from core.models.zones import SRZone, ZoneType


class SupportResistanceEngine:
    """
    Identifies high-probability candidate support and resistance price zones.
    Replaces single-line price illusions with realistic cluster boundaries.
    """

    def __init__(self, swing_window: int = 3, cluster_tolerance_pct: float = 0.002):
        self.swing_window = swing_window
        self.cluster_tolerance_pct = cluster_tolerance_pct

    def find_swings(self, bars: List[Bar]) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """
        Locate swing highs and swing lows across completed bars.
        Returns: (swing_highs, swing_lows) as [(index, price)]
        """
        completed = [b for b in bars if b.shift >= 1]
        n = len(completed)
        w = self.swing_window

        swing_highs: List[Tuple[int, float]] = []
        swing_lows: List[Tuple[int, float]] = []

        if n < (w * 2 + 1):
            return swing_highs, swing_lows

        for i in range(w, n - w):
            current_h = completed[i].high
            current_l = completed[i].low

            # Check if local peak
            is_peak = all(current_h >= completed[i - j].high for j in range(1, w + 1)) and \
                      all(current_h >= completed[i + j].high for j in range(1, w + 1))
            if is_peak:
                swing_highs.append((i, current_h))

            # Check if local trough
            is_trough = all(current_l <= completed[i - j].low for j in range(1, w + 1)) and \
                        all(current_l <= completed[i + j].low for j in range(1, w + 1))
            if is_trough:
                swing_lows.append((i, current_l))

        return swing_highs, swing_lows

    def build_zones(self, bars: List[Bar], timeframe: Timeframe, atr: float = 1.0) -> List[SRZone]:
        """
        Synthesize candidate support & resistance zones by clustering swings.
        """
        completed = [b for b in bars if b.shift >= 1]
        if not completed:
            return []

        current_price = completed[-1].close
        swing_highs, swing_lows = self.find_swings(completed)

        zones: List[SRZone] = []

        # 1. Cluster Resistance Swings (Highs)
        zones.extend(self._cluster_swings(
            swings=swing_highs,
            completed_bars=completed,
            zone_type=ZoneType.RESISTANCE,
            timeframe=timeframe,
            atr=atr
        ))

        # 2. Cluster Support Swings (Lows)
        zones.extend(self._cluster_swings(
            swings=swing_lows,
            completed_bars=completed,
            zone_type=ZoneType.SUPPORT,
            timeframe=timeframe,
            atr=atr
        ))

        # Sort zones by price low
        zones.sort(key=lambda z: z.low)
        return zones

    def _cluster_swings(
        self,
        swings: List[Tuple[int, float]],
        completed_bars: List[Bar],
        zone_type: ZoneType,
        timeframe: Timeframe,
        atr: float
    ) -> List[SRZone]:
        if not swings:
            return []

        # Group swings by price closeness (proportional to ATR or tolerance)
        tolerance = max(atr * 0.4, swings[0][1] * self.cluster_tolerance_pct)
        sorted_swings = sorted(swings, key=lambda x: x[1])

        clusters: List[List[Tuple[int, float]]] = []
        current_cluster: List[Tuple[int, float]] = [sorted_swings[0]]

        for swing in sorted_swings[1:]:
            cluster_mean = np.mean([s[1] for s in current_cluster])
            if abs(swing[1] - cluster_mean) <= tolerance:
                current_cluster.append(swing)
            else:
                clusters.append(current_cluster)
                current_cluster = [swing]
        if current_cluster:
            clusters.append(current_cluster)

        result_zones: List[SRZone] = []
        n_bars = len(completed_bars)

        for cluster in clusters:
            prices = [s[1] for s in cluster]
            min_p = min(prices)
            max_p = max(prices)

            # Zone width should span at least 0.2 ATR for realistic execution bracket
            min_width = atr * 0.2 if atr > 0 else (min_p * 0.0005)
            if (max_p - min_p) < min_width:
                half_diff = (min_width - (max_p - min_p)) / 2.0
                min_p -= half_diff
                max_p += half_diff

            # Calculate touches by testing all completed bars against this envelope
            touches = 0
            for b in completed_bars:
                if b.low <= max_p and b.high >= min_p:
                    touches += 1

            # Recency bonus: weight more recent swings
            latest_idx = max([s[0] for s in cluster])
            recency_weight = (latest_idx / n_bars) if n_bars > 0 else 1.0

            # Strength: 1.0 to 5.0 score
            raw_strength = (len(cluster) * 1.2) + (touches * 0.3) + (recency_weight * 1.5)
            strength = round(float(np.clip(raw_strength, 1.0, 5.0)), 2)

            result_zones.append(SRZone(
                type=zone_type,
                timeframe=timeframe,
                low=round(min_p, 4),
                high=round(max_p, 4),
                strength=strength,
                touches=touches,
                source="swing_cluster",
                created_at_price=round(float(np.mean(prices)), 4)
            ))

        return result_zones
