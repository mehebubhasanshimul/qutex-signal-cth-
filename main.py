import os
import logging
import asyncio
import threading
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, redirect, url_for
from telegram import Bot
from telegram.error import TelegramError
import pandas as pd
import numpy as np
import requests

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Credentials & Constants
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@qutexsignalcth")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
DEVELOPER_CREDIT = "@SHADOW_JOKER_CTH"
PROJECT_NAME = "Qutex Signal CTH"

bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

# Thread-Safe Global State
engine_state = {
    "running": True,
    "last_signal": None,
    "last_error": None,
    "last_data_timestamp": "Not Available",
    "active_signals_count": 0,
    "total_signals": 0,
    "wins": 0,
    "losses": 0,
    "draws": 0
}
state_lock = threading.Lock()

# Professional Dark Dashboard HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_name }} - Control Panel</title>
    <style>
        body { background-color: #0b0f19; color: #f1f5f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 35px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); width: 100%; max-width: 480px; border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 22px; margin-bottom: 5px; text-align: center; }
        .subtitle { text-align: center; color: #94a3b8; font-size: 13px; margin-bottom: 20px; }
        .status-badge { padding: 8px 16px; border-radius: 6px; font-weight: bold; display: block; text-align: center; margin-bottom: 20px; font-size: 13px; }
        .running { background-color: #065f46; color: #34d399; }
        .stopped { background-color: #7f1d1d; color: #fca5a5; }
        .info-box { background: #0f172a; padding: 15px; border-radius: 8px; font-size: 13px; margin-bottom: 20px; border: 1px solid #1e293b; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .info-row:last-child { margin-bottom: 0; }
        .label { color: #94a3b8; }
        .value { color: #f8fafc; font-weight: 600; }
        .error-text { color: #f87171; font-size: 12px; margin-top: 10px; text-align: center; word-break: break-all; }
        .btn-group { display: flex; gap: 12px; }
        .btn { flex: 1; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; font-size: 14px; transition: 0.2s; }
        .btn-start { background-color: #16a34a; color: white; }
        .btn-start:hover { background-color: #15803d; }
        .btn-stop { background-color: #dc2626; color: white; }
        .btn-stop:hover { background-color: #b91c1c; }
        .footer { margin-top: 20px; text-align: center; font-size: 11px; color: #64748b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>{{ project_name }}</h1>
        <div class="subtitle">Developer: {{ developer }}</div>
        
        <div class="status-badge {{ 'running' if state.running else 'stopped' }}">
            {{ '🟢 Engine Status: RUNNING (RapidAPI Connected)' if state.running else '🔴 Engine Status: STOPPED' }}
        </div>
        
        <div class="info-box">
            <div class="info-row"><span class="label">Last Data Time:</span><span class="value">{{ state.last_data_timestamp }}</span></div>
            <div class="info-row"><span class="label">Last Signal:</span><span class="value">{{ state.last_signal or 'None' }}</span></div>
            <div class="info-row"><span class="label">Total Signals:</span><span class="value">{{ state.total_signals }}</span></div>
            <div class="info-row"><span class="label">Wins / Losses / Draws:</span><span class="value">{{ state.wins }} / {{ state.losses }} / {{ state.draws }}</span></div>
        </div>
        
        {% if state.last_error %}
        <div class="error-text">⚠️ Last Error: {{ state.last_error }}</div>
        {% endif %}
        
        <form method="POST" action="/control" class="btn-group">
            <input type="hidden" name="action" value="{{ 'stop' if state.running else 'start' }}">
            <button type="submit" class="btn {{ 'btn-stop' if state.running else 'btn-start' }}">
                {{ 'Stop Engine' if state.running else 'Start Engine' }}
            </button>
        </form>
        
        <div class="footer">Disclaimer: Binary options trading involves substantial risk. No guaranteed accuracy.</div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    with state_lock:
        return render_template_string(HTML_TEMPLATE, project_name=PROJECT_NAME, developer=DEVELOPER_CREDIT, state=engine_state)

@app.route("/control", methods=["POST"])
def control():
    action = request.form.get("action")
    with state_lock:
        if action == "start":
            engine_state["running"] = True
            logger.info("Engine started via Web Control Panel.")
        elif action == "stop":
            engine_state["running"] = False
            logger.info("Engine stopped via Web Control Panel.")
    return redirect(url_for('home'))

def fetch_market_data():
    """
    RapidAPI YH Finance Chart Endpoint ব্যবহার করে EUR/USD লাইভ ডেটা ফেচ করা।
    """
    try:
        if not RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY is missing in environment variables.")

        url = "https://yh-finance.p.rapidapi.com/stock/v2/get-chart"
        querystring = {"symbol": "EURUSD=X", "interval": "1m", "range": "1d"}
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "yh-finance.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        if response.status_code != 200:
            raise ValueError(f"RapidAPI HTTP Error: {response.status_code}")

        res_json = response.json()
        result = res_json.get("chart", {}).get("result", [])
        if not result:
            raise ValueError("Invalid chart result structure from RapidAPI.")

        data_res = result[0]
        timestamps = data_res.get("timestamp", [])
        indicators = data_res.get("indicators", {}).get("quote", [{}])[0]

        if not timestamps or not indicators:
            raise ValueError("Missing timestamps or quote indicators in API response.")

        df = pd.DataFrame({
            "Open": indicators.get("open", []),
            "High": indicators.get("high", []),
            "Low": indicators.get("low", []),
            "Close": indicators.get("close", []),
            "Volume": indicators.get("volume", [0] * len(timestamps))
        }, index=pd.to_datetime(timestamps, unit="s", utc=True))

        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
        df = df[~df.index.duplicated(keep='last')]
        df = df.sort_index()

        if len(df) < 30:
            raise ValueError(f"Insufficient candles ({len(df)}). Need at least 30.")

        latest_time = df.index[-1]
        with state_lock:
            engine_state["last_data_timestamp"] = str(latest_time)
            engine_state["last_error"] = None

        return df
    except Exception as e:
        err_msg = str(e)
        logger.error(f"RapidAPI fetch error: {err_msg}")
        with state_lock:
            engine_state["last_error"] = err_msg
        return None

def compute_indicators(df):
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    df['EMA_Fast'] = close.ewm(span=8, adjust=False).mean()
    df['EMA_Slow'] = close.ewm(span=21, adjust=False).mean()
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    low14 = low.rolling(window=14).min()
    high14 = high.rolling(window=14).max()
    df['Stoch_K'] = 100 * ((close - low14) / (high14 - low14 + 1e-10))
    df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    return df.dropna()

def leakage_free_backtest(df):
    if len(df) < 30:
        return 0.0, 0, 0, 0
        
    df_bt = df.copy()
    df_bt['Signal'] = 0
    
    buy_cond = (df_bt['EMA_Fast'] > df_bt['EMA_Slow']) & (df_bt['RSI'] < 45) & (df_bt['MACD_Hist'] > 0) & (df_bt['Stoch_K'] < 30)
    sell_cond = (df_bt['EMA_Fast'] < df_bt['EMA_Slow']) & (df_bt['RSI'] > 55) & (df_bt['MACD_Hist'] < 0) & (df_bt['Stoch_K'] > 70)
    
    df_bt.loc[buy_cond, 'Signal'] = 1
    df_bt.loc[sell_cond, 'Signal'] = -1
    
    df_bt['Future_Return'] = df_bt['Close'].shift(-2) - df_bt['Close']
    
    executed = df_bt[df_bt['Signal'] != 0].dropna(subset=['Future_Return'])
    total_samples = len(executed)
    
    if total_samples == 0:
        return 0.0, 0, 0, 0
        
    executed['Win'] = ((executed['Signal'] == 1) & (executed['Future_Return'] > 0)) | \
                      ((executed['Signal'] == -1) & (executed['Future_Return'] < 0))
                      
    wins = executed['Win'].sum()
    losses = total_samples - wins
    win_rate = (wins / total_samples) * 100
    
    return round(win_rate, 1), total_samples, int(wins), int(losses)

def generate_signal():
    df = fetch_market_data()
    if df is None:
        return None, "RapidAPI Data Unavailable or Key Missing"
        
    df = compute_indicators(df)
    if df.empty:
        return None, "Insufficient Clean Data after indicators"
        
    win_rate, sample_count, bt_wins, bt_losses = leakage_free_backtest(df)
    
    latest = df.iloc[-1]
    price = float(latest['Close'])
    rsi = float(latest['RSI'])
    macd_hist = float(latest['MACD_Hist'])
    stoch_k = float(latest['Stoch_K'])
    atr = float(latest['ATR'])
    ema_fast = float(latest['EMA_Fast'])
    ema_slow = float(latest['EMA_Slow'])
    
    score = 0
    if ema_fast > ema_slow: score += 2
    else: score -= 2
    
    if rsi < 45: score += 2
    elif rsi > 55: score -= 2
    
    if macd_hist > 0: score += 2
    else: score -= 2
    
    if stoch_k < 35: score += 2
    elif stoch_k > 65: score -= 2
    
    if score >= 4:
        direction = "CALL 🟢 (HIGHER)"
    elif score <= -4:
        direction = "PUT 🔴 (LOWER)"
    else:
        return None, f"NO SIGNAL (Score: {score}/4 - Confluence not met)"
        
    analysis_text = (
        f"📊 <b>Technical Indicators:</b>\n"
        f"• RSI: <code>{rsi:.1f}</code> | MACD Hist: <code>{macd_hist:.4f}</code>\n"
        f"• Stoch %K: <code>{stoch_k:.1f}</code> | ATR: <code>{atr:.5f}</code>\n"
        f"📈 <b>Out-of-Sample Backtest:</b> <code>{win_rate}%</code> (Wins: {bt_wins}, Losses: {bt_losses}, Samples: {sample_count})"
    )
    
    return {
        "price": price,
        "direction": direction,
        "confidence": "Not calibrated (Live Out-of-Sample)",
        "analysis": analysis_text
    }, None

def evaluate_settlement(entry_price, direction, df_future):
    try:
        if df_future is None or df_future.empty:
            return "UNKNOWN"
        exit_price = float(df_future['Close'].iloc[-1])
        
        if "CALL" in direction:
            if exit_price > entry_price: return "WIN"
            elif exit_price < entry_price: return "LOSS"
            else: return "DRAW"
        elif "PUT" in direction:
            if exit_price < entry_price: return "WIN"
            elif exit_price > entry_price: return "LOSS"
            else: return "DRAW"
    except Exception:
        pass
    return "UNKNOWN"

def background_engine():
    global engine_state
    logger.info("Background Signal Engine started with RapidAPI.")
    
    import time
    while True:
        try:
            with state_lock:
                is_running = engine_state["running"]
                
            if not is_running:
                time.sleep(5)
                continue
                
            signal_data, error_reason = generate_signal()
            
            if signal_data is None:
                logger.info(f"Signal skipped: {error_reason}")
                with state_lock:
                    engine_state["last_error"] = error_reason
                time.sleep(60)
                continue
                
            asset = "EUR/USD (RapidAPI Live)"
            expiry = "2 Minutes"
            
            with state_lock:
                engine_state["total_signals"] += 1
                engine_state["last_signal"] = f"{signal_data['direction']} at {signal_data['price']:.5f}"
                engine_state["last_error"] = None
                
            signal_msg = (
                f"⚡ <b>{PROJECT_NAME} SIGNAL</b> ⚡\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Asset:</b> <code>{asset}</code>\n"
                f"💰 <b>Entry Price:</b> <code>{signal_data['price']:.5f}</code>\n"
                f"📈 <b>Prediction:</b> <b>{signal_data['direction']}</b>\n"
                f"⏳ <b>Expiry Time:</b> <code>{expiry}</code>\n"
                f"🎯 <b>Confidence:</b> <code>{signal_data['confidence']}</code>\n"
                f"{signal_data['analysis']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👨‍💻 <b>Developer:</b> <b>{DEVELOPER_CREDIT}</b>\n"
                f"⚠️ <i>Note: Quotex official settlement price may vary due to spread.</i>"
            )
            
            if bot and TELEGRAM_CHAT_ID:
                try:
                    async def send_msg():
                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=signal_msg, parse_mode="HTML")
                    asyncio.run(send_msg())
                except TelegramError as te:
                    logger.error(f"Telegram API Error: {te}")
                    with state_lock:
                        engine_state["last_error"] = f"Telegram Error: {te}"
            
            # ২ মিনিট (১২০ সেকেন্ড) অপেক্ষা
            elapsed = 0
            while elapsed < 120:
                with state_lock:
                    if not engine_running:
                        break
                time.sleep(1)
                elapsed += 1
                
            with state_lock:
                if not engine_running:
                    continue
                    
            future_df = fetch_market_data()
            result_status = evaluate_settlement(signal_data['price'], signal_data['direction'], future_df)
            
            with state_lock:
                if result_status == "WIN":
                    engine_state["wins"] += 1
                    res_display = "WIN ✅"
                elif result_status == "LOSS":
                    engine_state["losses"] += 1
                    res_display = "LOSS ❌"
                elif result_status == "DRAW":
                    engine_state["draws"] += 1
                    res_display = "DRAW ➖"
                else:
                    res_display = "UNKNOWN ⚠️"
                    
            result_msg = (
                f"📊 <b>SETTLEMENT RESULT</b> 📊\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏷 <b>Asset:</b> <code>{asset}</code>\n"
                f"🏁 <b>Status:</b> <b>{res_display}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👨‍💻 <b>{DEVELOPER_CREDIT}</b>"
            )
            
            if bot and TELEGRAM_CHAT_ID and result_status != "UNKNOWN":
                try:
                    async def send_res():
                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=result_msg, parse_mode="HTML")
                    asyncio.run(send_res())
                except Exception as ex:
                    logger.error(f"Result notification error: {ex}")
                    
            time.sleep(30)
            
        except Exception as ex:
            logger.error(f"Critical error in background engine: {ex}")
            with state_lock:
                engine_state["last_error"] = str(ex)
            time.sleep(15)

if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or os.environ.get("RENDER"):
    engine_thread = threading.Thread(target=background_engine, daemon=True)
    engine_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
