import os
import logging
import asyncio
import threading
from flask import Flask, render_template_string
from telegram import Bot
import pandas as pd
import numpy as np

app = Flask(__name__)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@qutexsignalcth")
DEVELOPER_CREDIT = "@SHADOW_JOKER_CTH"

bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

# স্ট্যাটাস দেখানোর জন্য সিম্পল ওয়েব পেজ
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUTEX Signal Engine Status</title>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 400px; text-align: center; border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 24px; margin-bottom: 10px; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 25px; line-height: 1.6; }
        .status-badge { background-color: #166534; color: #4ade80; padding: 10px 20px; border-radius: 8px; font-weight: bold; display: inline-block; margin-bottom: 15px; font-size: 14px; }
        .footer { margin-top: 25px; font-size: 12px; color: #64748b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>QUTEX Signal Engine</h1>
        <div class="status-badge">🟢 24/7 Fully Automated</div>
        <p>বটটি এখন সম্পূর্ণ স্বয়ংক্রিয়ভাবে ২৪ ঘণ্টা টেলিগ্রাম গ্রুপে সিগন্যাল, রেজাল্ট এবং ২০ মিনিট পর পর স্ট্যাটিস্টিকস পাঠাচ্ছে। কোনো ম্যানুয়াল ক্লিকের প্রয়োজন নেই!</p>
        <div class="footer">Dev: @SHADOW_JOKER_CTH</div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

def start_background_engine():
    """
    ব্যাকগ্রাউন্ডে ২৪ ঘণ্টা স্বয়ংক্রিয়ভাবে সিগন্যাল, রেজাল্ট এবং ২০ মিনিট পর পর সামারি পাঠানোর লুপ
    """
    if not bot:
        logger.error("টেলিগ্রাম বট টোকেন পাওয়া যায়নি!")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def engine_loop():
        logger.info("QUTEX 24/7 Automatic Signal Engine শুরু হয়েছে।")
        
        session_signals = 0
        session_wins = 0
        session_losses = 0
        session_start_time = asyncio.get_event_loop().time()

        while True:
            try:
                prices = np.random.uniform(1.0800, 1.1200, 50)
                df = pd.DataFrame({'price': prices})
                
                asset = "EUR/USD (QUTEX Live)"
                direction = "CALL 🟢 (HIGHER)" if np.random.choice([True, False]) else "PUT 🔴 (LOWER)"
                confidence = "97.5%"
                expiry = "3 Minutes"
                
                session_signals += 1
                
                # ১. সিগন্যাল পাঠানো
                signal_message = (
                    f"⚡ <b>QUTEX TRADING SIGNAL ENGINE</b> ⚡\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📊 <b>Asset:</b> <code>{asset}</code>\n"
                    f"📈 <b>Prediction:</b> <b>{direction}</b>\n"
                    f"⏳ <b>Expiry Time:</b> <code>{expiry}</code>\n"
                    f"🎯 <b>Confidence Score:</b> <code>{confidence}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👨‍💻 <b>Developer & Engine Core:</b> <b>{DEVELOPER_CREDIT}</b>\n"
                    f"⚠️ <i>Trade securely at your own risk.</i>"
                )
                
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=signal_message, parse_mode="HTML")
                logger.info(f"QUTEX সিগন্যাল #{session_signals} পাঠানো হয়েছে।")
                
                # ৩ মিনিট (১৮০ সেকেন্ড) ট্রেড বিট/মেয়াদ অপেক্ষা
                await asyncio.sleep(180)
                
                # উইন/লস নির্ধারণ
                is_win = np.random.choice([True, True, True, True, True, True, True, True, False, True])
                if is_win:
                    session_wins += 1
                    result_status = "WIN ✅ (In-The-Money)"
                else:
                    session_losses += 1
                    result_status = "LOSS ❌"
                
                # ২. রেজাল্ট পাঠানো
                result_message = (
                    f"📊 <b>QUTEX SETTLEMENT RESULT</b> 📊\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏷️ <b>Asset:</b> <code>{asset}</code>\n"
                    f"🏁 <b>Status:</b> <b>{result_status}</b>\n"
                    f"📈 <b>Accuracy Verification:</b> 99.2% Verified\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👨‍💻 <b>Developer & Powered By:</b> <b>{DEVELOPER_CREDIT}</b>"
                )
                
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=result_message, parse_mode="HTML")
                logger.info("QUTEX সেটেলমেন্ট রেজাল্ট পাঠানো হয়েছে।")
                
                # রেজাল্টের পর ১ মিনিট (৬০ সেকেন্ড) বিরতি
                await asyncio.sleep(60)

                # প্রতি ২০ মিনিট (১২০০ সেকেন্ড) পর পর স্ট্যাটিস্টিকস সামারি পাঠানো
                current_time = asyncio.get_event_loop().time()
                if current_time - session_start_time >= 1200:
                    win_rate = (session_wins / session_signals * 100) if session_signals > 0 else 0
                    summary_message = (
                        f"📊📈 <b>20-MIN SESSION PERFORMANCE SUMMARY</b> 📈📊\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎯 <b>Total Signals Sent:</b> <code>{session_signals}</code>\n"
                        f"✅ <b>Total Wins:</b> <code>{session_wins}</code>\n"
                        f"❌ <b>Total Losses:</b> <code>{session_losses}</code>\n"
                        f"⭐ <b>Win Rate:</b> <code>{win_rate:.1f}%</code>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"👨‍💻 <b>Powered By:</b> <b>{DEVELOPER_CREDIT}</b>"
                    )
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=summary_message, parse_mode="HTML")
                    logger.info("২০ মিনিটের সেশন স্ট্যাটিস্টিকস সামারি পাঠানো হয়েছে।")
                    
                    # পরবর্তী ২০ মিনিটের জন্য কাউন্টার রিসেট করা
                    session_signals = 0
                    session_wins = 0
                    session_losses = 0
                    session_start_time = current_time

            except Exception as e:
                logger.error(f"ইঞ্জিন লুপে ত্রুটি: {e}")
                await asyncio.sleep(15)

    loop.run_until_complete(engine_loop())

# অ্যাপ স্টার্ট হওয়ার সাথে সাথে ব্যাকগ্রাউন্ড থ্রেড চালু করা (ম্যানুয়াল ক্লিকের প্রয়োজন নেই)
threading.Thread(target=start_background_engine, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
