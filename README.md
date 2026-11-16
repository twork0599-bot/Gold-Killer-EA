# Gold-Killer-EA

Telegram-only gold market analysis bot. It runs on GitHub Actions; no personal PC or VPS is required.

## Data limitation
This starter reads Yahoo Finance `GC=F` (COMEX gold futures) as a proxy. It is **not** the live Exness `XAUUSDm` feed; prices and timing can differ. The bot does not place trades.

## Features
- 15-minute and 1-hour trend alignment.
- EMA 50/200, MACD, RSI(14), and ATR(14).
- BUY, SELL, or HOLD Telegram alerts.
- ATR-based entry reference, stop, and three targets for aligned setups.
- Scheduled every 15 minutes, plus manual workflow dispatch.

The rule-alignment score is a simple heuristic, not a win probability or backtested result. BOS, CHoCH, FVG, order blocks, and liquidity sweeps are not implemented in this starter.

## Setup from Android
1. Open **Settings → Secrets and variables → Actions → New repository secret**.
2. Add `TELEGRAM_BOT_TOKEN` (BotFather token) and `TELEGRAM_CHAT_ID` (your private chat ID or group chat ID). Never put the token in source code or share it in chat.
3. Start the Telegram bot by opening its chat and pressing **Start**.
4. Open **Actions → Gold signal bot → Run workflow** to test.
5. Scheduled runs occur every 15 minutes, but GitHub may delay them. This is not tick-by-tick real time.

## Risk
The 2% line is a risk reminder only. Position size is not calculated because account balance and broker contract specifications are not configured. Verify signals on Exness before acting. Educational use only.
