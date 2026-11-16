import os
import sys
from datetime import datetime, timezone

import pandas as pd
import requests
import yfinance as yf

SYMBOL = "GC=F"  # Yahoo gold-futures proxy, not Exness XAUUSDm.


def fetch_data(interval: str, period: str) -> pd.DataFrame:
    data = yf.download(SYMBOL, period=period, interval=interval,
                       auto_adjust=False, progress=False, threads=False)
    if data is None or data.empty:
        raise RuntimeError(f"No market data returned for {interval}.")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.columns = [str(c).title() for c in data.columns]
    needed = ["Open", "High", "Low", "Close"]
    if any(c not in data.columns for c in needed):
        raise RuntimeError("Market data is missing OHLC columns.")
    return data.dropna(subset=needed).copy()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    c = d["Close"]
    d["ema50"] = c.ewm(span=50, adjust=False).mean()
    d["ema200"] = c.ewm(span=200, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    d["rsi"] = 100 - 100 / (1 + rs)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    d["macd"] = macd
    d["macd_signal"] = macd.ewm(span=9, adjust=False).mean()
    prev = c.shift(1)
    tr = pd.concat([d["High"] - d["Low"],
                    (d["High"] - prev).abs(),
                    (d["Low"] - prev).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    return d.dropna()


def trend(row) -> str:
    if row["ema50"] > row["ema200"] and row["macd"] > row["macd_signal"]:
        return "BUY"
    if row["ema50"] < row["ema200"] and row["macd"] < row["macd_signal"]:
        return "SELL"
    return "HOLD"


def build_message() -> str:
    m15 = add_indicators(fetch_data("15m", "60d"))
    h1 = add_indicators(fetch_data("1h", "730d"))
    a, b = m15.iloc[-1], h1.iloc[-1]
    t15, t1h = trend(a), trend(b)
    price, atr, rsi = float(a["Close"]), float(a["atr"]), float(a["rsi"])
    signal = "HOLD"
    entry = sl = tp1 = tp2 = tp3 = None

    if t15 == t1h == "BUY" and 45 <= rsi <= 70:
        signal, entry = "BUY", price
        sl, tp1, tp2, tp3 = entry-1.5*atr, entry+1.5*atr, entry+2.5*atr, entry+3.5*atr
    elif t15 == t1h == "SELL" and 30 <= rsi <= 55:
        signal, entry = "SELL", price
        sl, tp1, tp2, tp3 = entry+1.5*atr, entry-1.5*atr, entry-2.5*atr, entry-3.5*atr

    score = 50 + (20 if t15 == t1h and t15 != "HOLD" else 0)
    if signal == "BUY" and 50 <= rsi <= 65 or signal == "SELL" and 35 <= rsi <= 50:
        score += 10
    if signal != "HOLD":
        score += 10
    score = min(score, 90)
    fmt = lambda x: f"{x:,.2f}" if x is not None else "—"
    lines = [
        "🥇 GOLD KILLER — MARKET ANALYSIS",
        f"Signal: {signal}",
        f"Reference price (GC=F): {fmt(price)}",
        f"15m trend: {t15} | 1h trend: {t1h}",
        f"RSI(14): {rsi:.1f} | ATR(14): {fmt(atr)}",
        f"Rule-alignment score: {score}/100 (not win probability)"
    ]
    if signal != "HOLD":
        lines += [f"Entry: {fmt(entry)}", f"Stop Loss: {fmt(sl)}",
                  f"TP1: {fmt(tp1)}", f"TP2: {fmt(tp2)}", f"TP3: {fmt(tp3)}",
                  "TP1 risk/reward: 1:1",
                  "Risk reminder: maximum 2% of account equity; calculate position size yourself."]
    else:
        lines.append("No aligned setup. Wait for confirmation.")
    lines += [
        f"Updated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
        "",
        "WARNING: GC=F is a Yahoo gold-futures proxy, NOT the live Exness XAUUSDm feed. Prices and timing may differ. Verify on your broker. Educational analysis only; no trades are placed."
    ]
    return "\n".join(lines)


def main():
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID GitHub Actions secret.")
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": build_message()}, timeout=25)
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API rejected message: {result}")
    print("Signal sent to Telegram.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
