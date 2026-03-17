from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

signals = []
MAX_SIGNALS = 100

@app.route('/')
def index():
    return jsonify({"status": "XAU/USD Webhook Server running", "signals": len(signals)})

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    TradingView envoie un JSON comme :
    {
      "type": "pattern" | "signal",
      "pattern": "Bullish Engulfing",
      "action": "BUY" | "SELL",
      "price": 5016.13,
      "sl": 4994.88,
      "tp": 5038.00,
      "rr": 2.1,
      "time": "2024-03-17T13:46:01Z"
    }
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON received"}), 400

        signal = {
            "id": len(signals) + 1,
            "type": data.get("type", "signal"),
            "pattern": data.get("pattern", ""),
            "action": data.get("action", ""),
            "price": float(data.get("price", 0)),
            "sl": float(data.get("sl", 0)),
            "tp": float(data.get("tp", 0)),
            "rr": float(data.get("rr", 0)),
            "time": data.get("time", datetime.datetime.utcnow().isoformat()),
            "received_at": datetime.datetime.utcnow().isoformat()
        }

        signals.append(signal)
        if len(signals) > MAX_SIGNALS:
            signals.pop(0)

        # Broadcast to all connected dashboard clients via WebSocket
        socketio.emit('new_signal', signal)

        print(f"[SIGNAL] {signal['action']} @ {signal['price']} | {signal['pattern']}")
        return jsonify({"status": "ok", "signal_id": signal["id"]}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/signals', methods=['GET'])
def get_signals():
    return jsonify({"signals": list(reversed(signals)), "count": len(signals)})

@app.route('/signals/clear', methods=['POST'])
def clear_signals():
    signals.clear()
    return jsonify({"status": "cleared"})

@socketio.on('connect')
def on_connect():
    print(f"[WS] Client connected")
    # Send last 10 signals to newly connected client
    emit('history', {"signals": list(reversed(signals[-10:]))})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
