"""PVV risk range v3 (price, volume, volatility) — a Hedgeye-style approximation. Version 3 (October 2026).
Changes from v2:
  1. Volatility is exponentially weighted (half-life 5 bars, last 60 bars) instead of a 15-bar equal-weight mean,
     so the band reacts to volatility changes sooner.
  2. Asset classes: "equity" (stocks, ETFs, indexes; K=1.24, trend in trading sessions 63/10/21) and
     "crypto" (24/7 markets; K=1.10, trend in calendar days 91/14/30).
Evidence (fit on Jun 25-Aug 21, 2026, tested on Aug 24-Oct 20, 2026, against Hedgeye Risk Range readings):
  equity, 11 tickers, 902 readings: within-ticker width corr 0.19 -> 0.31, RMSE 0.93 -> 0.91 pp, best-fit K 1.24 unchanged.
  crypto (BTC), 82 readings: width corr 0.70 -> 0.88, RMSE 1.42 -> 1.05 pp, K 1.10; calendar trend 81/81 agreement.
Input: rows oldest->newest with date,o,h,l,c,v (daily bars). Output: dict for the newest row."""
import numpy as np, pandas as pd

HALF_LIFE = 5
PARAMS = {
    "equity": dict(K=1.24, trend_n=63, sma_lag=10, close_lag=21),
    "crypto": dict(K=1.10, trend_n=91, sma_lag=14, close_lag=30),
}

def _ewma_vol(x, hl=HALF_LIFE, n=60):
    x2 = (x.iloc[-n:].dropna() ** 2).values
    w = 0.5 ** (np.arange(len(x2))[::-1] / hl)
    return float(np.sqrt((w * x2).sum() / w.sum()))

def pvv(df, asset="equity"):
    p = PARAMS[asset]
    d = df.copy().reset_index(drop=True)
    if len(d) < max(74, p["trend_n"] + p["sma_lag"] + 1): return None
    ret = np.log(d.c / d.c.shift()); park = np.sqrt(np.log(d.h / d.l) ** 2 / (4 * np.log(2)))
    tp = (d.h + d.l + d.c) / 3; c = d.c.iloc[-1]
    # --- TRADE (3 weeks) ---
    sig = 0.5 * _ewma_vol(park) + 0.5 * _ewma_vol(ret)                      # volatility, recent days weighted more
    vr = d.v.iloc[-5:].mean() / d.v.iloc[-15:].mean()                         # volume: last week vs 3 weeks
    vmult = float(np.clip(np.sqrt(vr), 0.85, 1.5))
    vwap5 = (tp.iloc[-5:] * d.v.iloc[-5:]).sum() / d.v.iloc[-5:].sum()       # price anchor (volume-weighted)
    center = 0.25 * c + 0.75 * vwap5
    half = p["K"] * sig * np.sqrt(3) * vmult * center
    # --- TREND (3 months): majority of three checks ---
    n = p["trend_n"]
    vwapN = (tp.iloc[-n:] * d.v.iloc[-n:]).sum() / d.v.iloc[-n:].sum()
    sma = d.c.rolling(n).mean()
    checks = [c > vwapN, sma.iloc[-1] > sma.iloc[-1 - p["sma_lag"]], c > d.c.iloc[-1 - p["close_lag"]]]
    trend = "Bullish" if sum(checks) >= 2 else "Bearish"
    rN, vN = ret.iloc[-n:], d.v.iloc[-n:]
    udv = vN[rN > 0].sum() / max(vN[rN < 0].sum(), 1)
    nd = 2 if c >= 10 else 4                                                   # 2 decimals for prices >= 10, else 4
    return dict(date=str(d.date.iloc[-1])[:10], close=round(float(c), nd), buy=round(float(center - half), nd), sell=round(float(center + half), nd),
                trend=trend, trendLine=round(float(vwapN), nd), checks=[bool(x) for x in checks], volPct=round(float(sig * 100), 2),
                volumeX=round(float(vr), 2), upDownVol=round(float(udv), 2), asset=asset, version=3)
