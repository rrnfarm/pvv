#!/usr/bin/env python3
"""Daily PVV run for a list of tickers.

Reads tickers.txt, runs the PVV model on each ticker, adds new readings to readings.csv,
and writes latest.md: a table of today's readings plus alerts for
  - TREND flips (Bullish <-> Bearish since the last logged reading)
  - low-confidence TREND (close within 0.5% of the trend line)
  - closes at or beyond the TRADE range's buy or sell level

Usage:  python3 run_daily.py
Needs:  pip install pandas numpy yfinance
"""
import os, sys
import pandas as pd
from pvv import pvv
from run_pvv import load_yf

HERE = os.path.dirname(os.path.abspath(__file__))
TICKERS = os.path.join(HERE, "tickers.txt")
LOG = os.path.join(HERE, "readings.csv")
LATEST = os.path.join(HERE, "latest.md")
DATA = os.path.join(HERE, "data")          # daily bars per ticker (data/SPY.csv, ...)
NEAR_LINE = 0.005          # within 0.5% of the trend line = low-confidence TREND
COLS = ["date", "ticker", "close", "buy", "sell", "range_pos", "trend", "trend_line",
        "check_vwap", "check_sma", "check_1mo", "vol_pct", "volume_x"]


def read_tickers(path):
    out = []
    with open(path) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line:
                out += line.replace(",", " ").split()
    return list(dict.fromkeys(t.upper() for t in out))


def yn(b):
    return "✓" if b else "✗"


def main(loader=load_yf):
    tickers = read_tickers(TICKERS)
    hist = pd.read_csv(LOG, dtype={"date": str}) if os.path.exists(LOG) else pd.DataFrame(columns=COLS)
    new_rows, table, alerts, errors = [], [], [], []

    for t in tickers:
        asset = "crypto" if t.endswith("-USD") else "equity"
        try:
            bars = loader(t)
            r = pvv(bars.tail(160).reset_index(drop=True), asset=asset)
            os.makedirs(DATA, exist_ok=True)       # save the bars so Claude can read them from GitHub
            bars.tail(170).rename(columns=dict(o="open", h="high", l="low", c="close", v="volume"))[
                ["date", "open", "high", "low", "close", "volume"]].round(4).to_csv(
                os.path.join(DATA, f"{t}.csv"), index=False)
        except Exception as e:
            errors.append(f"{t}: {e}")
            continue
        if r is None:
            errors.append(f"{t}: not enough history (needs ~75+ daily bars)")
            continue

        width = r["sell"] - r["buy"]
        pos = (r["close"] - r["buy"]) / width * 100 if width > 0 else float("nan")
        gap = r["close"] / r["trendLine"] - 1

        mine = hist[hist.ticker == t].sort_values("date")
        already = (mine.date == r["date"]).any()
        prior = mine[mine.date < r["date"]]
        prev = prior.iloc[-1] if len(prior) else None

        notes = []
        if prev is not None and prev.trend != r["trend"]:
            notes.append(f"TREND flipped {prev.trend} → {r['trend']}")
        if abs(gap) < NEAR_LINE:
            notes.append(f"low-confidence TREND (close {gap*100:+.1f}% from trend line)")
        if r["close"] <= r["buy"]:
            notes.append("at/below the buy level")
        elif r["close"] >= r["sell"]:
            notes.append("at/above the sell level")
        for n in notes:
            alerts.append(f"**{t}**: {n}")

        c = r["checks"]
        table.append(f"| {t} | {r['close']} | {r['buy']} – {r['sell']} | {pos:.0f}% | {r['trend']} | "
                     f"{r['trendLine']} ({gap*100:+.1f}%) | {yn(c[0])}{yn(c[1])}{yn(c[2])} | {r['volPct']}% |")
        if not already:
            new_rows.append(dict(date=r["date"], ticker=t, close=r["close"], buy=r["buy"], sell=r["sell"],
                                 range_pos=round(pos, 1), trend=r["trend"], trend_line=r["trendLine"],
                                 check_vwap=c[0], check_sma=c[1], check_1mo=c[2],
                                 vol_pct=r["volPct"], volume_x=r["volumeX"]))

    if new_rows:
        out = pd.concat([hist, pd.DataFrame(new_rows)], ignore_index=True) if len(hist) else pd.DataFrame(new_rows)
        out[COLS].sort_values(["date", "ticker"]).to_csv(LOG, index=False)

    dates = sorted({row["date"] for row in new_rows}) or sorted(hist.date.unique())[-1:]
    md = [f"## PVV readings — {', '.join(dates)}", ""]
    md += ["### Alerts", *(f"- {a}" for a in alerts), ""] if alerts else ["No alerts today.", ""]
    md += ["| Ticker | Close | TRADE range (buy – sell) | Position in range | TREND | Trend line (close vs line) | Checks* | Vol/day |",
           "|---|---|---|---|---|---|---|---|", *table, "",
           "*Checks: above 3-month VWAP / 3-month average rising / above 1 month ago. "
           "Bullish when at least 2 of 3 pass. Readings use completed daily bars. Not investment advice."]
    if errors:
        md += ["", "### Problems", *(f"- {e}" for e in errors)]
    if not new_rows and table:
        md += ["", "_No new daily bar since the last run (market holiday?), so nothing new was logged._"]
    text = "\n".join(md) + "\n"
    with open(LATEST, "w") as f:
        f.write(text)
    print(text)

    gh_out, gh_sum = os.environ.get("GITHUB_OUTPUT"), os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"new={'true' if new_rows else 'false'}\n")
    if gh_sum:
        with open(gh_sum, "a") as f:
            f.write(text)
    if not table:                      # every ticker failed: fail the run so GitHub emails you
        sys.exit(1)


if __name__ == "__main__":
    main()
