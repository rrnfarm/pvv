#!/usr/bin/env python3
"""Run the PVV risk-range model on one or more tickers.

Examples
  python3 run_pvv.py SPY QQQ NVDA            # downloads ~1 year of daily bars with yfinance
  python3 run_pvv.py BTC-USD --crypto        # 24/7 markets use the crypto settings
  python3 run_pvv.py --csv mydata.csv        # CSV with columns date,open,high,low,close,volume (oldest first)

Needs: pip install pandas numpy yfinance   (yfinance only for downloads)
Output per ticker: last close, TRADE range (buy - sell), TREND (Bullish/Bearish), trend line,
the three trend checks, volatility, and where the close sits inside the range.
"""
import sys, argparse
import pandas as pd
from pvv import pvv


def load_yf(ticker):
    import yfinance as yf
    h = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
    if h.empty:
        raise ValueError(f"no data for {ticker}")
    h = h.reset_index()
    return pd.DataFrame({"date": h["Date"].astype(str).str[:10], "o": h["Open"], "h": h["High"],
                         "l": h["Low"], "c": h["Close"], "v": h["Volume"].clip(lower=1)})


def load_csv(path):
    d = pd.read_csv(path)
    d.columns = [c.strip().lower() for c in d.columns]
    ren = {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"}
    d = d.rename(columns=ren)
    d["v"] = d["v"].clip(lower=1)
    return d[["date", "o", "h", "l", "c", "v"]].sort_values("date").reset_index(drop=True)


def show(name, d, asset):
    r = pvv(d.tail(160).reset_index(drop=True), asset=asset)
    if r is None:
        print(f"{name}: not enough history (need ~75+ daily bars)")
        return
    pos = (r["close"] - r["buy"]) / (r["sell"] - r["buy"]) * 100 if r["sell"] > r["buy"] else float("nan")
    checks = ", ".join(f"{lab} {'yes' if ok else 'no'}" for lab, ok in
                       zip(["above 3-mo VWAP", "3-mo avg rising", "above 1 month ago"], r["checks"]))
    print(f"{name} {r['date']}: close {r['close']} | TRADE {r['buy']} - {r['sell']} ({pos:.0f}% up the range) | "
          f"TREND {r['trend']} (line {r['trendLine']}; {checks}) | vol {r['volPct']}%/day, volume x{r['volumeX']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tickers", nargs="*")
    ap.add_argument("--csv")
    ap.add_argument("--crypto", action="store_true", help="use the 24/7 crypto settings")
    a = ap.parse_args()
    asset = "crypto" if a.crypto else "equity"
    if a.csv:
        show(a.csv, load_csv(a.csv), asset)
    for t in a.tickers:
        try:
            show(t, load_yf(t), "crypto" if (a.crypto or t.endswith("-USD")) else asset)
        except Exception as e:
            print(f"{t}: {e}")
    if not a.csv and not a.tickers:
        ap.print_help()
