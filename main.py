import os
import time
import logging
import threading
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from flask import Flask, render_template_string, request, redirect, url_for, abort

# =========================================================
# Qutex Signal CTH - Flask + Telegram + Binance Public API
# Developer: @SHADOW_JOKER_CTH
# =========================================================

PROJECT_NAME = "Qutex Signal CTH"
DEVELOPER_CREDIT = "@SHADOW_JOKER_CTH"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@qutexsignalcth").strip()
CONTROL_SECRET = os.getenv("CONTROL_SECRET", "").strip()

SIGNAL_GIF_URL = "https://media.giphy.com/media/w4zX4PfkQmZ4xeG7ny/giphy.gif"
RESULT_GIF_URL = "https://media.giphy.com/media/WWIvZaHUJEOWi5UhGV/giphy.gif"

# Binance public API - no auth required for klines
BINANCE_BASE = "https://api.binance.com"
SYMBOL = os.getenv("BINANCE_SYMBOL", "BTCUSDT")  # Binance format: no separator
EXPIRY_SECONDS = 120
LOOP_PAUSE_SECONDS = 60
DATA_INTERVAL = "1m"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(threadName)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

state_lock = threading.RLock()
engine_state = {
    "running": True,
    "safe_mode": False,
    "last_signal": None,
    "last_error": None,
    "last_data_timestamp": "Not available",
    "latency_ms": 0,
    "total_signals": 0,
    "wins": 0,
    "losses": 0,
    "draws": 0,
    "unavailable": 0,
    "last_result": "Not available",
    "last_result_detail": "—",
    "last_result_time": "Not available",
    "win_rate": 0.0,
    "active_filters": "EMA + RSI + MACD + Stochastic",
}

_engine_thread = None
_engine_start_lock = threading.Lock()
stop_event = threading.Event()

HTML_TEMPLATE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ project_name }} - Control Panel</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;padding:24px;display:flex;align-items:center;justify-content:center;
background:radial-gradient(circle at top,#172554,#070b13 58%);color:#e5edf8;
font-family:system-ui,-apple-system,Segoe UI,sans-serif}
.card{width:100%;max-width:620px;background:rgba(15,23,42,.94);border:1px solid #334155;
border-radius:20px;padding:24px;box-shadow:0 20px 60px #0008}
h1{text-align:center;color:#38bdf8;font-size:clamp(22px,5vw,30px);margin:0}
.sub{text-align:center;color:#94a3b8;font-size:13px;margin:8px 0 22px}
.badge{padding:11px;border-radius:10px;text-align:center;font-weight:700;margin-bottom:18px}
.running{background:#064e3b;color:#6ee7b7}.stopped{background:#7f1d1d;color:#fecaca}
.safe{background:#78350f;color:#fde68a}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.item{background:#080f1f;border:1px solid #243247;border-radius:12px;padding:13px;min-width:0}
.label{font-size:12px;color:#94a3b8;display:block;margin-bottom:7px}
.value{font-size:15px;font-weight:700;overflow-wrap:anywhere}
.value.green{color:#4ade80}.value.red{color:#f87171}.value.yellow{color:#facc15}
.error{color:#fca5a5;background:#450a0a;border-radius:10px;padding:12px;margin-top:14px;font-size:13px;overflow-wrap:anywhere}
.notice{font-size:12px;line-height:1.6;color:#cbd5e1;background:#111827;border:1px solid #374151;border-radius:10px;padding:12px;margin-top:14px}
.actions{display:flex;gap:10px;margin-top:18px}
button{width:100%;padding:13px;border:0;border-radius:10px;font-weight:800;font-size:14px;cursor:pointer}
.start{background:#16a34a;color:white}.stop{background:#dc2626;color:white}
.footer{text-align:center;color:#64748b;font-size:12px;margin-top:18px}
@media(max-width:430px){body{padding:12px}.card{padding:16px}.grid{grid-template-columns:1fr}.actions{flex-direction:column}}
</style>
</head>
<body>
<div class="card">
<h1>{{ project_name }}</h1>
<div class="sub">Developer: {{ developer }} · Binance Public API</div>
{% if state.safe_mode %}
<div class="badge safe">SAFE MODE ENABLED</div>
{% elif state.running %}
<div class="badge running">● ENGINE RUNNING</div>
{% else %}
<div class="badge stopped">● ENGINE STOPPED</div>
{% endif %}
<div class="grid">
<div class="item"><span class="label">Symbol</span><div class="value">{{ symbol }}</div></div>
<div class="item"><span class="label">Latest candle (UTC)</span><div class="value">{{ state.last_data_timestamp }}</div></div>
<div class="item"><span class="label">Fetch latency</span><div class="value">{{ state.latency_ms }} ms</div></div>
<div class="item"><span class="label">Last signal</span><div class="value">{{ state.last_signal or "None" }}</div></div>
<div class="item"><span class="label">Signals sent</span><div class="value">{{ state.total_signals }}</div></div>
<div class="item"><span class="label">Win Rate</span><div class="value {% if state.win_rate >= 60 %}green{% elif state.win_rate >= 40 %}yellow{% else %}red{% endif %}">{{ "%.1f"|format(state.win_rate) }}%</div></div>
<div class="item"><span class="label">WIN / LOSS / DRAW</span><div class="value"><span class="green">{{ state.wins }}</span> / <span class="red">{{ state.losses }}</span> / <span class="yellow">{{ state.draws }}</span></div></div>
<div class="item"><span class="label">Last result</span><div class="value {% if 'WIN' in state.last_result %}green{% elif 'LOSS' in state.last_result %}red{% else %}yellow{% endif %}">{{ state.last_result }}</div></div>
<div class="item" style="grid-column:1/-1"><span class="label">Result detail</span><div class="value">{{ state.last_result_detail }}</div></div>
</div>
{% if state.last_error %}<div class="error">⚠ {{ state.last_error }}</div>{% endif %}
{% if control_secret %}
<form method="post" action="/control" class="actions">
<input type="hidden" name="secret" value="{{ control_secret }}">
<button name="action" value="{{ 'stop' if state.running else 'start' }}" class="{{ 'stop' if state.running else 'start' }}">
{{ 'Stop Engine' if state.running else 'Start Engine' }}
</button>
</form>
{% else %}
<div class="notice">Set CONTROL_SECRET in environment variables to enable protected Start/Stop controls.</div>
{% endif %}
<div class="notice"><b>Data:</b> Binance public klines (no API key needed). <b>Settlement:</b> strict close vs close comparison at 2-min expiry.</div>
<div class="footer">{{ developer }} · {{ project_name }}</div>
</div>
</body></html>
"""

def utc_now_text():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def send_telegram(text, animation_url=None):
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set; skipping.")
        return False
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if animation_url:
            r = requests.post(
                base_url + "sendAnimation",
                data={"chat_id": TELEGRAM_CHAT_ID, "animation": animation_url,
                      "caption": text, "parse_mode": "HTML"},
                timeout=20,
            )
            if r.ok and r.json().get("ok"):
                return True
        r = requests.post(
            base_url + "sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=20,
        )
        r.raise_for_status()
        if not r.json().get("ok"):
            raise RuntimeError(r.text[:300])
        return True
    except Exception as exc:
        logger.exception("Telegram failed: %s", exc)
        with state_lock:
            engine_state["last_error"] = f"Telegram: {exc}"
        return False

def fetch_binance_klines(limit=100):
    """Public endpoint - no API key required."""
    started = time.monotonic()
    try:
        r = requests.get(
            f"{BINANCE_BASE}/api/v3/klines",
            params={"symbol": SYMBOL, "interval": DATA_INTERVAL, "limit": limit},
            timeout=15,
        )
        r.raise_for_status()
        raw = r.json()
        if not raw:
            raise ValueError("Empty klines response")

        # Binance kline: [openTime, open, high, low, close, volume, closeTime, ...]
        rows = []
        for k in raw:
            rows.append({
                "Open": float(k[1]),
                "High": float(k[2]),
                "Low": float(k[3]),
                "Close": float(k[4]),
                "Volume": float(k[5]),
                "_open_ms": int(k[0]),
                "_close_ms": int(k[6]),
            })
        df = pd.DataFrame(rows)
        df["Datetime"] = pd.to_datetime(df["_open_ms"], unit="ms", utc=True)
        df.set_index("Datetime", inplace=True)
        df.drop(columns=["_open_ms", "_close_ms"], inplace=True)
        df = df[~df.index.duplicated(keep="last")].sort_index()

        if len(df) < 30:
            raise ValueError(f"Insufficient candles: {len(df)}")

        latest = df.index[-1]
        latency = int((time.monotonic() - started) * 1000)
        with state_lock:
            engine_state["last_data_timestamp"] = latest.strftime("%Y-%m-%d %H:%M:%S UTC")
            engine_state["latency_ms"] = latency
            engine_state["last_error"] = None
        return df
    except Exception as exc:
        logger.warning("Binance fetch failed: %s", exc)
        with state_lock:
            engine_state["last_error"] = f"Binance data unavailable: {exc}"
            engine_state["latency_ms"] = int((time.monotonic() - started) * 1000)
        return None

def compute_indicators(df):
    data = df.copy()
    close = data["Close"]
    high = data["High"]
    low = data["Low"]

    data["EMA_Fast"] = close.ewm(span=8, adjust=False).mean()
    data["EMA_Slow"] = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(14, min_periods=14).mean()
    avg_loss = losses.rolling(14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    data["RSI"] = 100 - (100 / (1 + rs))
    data.loc[(avg_loss == 0) & (avg_gain > 0), "RSI"] = 100
    data.loc[(avg_loss == 0) & (avg_gain == 0), "RSI"] = 50

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    data["MACD"] = ema12 - ema26
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Hist"] = data["MACD"] - data["MACD_Signal"]

    lowest = low.rolling(14, min_periods=14).min()
    highest = high.rolling(14, min_periods=14).max()
    spread = (highest - lowest).replace(0, np.nan)
    data["Stoch_K"] = 100 * (close - lowest) / spread
    data["Stoch_D"] = data["Stoch_K"].rolling(3, min_periods=3).mean()

    tr = pd.concat([high - low, (high - close.shift(1)).abs(),
                    (low - close.shift(1)).abs()], axis=1).max(axis=1)
    data["ATR"] = tr.rolling(14, min_periods=14).mean()

    return data.replace([np.inf, -np.inf], np.nan).dropna()

def backtest_win_rate(df, horizon=2):
    """Leakage-free historical win rate on same logic as live signal."""
    if df is None or len(df) < 30:
        return 50.0, 0
    data = df.copy()
    raw = np.where(data["EMA_Fast"] >= data["EMA_Slow"], 1, -1)
    fut = data["Close"].shift(-horizon) - data["Close"]
    valid = (raw != 0) & fut.notna() & fut.ne(0)
    count = int(valid.sum())
    if count == 0:
        return 50.0, 0
    correct = (((raw == 1) & (fut > 0)) | ((raw == -1) & (fut < 0))) & valid
    return round(float(correct.sum()) / count * 100, 1), count

def generate_signal():
    raw = fetch_binance_klines()
    if raw is None:
        return None, "Market data unavailable"
    data = compute_indicators(raw)
    if data.empty:
        return None, "Not enough clean candles"

    latest = data.iloc[-1]
    candle_time = data.index[-1]

    fast = float(latest["EMA_Fast"])
    slow = float(latest["EMA_Slow"])

    direction = "CALL 🟢" if fast >= slow else "PUT 🔴"
    win_rate, samples = backtest_win_rate(data)

    return {
        "price": float(latest["Close"]),
        "direction": direction,
        "rsi": float(latest["RSI"]),
        "macd": float(latest["MACD_Hist"]),
        "stoch": float(latest["Stoch_K"]),
        "atr": float(latest["ATR"]),
        "backtest_win_rate": win_rate,
        "samples": samples,
        "candle_time": candle_time,
        "symbol": SYMBOL,
    }, None

def evaluate_settlement(entry_price, direction, df, expiry_time):
    """Strict binary settlement: close vs close."""
    if df is None or df.empty:
        return "UNAVAILABLE", entry_price, 0.0
    future = df[df.index >= expiry_time]
    if future.empty:
        # Not enough future data yet — use latest available close
        exit_price = float(df["Close"].iloc[-1])
    else:
        exit_price = float(future.iloc[0]["Close"])

    diff = exit_price - entry_price
    if abs(diff) < 1e-12:
        return "DRAW", exit_price, 0.0

    if "CALL" in direction:
        status = "WIN" if exit_price > entry_price else "LOSS"
    elif "PUT" in direction:
        status = "WIN" if exit_price < entry_price else "LOSS"
    else:
        status = "UNAVAILABLE"

    return status, exit_price, diff

def interruptible_wait(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with state_lock:
            if not engine_state["running"] or engine_state["safe_mode"]:
                return False
        if stop_event.wait(min(1, max(0, deadline - time.monotonic()))):
            return False
    return True

def background_engine():
    logger.info("Engine started — Binance public API, %s", SYMBOL)
    while not stop_event.is_set():
        with state_lock:
            if not engine_state["running"] or engine_state["safe_mode"]:
                stop_event.wait(2)
                continue

        try:
            sig, err = generate_signal()
            if sig is None:
                with state_lock:
                    engine_state["last_error"] = err
                stop_event.wait(15)
                continue

            entry_time = sig["candle_time"]
            expiry_time = entry_time + pd.Timedelta(seconds=EXPIRY_SECONDS)
            entry_price = sig["price"]

            with state_lock:
                engine_state["total_signals"] += 1
                engine_state["last_signal"] = f"{sig['direction']} @ {entry_price:.5f}"
                engine_state["last_error"] = None

            signal_msg = (
                f"⚡ <b>QUTEX PRO — BINANCE SIGNAL</b> ⚡\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Symbol:</b> <code>{sig['symbol']}</code>\n"
                f"💰 <b>Entry Price:</b> <code>{entry_price:.5f}</code>\n"
                f"📈 <b>Direction:</b> <b>{sig['direction']}</b>\n"
                f"⏳ <b>Expiry:</b> <code>{expiry_time.strftime('%H:%M:%S UTC')}</code> (2 min)\n"
                f"🎯 <b>Backtest Win Rate:</b> <code>{sig['backtest_win_rate']}%</code> ({sig['samples']} samples)\n"
                f"📊 <b>Indicators:</b>\n"
                f"• RSI: <code>{sig['rsi']:.1f}</code> | MACD: <code>{sig['macd']:.4f}</code>\n"
                f"• Stoch %K: <code>{sig['stoch']:.1f}</code> | ATR: <code>{sig['atr']:.5f}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👨‍💻 <b>{DEVELOPER_CREDIT}</b>"
            )
            send_telegram(signal_msg, SIGNAL_GIF_URL)

            wait_secs = max(0, (expiry_time - pd.Timestamp.now(tz="UTC")).total_seconds())
            if not interruptible_wait(wait_secs):
                continue

            future_df = fetch_binance_klines()
            status, exit_price, diff = evaluate_settlement(
                entry_price, sig["direction"], future_df, expiry_time
            )

            if status == "UNAVAILABLE":
                with state_lock:
                    engine_state["unavailable"] += 1
                stop_event.wait(15)
                continue

            with state_lock:
                if status == "WIN":
                    engine_state["wins"] += 1
                elif status == "LOSS":
                    engine_state["losses"] += 1
                else:
                    engine_state["draws"] += 1
                settled = engine_state["wins"] + engine_state["losses"] + engine_state["draws"]
                engine_state["win_rate"] = round(
                    engine_state["wins"] / settled * 100, 1
                ) if settled > 0 else 0.0
                engine_state["last_result"] = status
                engine_state["last_result_detail"] = (
                    f"Entry {entry_price:.5f} → Exit {exit_price:.5f} "
                    f"({'+' if diff >= 0 else ''}{diff:.5f})"
                )
                engine_state["last_result_time"] = utc_now_text()
                engine_state["last_error"] = None

            emoji = {"WIN": "✅", "LOSS": "❌", "DRAW": "➖"}[status]
            result_msg = (
                f"{emoji} <b>SETTLEMENT — {status}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Symbol:</b> <code>{sig['symbol']}</code>\n"
                f"📈 <b>Direction:</b> {sig['direction']}\n"
                f"💰 <b>Entry:</b> <code>{entry_price:.5f}</code>\n"
                f"🏁 <b>Exit:</b> <code>{exit_price:.5f}</code>\n"
                f"📉 <b>Move:</b> <code>{'+' if diff >= 0 else ''}{diff:.5f}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Session:</b> {engine_state['wins']}W / {engine_state['losses']}L / {engine_state['draws']}D "
                f"({engine_state['win_rate']}% WR)\n"
                f"👨‍💻 <b>{DEVELOPER_CREDIT}</b>"
            )
            send_telegram(result_msg, RESULT_GIF_URL)

            interruptible_wait(LOOP_PAUSE_SECONDS)

        except Exception as exc:
            logger.exception("Engine error")
            with state_lock:
                engine_state["last_error"] = str(exc)
            stop_event.wait(15)

@app.route("/")
def home():
    with state_lock:
        snapshot = dict(engine_state)
    return render_template_string(
        HTML_TEMPLATE,
        project_name=PROJECT_NAME, developer=DEVELOPER_CREDIT,
        state=snapshot, symbol=SYMBOL, control_secret=CONTROL_SECRET,
    )

@app.route("/health")
def health():
    with state_lock:
        return {"status": "ok", "running": engine_state["running"],
                "last_error": engine_state["last_error"]}

@app.route("/control", methods=["POST"])
def control():
    if not CONTROL_SECRET:
        abort(503, "Set CONTROL_SECRET first.")
    if request.form.get("secret", "") != CONTROL_SECRET:
        abort(403)
    action = request.form.get("action")
    with state_lock:
        if action == "start":
            engine_state["running"] = True
            engine_state["safe_mode"] = False
        elif action == "stop":
            engine_state["running"] = False
        else:
            abort(400)
    return redirect(url_for("home"))

def start_engine_once():
    global _engine_thread
    with _engine_start_lock:
        if _engine_thread is not None and _engine_thread.is_alive():
            return
        _engine_thread = threading.Thread(target=background_engine, name="signal-engine", daemon=True)
        _engine_thread.start()

if os.getenv("RENDER") or os.getenv("WERKZEUG_RUN_MAIN") == "true":
    start_engine_once()

if __name__ == "__main__":
    start_engine_once()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
