"""
Multi-timeframe channel mapping engine.

Reproduces the discretionary "draw the channel" workflow on every timeframe:

1. Find confirmed swing pivots.
2. Draw the primary trend line through two pivots (highs for the upper rail,
   lows for the lower rail) that has the most touches and the fewest breaches.
3. Draw the parallel rail through the most extreme opposite wick.
4. Project both rails to the current bar and stack the timeframes so that
   channel rails and horizontal swing levels that coincide ("confluence zones")
   stand out, e.g. a D1 descending-channel floor sitting on horizontal support.

Channels are fitted in bar-index space (what a trader sees on screen) and
exported as (time, price) points so any chart can draw them. Analysis only:
nothing here places or authorises orders.
"""

from typing import Any, Dict, List, Optional, Tuple

from core.models.candle import Bar

TF_ORDER = ["D1", "H4", "H1", "M15", "M5", "M1"]
TF_MINUTES = {"D1": 1440, "H4": 240, "H1": 60, "M15": 15, "M5": 5, "M1": 1}
TF_WEIGHT = {"D1": 3.0, "H4": 2.0, "H1": 1.5, "M15": 1.0, "M5": 0.5, "M1": 0.25}
PIVOT_STRENGTH = {"D1": 3, "H4": 3, "H1": 4, "M15": 4, "M5": 5, "M1": 5}
LOOKBACK = {"D1": 120, "H4": 150, "H1": 150, "M15": 150, "M5": 150, "M1": 150}

MIN_ANCHOR_GAP = 5
MIN_WIDTH_ATR = 1.0
MIN_CLOSES_INSIDE = 0.7
FLAT_DRIFT_ATR = 1.0
EDGE_ZONE = 0.15
PROJECTION_BARS = 10


def _tf_name(tf: Any) -> str:
    return tf.value if hasattr(tf, "value") else str(tf)


def _atr(bars: List[Bar], period: int = 14) -> float:
    if len(bars) < 2:
        return 0.0
    trs = []
    for prev, cur in zip(bars[:-1], bars[1:]):
        trs.append(max(cur.high - cur.low, abs(cur.high - prev.close), abs(cur.low - prev.close)))
    window = trs[-period:]
    return sum(window) / len(window) if window else 0.0


def find_pivots(bars: List[Bar], left: int, right: int) -> List[Dict[str, Any]]:
    """Confirmed swing highs/lows with their bar index (same rules as compute_swing_channels)."""
    pivots: List[Dict[str, Any]] = []
    for i in range(left, len(bars) - right):
        cur = bars[i]
        if all(cur.high > bars[i - k].high for k in range(1, left + 1)) and all(
            cur.high >= bars[i + k].high for k in range(1, right + 1)
        ):
            pivots.append({"idx": i, "kind": "high", "price": cur.high, "time": int(cur.timestamp.timestamp())})
        if all(cur.low < bars[i - k].low for k in range(1, left + 1)) and all(
            cur.low <= bars[i + k].low for k in range(1, right + 1)
        ):
            pivots.append({"idx": i, "kind": "low", "price": cur.low, "time": int(cur.timestamp.timestamp())})
    return pivots


def _distinct_touches(indices: List[int], gap: int = 3) -> int:
    count, last = 0, None
    for k in indices:
        if last is None or k - last >= gap:
            count += 1
            last = k
    return count


def _build_channel(
    tf: str,
    bars: List[Bar],
    side: str,
    idx1: int,
    p1: float,
    idx2: int,
    p2: float,
    atr: float,
    tol: float,
    n_fit: int,
    source: str,
    opposite_price_at: Optional[Tuple[int, float]] = None,
) -> Optional[Dict[str, Any]]:
    """Build a channel from a primary rail (side='upper'|'lower') through two anchors.

    The parallel rail passes through the extreme opposite wick, or through
    `opposite_price_at` (bar index, price) for manually drawn channels.
    """
    if idx2 == idx1 or atr <= 0:
        return None
    slope = (p2 - p1) / (idx2 - idx1)
    fit = bars[:n_fit]
    highs = [b.high for b in fit]
    lows = [b.low for b in fit]
    closes = [b.close for b in fit]
    start = min(idx1, idx2)
    base_idx = idx1

    def line_at(k: int, price0: float = p1) -> float:
        return price0 + slope * (k - base_idx)

    if opposite_price_at is not None:
        o_idx, o_price = opposite_price_at
        offset = o_price - line_at(o_idx)
    elif side == "upper":
        offset = min(lows[k] - line_at(k) for k in range(start, n_fit))
    else:
        offset = max(highs[k] - line_at(k) for k in range(start, n_fit))

    if (side == "upper" and offset >= 0) or (side == "lower" and offset <= 0):
        return None
    width = abs(offset)
    if width < MIN_WIDTH_ATR * atr and opposite_price_at is None:
        return None

    upper_off, lower_off = (0.0, offset) if side == "upper" else (offset, 0.0)

    def upper_at(k: int) -> float:
        return line_at(k) + upper_off

    def lower_at(k: int) -> float:
        return line_at(k) + lower_off

    up_touch, lo_touch, up_viol, lo_viol, inside = [], [], 0, 0, 0
    for k in range(start, n_fit):
        u, l = upper_at(k), lower_at(k)
        if highs[k] - u > tol:
            up_viol += 1
        elif abs(highs[k] - u) <= tol:
            up_touch.append(k)
        if l - lows[k] > tol:
            lo_viol += 1
        elif abs(lows[k] - l) <= tol:
            lo_touch.append(k)
        if l - tol <= closes[k] <= u + tol:
            inside += 1
    span = max(n_fit - start, 1)
    inside_frac = inside / span
    if source == "AUTO" and inside_frac < MIN_CLOSES_INSIDE:
        return None

    up_t, lo_t = _distinct_touches(up_touch), _distinct_touches(lo_touch)
    primary_t, primary_v = (up_t, up_viol) if side == "upper" else (lo_t, lo_viol)
    score = (
        2.0 * primary_t
        + 1.5 * (lo_t if side == "upper" else up_t)
        - 4.0 * primary_v
        + 3.0 * (max(idx1, idx2) / max(n_fit, 1))
        + 6.0 * inside_frac
    )

    last_idx = len(bars) - 1
    last_close = bars[last_idx].close
    upper_now, lower_now = upper_at(last_idx), lower_at(last_idx)
    mid_now = (upper_now + lower_now) / 2.0
    chan_width_now = upper_now - lower_now
    pct = (last_close - lower_now) / chan_width_now if chan_width_now else 0.5

    drift = slope * span
    if abs(drift) < FLAT_DRIFT_ATR * atr:
        direction = "HORIZONTAL"
    else:
        direction = "ASCENDING" if slope > 0 else "DESCENDING"

    if last_close > upper_now + tol:
        state = "BROKEN_ABOVE"
    elif last_close < lower_now - tol:
        state = "BROKEN_BELOW"
    elif pct >= 1 - EDGE_ZONE:
        state = "AT_UPPER"
    elif pct <= EDGE_ZONE:
        state = "AT_LOWER"
    else:
        state = "INSIDE_UPPER_HALF" if pct >= 0.5 else "INSIDE_LOWER_HALF"

    bar_secs = TF_MINUTES.get(tf, 60) * 60
    last_ts = int(bars[last_idx].timestamp.timestamp())

    def point(k: int, fn) -> Dict[str, float]:
        if k <= last_idx:
            t = int(bars[k].timestamp.timestamp())
        else:
            t = last_ts + (k - last_idx) * bar_secs
        return {"time": t, "price": round(fn(k), 2)}

    ks = [start, last_idx, last_idx + PROJECTION_BARS]
    anchor_side_pts = [
        {"time": int(bars[i].timestamp.timestamp()), "price": round(p, 2), "idx": i}
        for i, p in ((idx1, p1), (idx2, p2))
    ]

    return {
        "tf": tf,
        "source": source,
        "direction": direction,
        "primary_side": side,
        "slope_per_bar": round(slope, 4),
        "width_now": round(chan_width_now, 2),
        "width_atr": round(chan_width_now / atr, 2),
        "atr": round(atr, 2),
        "tolerance": round(tol, 2),
        "touches": {"upper": up_t, "lower": lo_t},
        "breaches": {"upper": up_viol, "lower": lo_viol},
        "closes_inside_pct": round(inside_frac * 100, 1),
        "score": round(score, 2),
        "anchors": anchor_side_pts,
        "lines": {
            "upper": [point(k, upper_at) for k in ks],
            "mid": [point(k, lambda x: (upper_at(x) + lower_at(x)) / 2.0) for k in ks],
            "lower": [point(k, lower_at) for k in ks],
        },
        "now": {
            "price": round(last_close, 2),
            "upper": round(upper_now, 2),
            "mid": round(mid_now, 2),
            "lower": round(lower_now, 2),
            "position_pct": round(pct * 100, 1),
            "state": state,
        },
    }


def fit_channel(tf: str, bars: List[Bar]) -> Optional[Dict[str, Any]]:
    """Auto-fit the best channel on one timeframe from its swing pivots."""
    completed = [b for b in bars if b.shift >= 1] or list(bars)
    completed = completed[-LOOKBACK.get(tf, 150):]
    if len(completed) < 20:
        return None
    # Keep the forming bar (if any) so "now" reflects the latest price.
    forming = [b for b in bars if b.shift == 0]
    work = completed + forming[-1:]
    n_fit = len(completed)

    atr = _atr(completed)
    if atr <= 0:
        return None
    tol = 0.3 * atr

    strength = PIVOT_STRENGTH.get(tf, 3)
    pivots = find_pivots(completed, strength, strength)
    if sum(p["kind"] == "high" for p in pivots) < 2 or sum(p["kind"] == "low" for p in pivots) < 2:
        pivots = find_pivots(completed, max(2, strength - 1), max(2, strength - 1))

    best: Optional[Dict[str, Any]] = None
    for side, kind in (("upper", "high"), ("lower", "low")):
        side_pivots = [p for p in pivots if p["kind"] == kind][-8:]
        for i in range(len(side_pivots)):
            for j in range(i + 1, len(side_pivots)):
                a, b = side_pivots[i], side_pivots[j]
                if b["idx"] - a["idx"] < MIN_ANCHOR_GAP:
                    continue
                ch = _build_channel(
                    tf, work, side, a["idx"], a["price"], b["idx"], b["price"], atr, tol, n_fit, "AUTO"
                )
                if ch and (best is None or ch["score"] > best["score"]):
                    best = ch
    if best is not None:
        best["pivots"] = [
            {"time": p["time"], "price": round(p["price"], 2), "kind": p["kind"]} for p in pivots[-14:]
        ]
    return best


def manual_channel(tf: str, bars: List[Bar], override: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a channel from three user clicks: two on the primary rail, one on the opposite rail."""
    if len(bars) < 5:
        return None
    times = [int(b.timestamp.timestamp()) for b in bars]

    def nearest(t: float) -> int:
        return min(range(len(times)), key=lambda i: abs(times[i] - t))

    try:
        a1, a2, opp = override["a1"], override["a2"], override["opposite"]
        i1, i2 = nearest(float(a1["time"])), nearest(float(a2["time"]))
        p1, p2 = float(a1["price"]), float(a2["price"])
        io, po = nearest(float(opp["time"])), float(opp["price"])
    except (KeyError, TypeError, ValueError):
        return None
    if i1 == i2:
        return None
    if i1 > i2:
        i1, i2, p1, p2 = i2, i1, p2, p1

    slope = (p2 - p1) / (i2 - i1)
    primary_at_opp = p1 + slope * (io - i1)
    side = "upper" if po < primary_at_opp else "lower"
    atr = _atr([b for b in bars if b.shift >= 1] or bars)
    n_fit = len([b for b in bars if b.shift >= 1]) or len(bars)
    ch = _build_channel(tf, bars, side, i1, p1, i2, p2, atr, 0.3 * atr, n_fit, "MANUAL", (io, po))
    return ch


def _horizontal_levels(
    tf_bars: Dict[str, List[Bar]], tol: float, price: float
) -> List[Dict[str, Any]]:
    """Cluster swing pivots across D1/H4/H1 into horizontal support/resistance levels."""
    raw: List[Tuple[float, str, str]] = []
    for tf in ("D1", "H4", "H1"):
        bars = [b for b in tf_bars.get(tf, []) if b.shift >= 1][-LOOKBACK[tf]:]
        s = PIVOT_STRENGTH[tf]
        for p in find_pivots(bars, s, s):
            raw.append((p["price"], tf, p["kind"]))
    raw.sort(key=lambda r: r[0])

    clusters: List[List[Tuple[float, str, str]]] = []
    for item in raw:
        if clusters and item[0] - clusters[-1][-1][0] <= tol:
            clusters[-1].append(item)
        else:
            clusters.append([item])

    levels = []
    for c in clusters:
        if len(c) < 2:
            continue
        level = sum(x[0] for x in c) / len(c)
        tfs = sorted({x[1] for x in c}, key=TF_ORDER.index)
        levels.append({
            "price": round(level, 2),
            "touches": len(c),
            "timeframes": tfs,
            "type": "SUPPORT" if level < price else "RESISTANCE",
            "weight": round(sum(TF_WEIGHT[x[1]] for x in c) / 2.0, 2),
        })
    levels.sort(key=lambda l: abs(l["price"] - price))
    return levels[:8]


def _confluence_zones(
    channels: Dict[str, Dict[str, Any]], levels: List[Dict[str, Any]], tol: float, price: float
) -> List[Dict[str, Any]]:
    """Cluster channel rails and horizontal levels that land within `tol` of each other."""
    items: List[Dict[str, Any]] = []
    for tf, ch in channels.items():
        for rail in ("upper", "mid", "lower"):
            if rail == "mid":
                continue
            items.append({
                "price": ch["now"][rail],
                "label": f"{tf} {ch['direction'].lower()} channel {rail}",
                "role": "RESISTANCE" if rail == "upper" else "SUPPORT",
                "weight": TF_WEIGHT[tf],
                "kind": "channel",
            })
    for lv in levels:
        items.append({
            "price": lv["price"],
            "label": f"horizontal {lv['type'].lower()} ({'/'.join(lv['timeframes'])}, {lv['touches']} touches)",
            "role": lv["type"],
            "weight": lv["weight"],
            "kind": "horizontal",
        })
    items.sort(key=lambda i: i["price"])

    groups: List[List[Dict[str, Any]]] = []
    for it in items:
        if groups and it["price"] - groups[-1][0]["price"] <= tol:
            groups[-1].append(it)
        else:
            groups.append([it])

    zones = []
    for g in groups:
        if len(g) < 2:
            continue
        lo, hi = min(i["price"] for i in g), max(i["price"] for i in g)
        center = sum(i["price"] for i in g) / len(g)
        zones.append({
            "low": round(lo, 2),
            "high": round(hi, 2),
            "center": round(center, 2),
            "role": "SUPPORT" if center < price else "RESISTANCE",
            "score": round(sum(i["weight"] for i in g), 2),
            "distance": round(center - price, 2),
            "sources": [i["label"] for i in g],
        })
    zones.sort(key=lambda z: (-z["score"], abs(z["distance"])))
    return zones[:6]


def _alignment(channels: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    dirs = {tf: ch["direction"] for tf, ch in channels.items()}
    macro_dirs = [dirs[t] for t in ("D1", "H4") if t in dirs]
    if macro_dirs and len(set(macro_dirs)) == 1 and macro_dirs[0] != "HORIZONTAL":
        macro, macro_state = macro_dirs[0], "ALIGNED"
    elif macro_dirs and len(set(macro_dirs)) == 1:
        macro, macro_state = "HORIZONTAL", "RANGE"
    else:
        macro, macro_state = (dirs.get("D1") or dirs.get("H4") or "UNKNOWN"), "MIXED"

    relations = []
    ordered = [t for t in TF_ORDER if t in channels]
    for hi_tf, lo_tf in zip(ordered[:-1], ordered[1:]):
        hi, lo = channels[hi_tf], channels[lo_tf]
        same = hi["direction"] == lo["direction"]
        inside = hi["now"]["lower"] <= lo["now"]["mid"] <= hi["now"]["upper"]
        relations.append({
            "parent": hi_tf,
            "child": lo_tf,
            "relation": "WITH_TREND" if same else "COUNTER_TREND_PULLBACK",
            "child_inside_parent": inside,
        })
    return {"macro_direction": macro, "macro_state": macro_state, "directions": dirs, "relations": relations}


def _guide(
    price: float,
    channels: Dict[str, Dict[str, Any]],
    alignment: Dict[str, Any],
    zones: List[Dict[str, Any]],
) -> Dict[str, Any]:
    macro = alignment["macro_direction"]
    anchor_tf = "D1" if "D1" in channels else (next(iter(channels), None))
    steps: List[str] = []
    scenarios: List[Dict[str, str]] = []

    if anchor_tf is None:
        return {"steps": ["Not enough bars to fit a channel on any timeframe."], "scenarios": []}

    ch = channels[anchor_tf]
    now = ch["now"]
    steps.append(
        f"1. Map {anchor_tf}: {ch['direction']} channel, rails {now['lower']:.2f} - {now['upper']:.2f} "
        f"(width {ch['width_atr']} ATR, {ch['touches']['upper']} upper / {ch['touches']['lower']} lower touches)."
    )
    steps.append(
        f"2. Macro bias is {macro} ({alignment['macro_state']}); price sits at {now['position_pct']:.0f}% "
        f"of the {anchor_tf} channel ({now['state'].replace('_', ' ').lower()})."
    )
    inner = [t for t in TF_ORDER[1:] if t in channels]
    if inner:
        parts = []
        for t in inner:
            c = channels[t]
            parts.append(f"{t} {c['direction'].lower()} @ {c['now']['position_pct']:.0f}%")
        steps.append("3. Nest the lower timeframes inside it: " + "; ".join(parts) + ".")

    zone = None
    if zones:
        zone = min(zones, key=lambda z: abs(z["distance"]))
        steps.append(
            f"4. Key confluence: {zone['role'].lower()} zone {zone['low']:.2f} - {zone['high']:.2f} "
            f"(score {zone['score']}) built from {', '.join(zone['sources'])}."
        )

    tol = ch["tolerance"]
    lower, upper, mid = now["lower"], now["upper"], now["mid"]
    if macro == "DESCENDING":
        scenarios.append({
            "name": "Channel-floor bounce (counter-trend)",
            "trigger": f"Price tags {lower:.2f} support and a lower-timeframe (H1/M15) bullish structure shift prints.",
            "target": f"Channel mid {mid:.2f}, then upper rail {upper:.2f}.",
            "invalidation": f"Candle close below {lower - tol:.2f}.",
        })
        scenarios.append({
            "name": "Channel-floor break (trend continuation)",
            "trigger": f"Close below {lower - tol:.2f}, retest of the broken floor from below fails.",
            "target": "Next lower horizontal support / lower-timeframe channel floor.",
            "invalidation": f"Close back inside the channel above {lower:.2f}.",
        })
    elif macro == "ASCENDING":
        scenarios.append({
            "name": "Channel-floor pullback buy (with trend)",
            "trigger": f"Pullback holds {lower:.2f} and a lower-timeframe bullish structure shift prints.",
            "target": f"Channel mid {mid:.2f}, then upper rail {upper:.2f}.",
            "invalidation": f"Candle close below {lower - tol:.2f}.",
        })
        scenarios.append({
            "name": "Channel-roof rejection (counter-trend)",
            "trigger": f"Price tags {upper:.2f} resistance and a lower-timeframe bearish structure shift prints.",
            "target": f"Channel mid {mid:.2f}.",
            "invalidation": f"Candle close above {upper + tol:.2f}.",
        })
    else:
        scenarios.append({
            "name": "Range fade",
            "trigger": f"Fade rejections at {upper:.2f} / {lower:.2f}.",
            "target": f"Channel mid {mid:.2f}.",
            "invalidation": f"Close beyond either rail by {tol:.2f}.",
        })

    return {
        "steps": steps,
        "scenarios": scenarios,
        "focus_zone": zone,
        "how_to_map": [
            "Start on the highest timeframe (D1) and zoom out until the dominant swing structure is visible.",
            "Click two swing points on one rail (highs for a descending channel, lows for an ascending one).",
            "Click the most extreme wick on the opposite side - the parallel rail is cloned through it.",
            "Move down to H4, then H1, and repeat; the lower channels must nest inside or cross the parent.",
            "Mark where rails meet horizontal support/resistance - those confluence zones are the trade areas.",
        ],
    }


def map_multi_timeframe_channels(
    tf_bars: Dict[Any, List[Bar]],
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Fit channels on every timeframe and derive alignment, confluence zones and a guide."""
    named = {_tf_name(k): v for k, v in tf_bars.items() if v}
    overrides = overrides or {}

    channels: Dict[str, Dict[str, Any]] = {}
    for tf in TF_ORDER:
        bars = named.get(tf)
        if not bars:
            continue
        ch = None
        if tf in overrides:
            ch = manual_channel(tf, bars, overrides[tf])
        if ch is None:
            ch = fit_channel(tf, bars)
        if ch is not None:
            channels[tf] = ch

    ref = named.get("M1") or named.get("M5") or next(iter(named.values()), [])
    price = ref[-1].close if ref else 0.0

    tol_src = [named[t] for t in ("H4", "D1", "H1") if t in named]
    tol = 0.5 * _atr([b for b in tol_src[0] if b.shift >= 1]) if tol_src else 0.0

    levels = _horizontal_levels(named, tol, price) if tol > 0 else []
    zones = _confluence_zones(channels, levels, tol, price) if tol > 0 else []
    alignment = _alignment(channels) if channels else {
        "macro_direction": "UNKNOWN", "macro_state": "MIXED", "directions": {}, "relations": []
    }

    return {
        "price": round(price, 2),
        "confluence_tolerance": round(tol, 2),
        "channels": channels,
        "horizontal_levels": levels,
        "confluence_zones": zones,
        "alignment": alignment,
        "guide": _guide(price, channels, alignment, zones),
    }
