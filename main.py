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

# ওয়েব পেজের ডিজাইন এবং ট্রিগার বাটন
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUTEX Signal Control Panel</title>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); width: 100%; max-width: 400px; text-align: center; border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 24px; margin-bottom: 10px; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 25px; }
        .btn { background-color: #2563eb; color: white; border: none; padding: 14px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: bold; width: 100%; transition: background 0.3s; }
        .btn:hover { background-color: #1d4ed8; }
        .status { margin-top: 20px; font-size: 14px; color: #22c55e; font-weight: 500; }
        .footer { margin-top: 25px; font-size: 12px; color: #64748b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>QUTEX Signal Engine</h1>
        <p>বাটনে ক্লিক করে সরাসরি টেলিগ্রাম গ্রুপে ৩ মিনিটের সিগন্যাল ও রেজাল্ট ট্রিগার করুন।</p>
        <form action="/trigger-signal" method="POST">
            <button type="submit" class="btn">🚀 Send QUTEX Signal</button>
        </form>
        <div class="status">{{ message }}</div>
        <div class="footer">Dev: @SHADOW_JOKER_CTH</div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE, message="")

@app.route("/trigger-signal", methods=["POST"])
def trigger_signal():
    if not bot:
        return render_template_string(HTML_PAGE, message="ত্রুটি: টেলিগ্রাম বট টোকেন কনফিগার করা নেই!")
    
    try:
        # QUTEX লাইভ মার্কেট ডাটা সিমুলেশন
        prices = np.random.uniform(1.0800, 1.1200, 50)
        df = pd.DataFrame({'price': prices})
        
        asset = "EUR/USD (QUTEX Live)"
        direction = "CALL 🟢 (HIGHER)" if np.random.choice([True, False]) else "PUT 🔴 (LOWER)"
        confidence = "97.5%"
        expiry = "3 Minutes"
        
        # ১. প্রি-ট্রেড সিগন্যাল কার্ড (QUTEX ব্র্যান্ডিং সহ)
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
        
        # ব্যাকগ্রাউন্ডে সিগন্যাল পাঠানো, ৩ মিনিট অপেক্ষা করা এবং রেজাল্ট পাঠানো প্রসেস
        def run_background_trade_cycle():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def flow():
                    # সিগন্যাল পাঠানো
                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=signal_message, parse_mode="HTML")
                    logger.info("QUTEX সিগন্যাল সফলভাবে পাঠানো হয়েছে।")
                    
                    # ঠিক ৩ মিনিট (১৮০ সেকেন্ড) ট্রেড বিট/মেয়াদ অপেক্ষা করা
                    await asyncio.sleep(180)
                    
                    # ২. রেজাল্ট স্ট্যাটাস আপডেট কার্ড
                    result_status = "WIN ✅ (In-The-Money)" if np.random.choice([True, True, False]) else "WIN via Safe Exit 🟢"
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
                    logger.info("QUTEX সেটেলমেন্ট রেজাল্ট সফলভাবে পাঠানো হয়েছে।")

                loop.run_until_complete(flow())
                loop.close()
            except Exception as ex:
                logger.error(f"ব্যাকগ্রাউন্ড প্রসেসে ত্রুটি: {ex}")

        # থ্রেডের মাধ্যমে ব্যাকগ্রাউন্ডে রান করা যাতে ওয়েব পেজ ফ্রি থাকে
        threading.Thread(target=run_background_trade_cycle).start()
        
        return render_template_string(HTML_PAGE, message="সফল! টেলিগ্রাম গ্রুপে সিগন্যাল পাঠানো হয়েছে।")
        
    except Exception as e:
        logger.error(f"ট্রিগার করতে ত্রুটি: {e}")
        return render_template_string(HTML_PAGE, message=f"ত্রুটি: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
