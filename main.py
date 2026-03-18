from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
import time
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

signals = deque(maxlen=100)
subscribers = []

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XAU/USD Live Dashboard</title>
<style>
  :root { --bg:#0d0d0d;--bg2:#141414;--bg3:#1a1a1a;--border:rgba(255,255,255,0.08);--text:#e8e8e8;--muted:#666;--green:#1D9E75;--red:#E24B4A;--blue:#378ADD;--amber:#BA7517;--green-bg:rgba(29,158,117,0.12);--red-bg:rgba(226,75,74,0.12);--blue-bg:rgba(55,138,221,0.12); }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--text);font-family:'Courier New',monospace;font-size:13px;}
  #app{display:grid;grid-template-rows:48px 1fr;height:100vh;}
  #topbar{background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px;}
  .tb-left{display:flex;align-items:center;gap:16px;}
  .asset{font-size:16px;font-weight:700;letter-spacing:1px;}
  .live-dot{width:8px;height:8px;border-radius:50%;background:var(--red);animation:pulse 1.5s infinite;}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
  .price-big{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;}
  .delta{font-size:12px;padding:2px 8px;border-radius:3px;}
  .delta.up{background:var(--green-bg);color:var(--green);}
  .delta.dn{background:var(--red-bg);color:var(--red);}
  .conn-badge{font-size:11px;padding:3px 10px;border-radius:3px;border:1px solid;}
  .conn-badge.connected{border-color:var(--green);color:var(--green);}
  .conn-badge.disconnected{border-color:var(--red);color:var(--red);}
  #main{display:grid;grid-template-columns:1fr 300px;overflow:hidden;}
  #chartArea{display:flex;flex-direction:column;padding:16px;gap:12px;overflow-y:auto;}
  .metrics-row{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;}
  .metric{background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:10px 14px;}
  .metric-lbl{font-size:10px;color:var(--muted);margin-bottom:4px;letter-spacing:0.5px;text-transform:uppercase;}
  .metric-val{font-size:16px;font-weight:700;font-variant-numeric:tabular-nums;}
  canvas{background:var(--bg2);border:1px solid var(--border);border-radius:6px;width:100%;}
  .patterns-row{display:flex;gap:8px;flex-wrap:wrap;}
  .pattern-badge{font-size:11px;padding:4px 10px;border-radius:3px;border:1px solid;font-weight:600;}
  .pattern-badge.bull{border-color:var(--green);color:var(--green);background:var(--green-bg);}
  .pattern-badge.bear{border-color:var(--red);color:var(--red);background:var(--red-bg);}
  .pattern-badge.neutral{border-color:var(--amber);color:var(--amber);background:rgba(186,117,23,0.1);}
  #side{background:var(--bg2);border-left:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
  .side-section{border-bottom:1px solid var(--border);padding:12px 14px;}
  .side-title{font-size:10px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;}
  .sr-item{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);}
  .sr-item:last-child{border-bottom:none;}
  .sr-lbl{font-size:11px;color:var(--muted);}
  .sr-val{font-weight:700;font-variant-numeric:tabular-nums;}
  .sr-res{color:var(--red);}.sr-sup{color:var(--green);}.sr-entry{color:var(--blue);}
  #feed{flex:1;overflow-y:auto;}
  .feed-item{padding:10px 14px;border-bottom:1px solid var(--border);cursor:pointer;transition:background 0.15s;}
  .feed-item:hover{background:var(--bg3);}
  .feed-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
  .feed-signal{font-size:11px;font-weight:700;padding:2px 7px;border-radius:3px;}
  .feed-signal.BUY{background:var(--green-bg);color:var(--green);}
  .feed-signal.SELL{background:var(--red-bg);color:var(--red);}
  .feed-signal.NEUTRAL{background:rgba(186,117,23,0.1);color:var(--amber);}
  .feed-time{font-size:10px;color:var(--muted);}
  .feed-msg{font-size:11px;color:var(--muted);}
  .feed-price{font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;}
  .empty-feed{padding:20px 14px;color:var(--muted);font-size:11px;text-align:center;}
  .rsi-bar-wrap{height:4px;background:var(--bg3);border-radius:2px;margin-top:6px;overflow:hidden;}
  .rsi-bar{height:100%;border-radius:2px;transition:width 0.4s;}
  @media(max-width:700px){#main{grid-template-columns:1fr;}#side{display:none;}.metrics-row{grid-template-columns:repeat(3,1fr);}}
</style>
</head>
<body>
<div id="app">
  <div id="topbar">
    <div class="tb-left">
      <div class="live-dot" id="liveDot"></div>
      <div class="asset">XAU/USD</div>
      <span style="color:var(--muted);font-size:11px;">5m · Capital.com</span>
    </div>
    <div class="tb-left">
      <div class="price-big" id="livePrice">—</div>
      <div class="delta" id="liveDelta">—</div>
    </div>
    <div class="conn-badge disconnected" id="connBadge">DISCONNECTED</div>
  </div>
  <div id="main">
    <div id="chartArea">
      <div class="metrics-row">
        <div class="metric"><div class="metric-lbl">Open</div><div class="metric-val" id="mO">—</div></div>
        <div class="metric"><div class="metric-lbl">High</div><div class="metric-val" style="color:var(--green)" id="mH">—</div></div>
        <div class="metric"><div class="metric-lbl">Low</div><div class="metric-val" style="color:var(--red)" id="mL">—</div></div>
        <div class="metric"><div class="metric-lbl">RSI</div><div class="metric-val" id="mRsi">—</div>
          <div class="rsi-bar-wrap"><div class="rsi-bar" id="rsiBar" style="width:50%;background:var(--amber)"></div></div>
        </div>
        <div class="metric"><div class="metric-lbl">Signaux</div><div class="metric-val" id="mCount">0</div></div>
      </div>
      <div class="patterns-row" id="patternBadges">
        <span class="pattern-badge neutral">En attente de donnees...</span>
      </div>
      <canvas id="priceChart" height="280"></canvas>
      <div style="color:var(--muted);font-size:11px;padding:4px 0;">
        Mise a jour : <span id="lastUpdate">—</span> &nbsp;·&nbsp; <span id="signalCount">0</span> signal(s)
      </div>
    </div>
    <div id="side">
      <div class="side-section">
        <div class="side-title">Serveur Webhook</div>
        <input id="urlInp" type="text" style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);font-family:monospace;font-size:11px;padding:6px 8px;border-radius:4px;outline:none;" placeholder="https://...onrender.com" />
        <button onclick="connectSSE()" style="margin-top:8px;width:100%;padding:7px;background:var(--blue-bg);border:1px solid var(--blue);color:var(--blue);font-family:monospace;font-size:12px;border-radius:4px;cursor:pointer;">Connecter</button>
      </div>
      <div class="side-section">
        <div class="side-title">Niveaux S/R</div>
        <div class="sr-item"><span class="sr-lbl">Resistance</span><span class="sr-val sr-res" id="srRes1">—</span></div>
        <div class="sr-item"><span class="sr-lbl">Resistance</span><span class="sr-val sr-res" id="srRes2">—</span></div>
        <div class="sr-item"><span class="sr-lbl">Prix actuel</span><span class="sr-val" id="srCur">—</span></div>
        <div class="sr-item"><span class="sr-lbl">Support</span><span class="sr-val sr-sup" id="srSup1">—</span></div>
        <div class="sr-item"><span class="sr-lbl">Entree long</span><span class="sr-val sr-entry">4994.88</span></div>
      </div>
      <div class="side-title" style="padding:12px 14px 0;">Flux alertes live</div>
      <div id="feed"><div class="empty-feed">En attente de signaux TradingView...</div></div>
    </div>
  </div>
</div>
<script>
let es=null,signalCount=0,priceHistory=[],basePrice=null;
const canvas=document.getElementById('priceChart');
const ctx=canvas.getContext('2d');
function resizeCanvas(){canvas.width=canvas.offsetWidth*window.devicePixelRatio;canvas.height=280*window.devicePixelRatio;ctx.scale(window.devicePixelRatio,window.devicePixelRatio);drawChart();}
window.addEventListener('resize',resizeCanvas);setTimeout(resizeCanvas,100);
function drawChart(){
  const W=canvas.offsetWidth,H=280;
  ctx.clearRect(0,0,W,H);
  if(priceHistory.length<2){ctx.fillStyle='rgba(255,255,255,0.15)';ctx.font='13px Courier New';ctx.textAlign='center';ctx.fillText('En attente de donnees...',W/2,H/2);return;}
  const prices=priceHistory.map(p=>p.price),times=priceHistory.map(p=>p.time);
  const minP=Math.min(...prices)-2,maxP=Math.max(...prices)+2;
  const P={t:20,r:55,b:25,l:10},cW=W-P.l-P.r,cH=H-P.t-P.b;
  const toY=p=>P.t+(maxP-p)/(maxP-minP)*cH,toX=i=>P.l+(i/(priceHistory.length-1))*cW;
  ctx.strokeStyle='rgba(255,255,255,0.05)';ctx.lineWidth=0.5;
  for(let i=0;i<=5;i++){const p=minP+(maxP-minP)*i/5,y=toY(p);ctx.beginPath();ctx.moveTo(P.l,y);ctx.lineTo(W-P.r,y);ctx.stroke();ctx.fillStyle='rgba(255,255,255,0.35)';ctx.font='10px Courier New';ctx.textAlign='left';ctx.fillText(p.toFixed(1),W-P.r+4,y+3);}
  const isUp=prices[prices.length-1]>=prices[0];
  const grad=ctx.createLinearGradient(0,0,0,H);
  grad.addColorStop(0,isUp?'rgba(29,158,117,0.3)':'rgba(226,75,74,0.3)');grad.addColorStop(1,'rgba(0,0,0,0)');
  ctx.beginPath();priceHistory.forEach((p,i)=>{const x=toX(i),y=toY(p.price);i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.lineTo(toX(priceHistory.length-1),H);ctx.lineTo(P.l,H);ctx.closePath();ctx.fillStyle=grad;ctx.fill();
  ctx.beginPath();priceHistory.forEach((p,i)=>{const x=toX(i),y=toY(p.price);i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.strokeStyle=isUp?'#1D9E75':'#E24B4A';ctx.lineWidth=1.5;ctx.stroke();
  priceHistory.forEach((p,i)=>{if(p.signal==='BUY'||p.signal==='SELL'){ctx.beginPath();ctx.arc(toX(i),toY(p.price),4,0,Math.PI*2);ctx.fillStyle=p.signal==='BUY'?'#1D9E75':'#E24B4A';ctx.fill();}});
  ctx.fillStyle='rgba(255,255,255,0.25)';ctx.font='10px Courier New';ctx.textAlign='center';
  const step=Math.max(1,Math.floor(priceHistory.length/5));
  for(let i=0;i<priceHistory.length;i+=step)ctx.fillText(times[i],toX(i),H-8);
}
function onSignal(data){
  signalCount++;
  document.getElementById('mCount').textContent=signalCount;
  document.getElementById('signalCount').textContent=signalCount;
  document.getElementById('lastUpdate').textContent=new Date().toLocaleTimeString('fr-FR');
  if(data.price){
    if(!basePrice)basePrice=data.price;
    const delta=data.price-basePrice,pct=(delta/basePrice*100).toFixed(2),isUp=delta>=0;
    document.getElementById('livePrice').textContent=data.price.toFixed(2);
    const dEl=document.getElementById('liveDelta');
    dEl.textContent=(isUp?'+':'')+delta.toFixed(2)+' ('+pct+'%)';
    dEl.className='delta '+(isUp?'up':'dn');
    document.getElementById('srCur').textContent=data.price.toFixed(2);
    priceHistory.push({price:data.price,time:new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}),signal:data.signal});
    if(priceHistory.length>80)priceHistory.shift();
    drawChart();
  }
  if(data.ohlcv){
    if(data.ohlcv.open)document.getElementById('mO').textContent=data.ohlcv.open.toFixed(2);
    if(data.ohlcv.high)document.getElementById('mH').textContent=data.ohlcv.high.toFixed(2);
    if(data.ohlcv.low)document.getElementById('mL').textContent=data.ohlcv.low.toFixed(2);
  }
  if(data.rsi){const rsi=data.rsi;document.getElementById('mRsi').textContent=rsi.toFixed(1);const bar=document.getElementById('rsiBar');bar.style.width=rsi+'%';bar.style.background=rsi<30?'#1D9E75':rsi>70?'#E24B4A':'#BA7517';}
  if(data.sr){if(data.sr.resistance)document.getElementById('srRes1').textContent=data.sr.resistance.toFixed(2);if(data.sr.support)document.getElementById('srSup1').textContent=data.sr.support.toFixed(2);}
  if(data.pattern){
    const badges=document.getElementById('patternBadges');
    const sig=data.signal||'NEUTRAL',cls=sig==='BUY'?'bull':sig==='SELL'?'bear':'neutral';
    const badge=document.createElement('span');badge.className='pattern-badge '+cls;badge.textContent=data.pattern;
    if(badges.querySelector('.neutral')?.textContent.includes('attente'))badges.innerHTML='';
    badges.prepend(badge);if(badges.children.length>6)badges.removeChild(badges.lastChild);
  }
  const feed=document.getElementById('feed');
  if(feed.querySelector('.empty-feed'))feed.innerHTML='';
  const item=document.createElement('div');item.className='feed-item';
  const sig=data.signal||'NEUTRAL';
  item.innerHTML='<div class="feed-top"><span class="feed-signal '+sig+'">'+sig+'</span><span class="feed-time">'+new Date().toLocaleTimeString('fr-FR')+'</span></div><div style="display:flex;justify-content:space-between;margin-top:2px;"><span class="feed-msg">'+(data.pattern||data.message||'—')+'</span><span class="feed-price">'+(data.price?data.price.toFixed(2):'—')+'</span></div>';
  feed.prepend(item);if(feed.children.length>50)feed.removeChild(feed.lastChild);
}
function connectSSE(){
  if(es){es.close();es=null;}
  const url=(document.getElementById('urlInp').value.trim()||window.location.origin).replace(/\\/$/,'');
  const badge=document.getElementById('connBadge');
  badge.textContent='CONNECTING...';badge.className='conn-badge disconnected';
  es=new EventSource(url+'/stream');
  es.onopen=()=>{badge.textContent='LIVE';badge.className='conn-badge connected';document.getElementById('liveDot').style.background='#1D9E75';};
  es.onmessage=(e)=>{try{onSignal(JSON.parse(e.data));}catch(err){}};
  es.onerror=()=>{badge.textContent='DISCONNECTED';badge.className='conn-badge disconnected';document.getElementById('liveDot').style.background='#E24B4A';};
}
drawChart();
window.addEventListener('load',()=>{document.getElementById('urlInp').value=window.location.origin;connectSSE();});
</script>
</body>
</html>"""


class TVAlert(BaseModel):
    symbol: Optional[str] = "XAUUSD"
    timeframe: Optional[str] = "5m"
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    pattern: Optional[str] = None
    signal: Optional[str] = None
    sr_resistance: Optional[float] = None
    sr_support: Optional[float] = None
    rsi: Optional[float] = None
    message: Optional[str] = None
    secret: Optional[str] = None


def classify_signal(alert: TVAlert) -> dict:
    signal_type = (alert.signal or "NEUTRAL").upper()
    color = {"BUY": "green", "SELL": "red"}.get(signal_type, "gray")
    return {
        "id": int(time.time() * 1000),
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": alert.symbol,
        "timeframe": alert.timeframe,
        "price": alert.close,
        "ohlcv": {"open": alert.open, "high": alert.high, "low": alert.low, "close": alert.close, "volume": alert.volume},
        "pattern": alert.pattern,
        "signal": signal_type,
        "color": color,
        "sr": {"resistance": alert.sr_resistance, "support": alert.sr_support},
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


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=DASHBOARD_HTML)


@app.post("/webhook")
async def receive_webhook(alert: TVAlert, request: Request):
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
    queue = asyncio.Queue()
    subscribers.append(queue)

    async def event_generator():
        for s in list(signals)[:5]:
            yield f"data: {json.dumps(s)}\n\n"
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            if queue in subscribers:
                subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/health")
async def health():
    return {"status": "ok", "signals_count": len(signals), "subscribers": len(subscribers)}
