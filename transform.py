import logging

import numpy as np
import pandas as pd

from config import RAW

log = logging.getLogger(__name__)


def add_indicators(g):
    g = g.sort_values("date").copy()
    g["daily_return"] = g["close"].pct_change()
    g["volatility_20"] = g["daily_return"].rolling(20).std()
    g["sma_20"] = g["close"].rolling(20).mean()
    g["sma_50"] = g["close"].rolling(50).mean()
    std20 = g["close"].rolling(20).std()
    g["bb_upper"] = g["sma_20"] + 2 * std20
    g["bb_lower"] = g["sma_20"] - 2 * std20
    delta = g["close"].diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    g["rsi_14"] = 100 - 100 / (1 + avg_gain / avg_loss)
    return g


def quality_checks(df):
    assert df["close"].notna().all(), "Cours de clôture manquants"
    assert not df.duplicated(subset=["ticker", "date"]).any(), "Doublons ticker/date"
    assert (df["close"] > 0).all(), "Cours négatifs ou nuls"
    assert df["rsi_14"].dropna().between(0, 100).all(), "RSI hors de [0, 100]"
    log.info("Contrôles qualité OK")


def run():
    prices = pd.read_csv(RAW / "prices.csv", parse_dates=["date"])
    company = pd.read_csv(RAW / "sp500_companies.csv")

    prices["date"] = pd.to_datetime(prices["date"]).dt.tz_localize(None)
    prices = (prices.drop_duplicates(subset=["ticker", "date"])
                    .dropna(subset=["close"])
                    .sort_values(["ticker", "date"]).reset_index(drop=True))

    company = company.rename(columns={
        "Symbol": "ticker", "Security": "name", "GICS Sector": "sector",
        "GICS Sub-Industry": "sub_industry", "Headquarters Location": "headquarters",
    })
    company["ticker"] = company["ticker"].str.replace(".", "-", regex=False)
    company = company.drop_duplicates(subset="ticker")

    prices_t = pd.concat(
        [add_indicators(g) for _, g in prices.groupby("ticker")], ignore_index=True
    )
    enriched = prices_t.merge(company[["ticker", "name", "sector"]], on="ticker", how="left")

    quality_checks(enriched)
    return enriched, company
