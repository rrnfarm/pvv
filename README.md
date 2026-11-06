# PVV risk range model (v3)

A price / volume / volatility model that gives each stock or ETF a short-term **TRADE range** (a buy level and a sell level) and a 3-month **TREND** (Bullish or Bearish). It was built with Claude in October 2026 as an approximation of Hedgeye's Risk Range Signals, then tested against Hedgeye's published ranges. It is not affiliated with Hedgeye, and it doesn't use any Hedgeye data. It only needs daily price bars.

## How to use it with Claude
1. Upload all three files (`pvv.py`, `run_pvv.py`, `README.md`) to a Claude chat that can run code.
2. Ask, for example: *"Run the PVV model on SPY, QQQ, NVDA and GLD and explain the readings."*
   Claude will install `pandas numpy yfinance` and run `python3 run_pvv.py SPY QQQ NVDA GLD`.
3. You can also give it your own data as a CSV with columns `date,open,high,low,close,volume`, oldest first: `python3 run_pvv.py --csv mydata.csv`.
4. For Bitcoin and other 24/7 markets, use the crypto settings: `python3 run_pvv.py BTC-USD --crypto`.

## How it works
**TRADE range (about 3 weeks):**
- Volatility comes from daily returns and daily high-low ranges, exponentially weighted with a 5-day half-life over the last 60 days.
- The range is centered mostly on the 5-day volume-weighted price (VWAP), with 25% weight on the last close.
- Width = 1.24 × volatility × √3. It widens by up to 50% when the last week's volume runs above the last 3 weeks' volume.

**TREND (about 3 months):** Bullish if at least 2 of these 3 checks pass:
1. The close is above the 63-day volume-weighted price. That price is reported as the "trend line".
2. The 63-day moving average is higher than it was 10 days ago.
3. The close is above its level 21 trading days ago.

## How it has performed
Backtest against Hedgeye's daily Risk Range readings: 25 tickers, Jun 25 – Nov 5, 2026, about 1,900 readings.

- **TREND:** when Hedgeye takes a side, PVV agrees 92–94% of the time. Counting Hedgeye's Neutral calls, the exact match is about 85%. PVV is on the opposite side only 5–7% of the time. Its flips land within about a day of Hedgeye's on average.
- **TRADE ranges:**
  - Same average width (about 7%).
  - Buy and sell levels within about 1% of price of Hedgeye's.
  - The next day's close landed inside PVV's range 84% of the time, vs 81% for Hedgeye's range.

## Limits
- **No Neutral setting.** PVV always says Bullish or Bearish. When a close is within about 0.5% of the trend line, treat the TREND reading as low-confidence: it can flip back and forth.
- **Short test.** The out-of-sample period is only about 2 weeks, and the whole sample covers a single market regime (mid-2026 into a downturn).
- **What it's tested on:** stocks, ETFs, and gold, silver and Bitcoin through their ETFs. Yields, currencies, oil and VIX are not tested.
- **Timing.** It uses completed daily bars, so a reading reflects the prior close.
- **Not investment advice.** It's a tool to frame entries, exits and trend. It doesn't tell you what to buy or sell.
