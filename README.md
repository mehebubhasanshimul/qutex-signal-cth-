# Qutex Signal CTH

Professional automated multi-indicator trading signal and analytics engine for EUR/USD, developed by `@SHADOW_JOKER_CTH`.

## Features
- **Strict Market Validation:** Real-time data fetching with freshness checks and zero synthetic generation.
- **Multi-Indicator Confluence:** EMA (8, 21), RSI (14), MACD (12, 26, 9), Stochastic (%K, %D), and ATR (14).
- **Leakage-Free Backtesting:** Real out-of-sample historical validation without future data leakage.
- **Flask Control Panel:** Secure web dashboard with real-time status and Start/Stop controls.
- **Telegram Integration:** Automated 2-minute expiry signals and settlement result tracking.

## Deployment on Render
1. Create a new Web Service on Render and link your GitHub repository.
2. Set the Environment Variables:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token from @BotFather.
   - `TELEGRAM_CHAT_ID`: `@qutexsignalcth`
3. Use the provided `render.yaml` configuration. Ensure `workers 1` is configured to avoid worker state conflicts.
