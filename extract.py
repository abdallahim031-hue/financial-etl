import logging
import sqlite3
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

from config import TICKERS, START_DATE, RAW, PORTFOLIO_DB

log = logging.getLogger(__name__)


def extract_prices():
    df = yf.download(TICKERS, start=START_DATE, group_by="ticker", auto_adjust=True, progress=False)
    frames = []
    for t in TICKERS:
        d = df[t].copy().reset_index()
        d["ticker"] = t
        frames.append(d)
    prices = pd.concat(frames, ignore_index=True)
    prices.columns = [c.lower() for c in prices.columns]
    prices = prices.dropna(subset=["close"])
    if prices.empty:
        raise ValueError("Aucun cours téléchargé : Yahoo Finance a probablement échoué")
    prices.to_csv(RAW / "prices.csv", index=False)
    log.info("prices : %d lignes", len(prices))


def extract_companies():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (financial-etl)"}, timeout=30).text
    company = pd.read_html(StringIO(html))[0]
    company.to_csv(RAW / "sp500_companies.csv", index=False)
    log.info("companies : %d lignes", len(company))


def extract_transactions():
    with sqlite3.connect(PORTFOLIO_DB) as conn:
        tx = pd.read_sql("SELECT * FROM transactions", conn)
    tx.to_csv(RAW / "transactions.csv", index=False)
    log.info("transactions : %d lignes", len(tx))


def run():
    extract_prices()
    extract_companies()
    extract_transactions()
