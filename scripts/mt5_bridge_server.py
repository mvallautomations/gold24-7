"""
GOLD24-7 MetaTrader 5 Bridge Server
Runs on Windows host (where MT5 and MetaTrader5 Python DLLs execute).
Exposes live market rates, ticks, account metadata, and symbols over HTTP/JSON-RPC
to GOLD24-7 running in WSL2 / Linux.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MT5Bridge")

app = FastAPI(title="MT5 Windows Bridge Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TERMINAL_PATH = os.getenv("MT5_PATH", r"C:\Program Files\XM Global MT5\terminal64.exe")

TIMEFRAME_MAP = {
    "M1": 1,     # mt5.TIMEFRAME_M1
    "M5": 5,     # mt5.TIMEFRAME_M5
    "M15": 15,   # mt5.TIMEFRAME_M15
    "M30": 30,   # mt5.TIMEFRAME_M30
    "H1": 16385, # mt5.TIMEFRAME_H1
    "H4": 16388, # mt5.TIMEFRAME_H4
    "D1": 16408, # mt5.TIMEFRAME_D1
    "W1": 32769, # mt5.TIMEFRAME_W1
    "MN1": 49153,# mt5.TIMEFRAME_MN1
}


def ensure_mt5_connected() -> bool:
    if mt5 is None:
        logger.error("MetaTrader5 library is not installed in this Python environment.")
        return False

    info = mt5.terminal_info()
    if info is not None and getattr(info, "connected", False):
        return True

    logger.info(f"Connecting to MT5 via: {TERMINAL_PATH}")
    if os.path.exists(TERMINAL_PATH):
        ok = mt5.initialize(path=TERMINAL_PATH)
    else:
        ok = mt5.initialize()

    if not ok:
        err = mt5.last_error()
        logger.warning(f"mt5.initialize() failed: {err}")
    return bool(ok)


@app.get("/health")
def health():
    connected = ensure_mt5_connected()
    acc = mt5.account_info() if connected and mt5 else None
    return {
        "status": "ok" if connected else "offline",
        "connected": connected,
        "login": getattr(acc, "login", None),
        "server": getattr(acc, "server", None),
        "company": getattr(acc, "company", None),
        "leverage": getattr(acc, "leverage", None),
        "currency": getattr(acc, "currency", None),
        "balance": getattr(acc, "balance", None),
        "equity": getattr(acc, "equity", None),
    }


@app.get("/api/symbols")
def get_symbols():
    if not ensure_mt5_connected():
        return JSONResponse({"error": "MT5 not connected"}, status_code=503)
    symbols = mt5.symbols_get()
    return {"symbols": [s.name for s in symbols] if symbols else []}


@app.get("/api/rates")
def get_rates_get(symbol: str = "GOLD", timeframe: str = "M1", count: int = 100):
    if not ensure_mt5_connected():
        return JSONResponse({"error": "MT5 not connected"}, status_code=503)

    tf_const = TIMEFRAME_MAP.get(timeframe.upper(), 1)
    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
    if rates is None or len(rates) == 0:
        return {"rates": []}

    parsed = []
    for r in rates:
        parsed.append({
            "time": int(r[0]),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "tick_volume": float(r[5]),
            "spread": int(r[6]),
            "real_volume": float(r[7]),
        })
    return {"rates": parsed}


@app.post("/rpc")
async def rpc_endpoint(req: Request):
    body = await req.json()
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id", 1)

    if not ensure_mt5_connected():
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "MT5 terminal not connected"},
            "id": req_id
        }, status_code=503)

    if method == "symbols_get":
        symbols = mt5.symbols_get()
        names = [s.name for s in symbols] if symbols else []
        return {"jsonrpc": "2.0", "result": {"symbols": names}, "id": req_id}

    elif method == "rates_get":
        symbol = params.get("symbol", "GOLD")
        tf_str = params.get("timeframe", "M1").upper()
        count = int(params.get("count", 100))
        tf_const = TIMEFRAME_MAP.get(tf_str, 1)

        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
        if rates is None or len(rates) == 0:
            return {"jsonrpc": "2.0", "result": {"rates": []}, "id": req_id}

        parsed = []
        for r in rates:
            parsed.append({
                "time": int(r[0]),
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4]),
                "tick_volume": float(r[5]),
                "spread": int(r[6]),
                "real_volume": float(r[7]),
            })
        return {"jsonrpc": "2.0", "result": {"rates": parsed}, "id": req_id}

    elif method == "account_info":
        acc = mt5.account_info()
        data = acc._asdict() if acc else {}
        return {"jsonrpc": "2.0", "result": data, "id": req_id}

    elif method == "terminal_info":
        term = mt5.terminal_info()
        data = term._asdict() if term else {}
        return {"jsonrpc": "2.0", "result": data, "id": req_id}

    elif method == "tick_get":
        symbol = params.get("symbol", "GOLD")
        tick = mt5.symbol_info_tick(symbol)
        data = tick._asdict() if tick else {}
        return {"jsonrpc": "2.0", "result": data, "id": req_id}

    elif method == "positions_get":
        symbol = params.get("symbol")
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        parsed = [p._asdict() for p in positions] if positions else []
        return {"jsonrpc": "2.0", "result": {"positions": parsed}, "id": req_id}

    elif method == "history_deals_get":
        import datetime as dt
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        now = datetime.now(timezone.utc)
        d_from = datetime.fromtimestamp(date_from, tz=timezone.utc) if isinstance(date_from, (int, float)) else (datetime.fromisoformat(str(date_from)) if date_from else now - dt.timedelta(days=365))
        d_to = datetime.fromtimestamp(date_to, tz=timezone.utc) if isinstance(date_to, (int, float)) else (datetime.fromisoformat(str(date_to)) if date_to else now + dt.timedelta(days=1))
        # MT5 accepts naive or aware datetimes
        deals = mt5.history_deals_get(d_from, d_to)
        parsed = [d._asdict() for d in deals] if deals else []
        return {"jsonrpc": "2.0", "result": {"deals": parsed}, "id": req_id}

    elif method == "history_orders_get":
        import datetime as dt
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        now = datetime.now(timezone.utc)
        d_from = datetime.fromtimestamp(date_from, tz=timezone.utc) if isinstance(date_from, (int, float)) else (datetime.fromisoformat(str(date_from)) if date_from else now - dt.timedelta(days=365))
        d_to = datetime.fromtimestamp(date_to, tz=timezone.utc) if isinstance(date_to, (int, float)) else (datetime.fromisoformat(str(date_to)) if date_to else now + dt.timedelta(days=1))
        orders = mt5.history_orders_get(d_from, d_to)
        parsed = [o._asdict() for o in orders] if orders else []
        return {"jsonrpc": "2.0", "result": {"orders": parsed}, "id": req_id}

    elif method == "symbol_info":
        symbol = params.get("symbol", "GOLD#")
        info = mt5.symbol_info(symbol)
        data = info._asdict() if info else {}
        return {"jsonrpc": "2.0", "result": data, "id": req_id}

    elif method == "position_modify":
        ticket = params.get("ticket")
        sl = params.get("sl")
        tp = params.get("tp")
        positions = mt5.positions_get(ticket=int(ticket)) if ticket else None
        if not positions:
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": f"Position {ticket} not found"}, "id": req_id}
        pos = positions[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "symbol": pos.symbol,
            "sl": float(sl) if sl is not None else float(pos.sl),
            "tp": float(tp) if tp is not None else float(pos.tp),
        }
        res = mt5.order_send(request)
        if res is None:
            err = mt5.last_error()
            return {"jsonrpc": "2.0", "error": {"code": -32002, "message": f"order_send failed: {err}"}, "id": req_id}
        return {"jsonrpc": "2.0", "result": res._asdict(), "id": req_id}

    elif method == "position_close":
        ticket = params.get("ticket")
        positions = mt5.positions_get(ticket=int(ticket)) if ticket else None
        if not positions:
            return {"jsonrpc": "2.0", "error": {"code": -32001, "message": f"Position {ticket} not found"}, "id": req_id}
        pos = positions[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        if not tick:
            return {"jsonrpc": "2.0", "error": {"code": -32003, "message": f"Cannot get tick for {pos.symbol}"}, "id": req_id}

        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

        s_info = mt5.symbol_info(pos.symbol)
        filling_type = mt5.ORDER_FILLING_IOC
        if s_info:
            if s_info.filling_mode & 2:
                filling_type = mt5.ORDER_FILLING_IOC
            elif s_info.filling_mode & 1:
                filling_type = mt5.ORDER_FILLING_FOK
            else:
                filling_type = mt5.ORDER_FILLING_RETURN

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": int(ticket),
            "symbol": pos.symbol,
            "volume": float(pos.volume),
            "type": order_type,
            "price": float(price),
            "deviation": int(params.get("deviation", 20)),
            "magic": int(pos.magic),
            "comment": str(params.get("comment", "mitigation_close")),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        res = mt5.order_send(request)
        if res is None:
            err = mt5.last_error()
            return {"jsonrpc": "2.0", "error": {"code": -32002, "message": f"order_send failed: {err}"}, "id": req_id}
        return {"jsonrpc": "2.0", "result": res._asdict(), "id": req_id}

    elif method == "order_send":
        req = params.get("request", {})
        if "type_filling" not in req and "symbol" in req:
            s_info = mt5.symbol_info(req["symbol"])
            if s_info:
                if s_info.filling_mode & 2:
                    req["type_filling"] = mt5.ORDER_FILLING_IOC
                elif s_info.filling_mode & 1:
                    req["type_filling"] = mt5.ORDER_FILLING_FOK
                else:
                    req["type_filling"] = mt5.ORDER_FILLING_RETURN
        res = mt5.order_send(req)
        if res is None:
            err = mt5.last_error()
            return {"jsonrpc": "2.0", "error": {"code": -32002, "message": f"order_send failed: {err}"}, "id": req_id}
        return {"jsonrpc": "2.0", "result": res._asdict(), "id": req_id}

    return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method {method} not found"}, "id": req_id}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8082))
    print(f"Starting MT5 Bridge Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
