import os
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

# Free public XAU/USD spot feed. Indicative mid-market, not Exness bid/ask.
API_URL = "https://xaus.com/api/v1/intraday"
HEADERS = {"User-Agent": "Gold-Killer-EA/1.0"}


def fetch_bars():
    response = requests.get(
        API_URL, params={"symbol": "xau", "hours": 48},
        headers=HEADERS, timeout=20
    )
    response.raise_for_status()
    payload = response.json()

    state = payload.get("data_state") or {}
    if state.get("status") != "fresh":
        raise RuntimeError(
            f"Gold feed is not fresh (status={state.get('status')}, "
            f"as_of={state.get('as_of')}). No signal sent."
        )

    points = payload.get("points") or []
    if len(points) < 100:
        raise RuntimeError(f"Not enough intraday observations: {len(points)}")

    df = pd.DataFrame(points)
    df["time"] = pd.to_datetime(df["t"], unit="s", utc=True)
    df["price"] = pd.to_numeric(df["p"], errors="coerce")
    df = df.dropna(subset=["time", "price"]).set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    bars = {}
    for interval in ("15min", "1h"):
        ohlc = df["price"].resample(interval).ohlc().dropna()
        if len(ohlc) < 35:
            raise RuntimeError(
                f"Not enough {interval} bars ({len(ohlc)}); wait for more feed history."
            )
        bars[interval] = ohlc
    return bars, state


def add_indicators(df, fast=20, slow=50):
    d = df.copy()
    c = d["close"]
    d["ema_fast"] = c.ewm(span=fast, adjust=False).mean()
    d["ema_slow"] = c.ewm(span=slow, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    d["rsi"] = 100 - 100 / (1 + rs)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    d["macd"] = macd
    d["macd_signal"] = macd.ewm(span=9, adjust=False).mean()
    prev = c.shift(1)
    tr = pd.concat([
        d["high"] - d["low"],
        (d["high"] - prev).abs(),
        (d["low"] - prev).abs()
    ], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    return d.dropna()


def trend(row):
    if row["ema_fast"] > row["ema_slow"] and row["macd"] > row["macd_signal"]:
        return "BUY"
    if row["ema_fast"] < row["ema_slow"] and row["macd"] < row["macd_signal"]:
        return "SELL"
    return "HOLD"


def build_message():
    bars, state = fetch_bars()
    m15 = add_indicators(bars["15min"], fast=20, slow=50)
    h1 = add_indicators(bars["1h"], fast=10, slow=20)
    a, b = m15.iloc[-1], h1.iloc[-1]
    t15, t1h = trend(a), trend(b)
    price, atr, rsi = float(a["close"]), float(a["atr"]), float(a["rsi"])

    signal = "HOLD"
    entry = sl = tp1 = tp2 = tp3 = None
    if t15 == t1h == "BUY" and 45 <= rsi <= 70:
        signal, entry = "BUY", price
        sl, tp1, tp2, tp3 = entry-1.5*atr, entry+1.5*atr, entry+2.5*atr, entry+3.5*atr
    elif t15 == t1h == "SELL" and 30 <= rsi <= 55:
        signal, entry = "SELL", price
        sl, tp1, tp2, tp3 = entry+1.5*atr, entry-1.5*atr, entry-2.5*atr, entry-3.5*atr

    score = 50 + (20 if t15 == t1h and t15 != "HOLD" else 0)
    if signal != "HOLD":
        score += 20
    score = min(score, 90)
    fmt = lambda x: f"{x:,.2f}" if x is not None else "—"
    lines = [
        "🥇 GOLD KILLER — XAU/USD SPOT ANALYSIS",
        f"Signal: {signal}",
        f"Reference spot price: {fmt(price)} USD/oz",
        f"15m trend: {t15} | 1h trend: {t1h}",
        f"RSI(14): {rsi:.1f} | ATR(14): {fmt(atr)}",
        f"Rule-alignment score: {score}/100 (not win probability)"
    ]
    if signal != "HOLD":
        lines += [
            f"Indicative entry: {fmt(entry)}",
            f"Indicative Stop Loss: {fmt(sl)}",
            f"TP1: {fmt(tp1)} | TP2: {fmt(tp2)} | TP3: {fmt(tp3)}",
            "TP1 risk/reward: 1:1",
            "Risk reminder: maximum 2% of account equity; calculate position size yourself."
        ]
    else:
        lines.append("No aligned setup. Wait for confirmation.")

    lines += [
        f"Feed status: {state.get('status')} | As of: {state.get('as_of')}",
        f"Bot checked: {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
        "",
        "DATA WARNING: Free XAUS XAU/USD indicative spot feed, sampled intraday. "
        "It is NOT the Exness MT5 XAUUSDm bid/ask or broker candles. "
        "Spread, execution price and timing may differ. Verify on MT5 before any decision. "
        "Educational analysis only; no trades are placed."
    ]
    return "\n".join(lines)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID GitHub Actions secret.")
    message = build_message()
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message}, timeout=25
    )
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
