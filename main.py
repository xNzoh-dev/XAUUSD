from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import time
import os
from datetime import datetime
from collections import deque

app = FastAPI(title="XAU/USD TradingView Webhook")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (last 100 signals)
signals = deque(maxlen=100)
subscribers = []

# --- Models ---
class TVAlert(BaseModel):
    symbol: Optional[str] = "XAUUSD"
    timeframe: Optional[str] = "5m"
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    pattern: Optional[str] = None
    signal: Optional[str] = None       # "BUY" | "SELL" | "NEUTRAL"
    sr_resistance: Optional[float] = None
    sr_support: Optional[float] = None
    rsi: Optional[float] = None
    message: Optional[str] = None
    secret: Optional[str] = None

# --- Helpers ---
def classify_signal(alert: TVAlert) -> dict:
    signal_type = (alert.signal or "NEUTRAL").upper()
    color = {"BUY": "green", "SELL": "red"}.get(signal_type, "gray")
    return {
        "id": int(time.time() * 1000),
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": alert.symbol,
        "timeframe": alert.timeframe,
        "price": alert.close,
        "ohlcv": {
            "open": alert.open, "high": alert.high,
            "low": alert.low, "close": alert.close, "volume": alert.volume
        },
        "pattern": alert.pattern,
        "signal": signal_type,
        "color": color,
        "sr": {
            "resistance": alert.sr_resistance,
            "support": alert.sr_support
        },
        "rsi": alert.rsi,
        "message": alert.message or f"{signal_type} signal on {alert.symbol} @ {alert.close}"
    }

async def broadcast(data: dict):
    dead = []
    for q in subscribers:
        try:
            await q.put(data)
        except Exception:
            dead.append(q)
    for q in dead:
        subscribers.remove(q)

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def root():
    """Sert le dashboard HTML directement depuis le serveur."""
    import os
    dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
    try:
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h2>dashboard.html introuvable</h2>", status_code=404)

@app.post("/webhook")
async def receive_webhook(alert: TVAlert, request: Request):
    # Optional secret validation
    SECRET = "xauusd_secret_2024"
    if alert.secret and alert.secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    signal = classify_signal(alert)
    signals.appendleft(signal)
    await broadcast(signal)
    return {"status": "ok", "signal_id": signal["id"]}

@app.get("/signals")
async def get_signals(limit: int = 20):
    return {"signals": list(signals)[:limit], "total": len(signals)}

@app.get("/stream")
async def stream_signals():
    """SSE endpoint — dashboard connects here for live updates."""
    queue = asyncio.Queue()
    subscribers.append(queue)

    async def event_generator():
        # Send last 5 signals on connect
        for s in list(signals)[:5]:
            yield f"data: {json.dumps(s)}\n\n"
        # Then stream live
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.get("/health")
async def health():
    return {"status": "ok", "signals_count": len(signals), "subscribers": len(subscribers)}
