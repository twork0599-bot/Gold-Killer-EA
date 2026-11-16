# Gold-Killer-EA

Telegram-only gold market analysis bot. It runs on GitHub Actions; no personal PC or VPS is required.

## Data source and limitation
The bot now reads XAUS's free, keyless XAU/USD spot intraday series (up to 48 hours), sampled by that provider. This is an indicative international spot mid-price, **not** the live Exness MT5 XAUUSDm bid/ask feed or broker candles. Spread, quote timing and execution prices can differ. Verify every setup in MT5.

The feed's freshness state is checked. If it is not marked fresh, or there are too few observations, the bot stops without sending a signal.

## Features
- Builds approximate 15-minute and 1-hour bars from the provider's sampled spot observations.
- EMA, MACD, RSI(14), and ATR(14) checks.
- BUY, SELL, or HOLD Telegram alerts.
- ATR-based indicative entry, stop, and three targets for aligned setups.
- Scheduled every 15 minutes, plus manual workflow dispatch.

The rule-alignment score is a simple heuristic, not a win probability or backtested result. It does not implement BOS, CHoCH, FVG, order blocks, or liquidity sweeps. Since bars are reconstructed from sampled spot observations, they are not exchange/broker OHLC candles.

## Setup from Android
1. Open **Settings → Secrets and variables → Actions**.
2. Add `TELEGRAM_BOT_TOKEN` (BotFather token) and `TELEGRAM_CHAT_ID` (your private chat ID or group chat ID). Never put the token in source code or share it in chat.
3. Start the Telegram bot by opening its chat and pressing **Start**.
4. Open **Actions → Gold signal bot → Run workflow** to test.
5. Scheduled runs occur every 15 minutes, but GitHub may delay them. This is not tick-by-tick real time.

## Risk
The 2% line is a risk reminder only. Position size is not calculated because account balance and broker contract specifications are not configured. Verify prices and signals on Exness MT5 before acting. Educational use only; no trades are placed.
