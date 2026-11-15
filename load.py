import logging
import sqlite3

import pandas as pd

from config import WAREHOUSE_DB

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS dim_company (
    ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, sub_industry TEXT, headquarters TEXT);
CREATE TABLE IF NOT EXISTS dim_date (
    date_id INTEGER PRIMARY KEY, date TEXT NOT NULL, year INTEGER,
    quarter INTEGER, month INTEGER, day INTEGER, weekday INTEGER);
CREATE TABLE IF NOT EXISTS fact_prices (
    date_id INTEGER NOT NULL, ticker TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL NOT NULL, volume INTEGER,
    daily_return REAL, volatility_20 REAL, sma_20 REAL, sma_50 REAL,
    bb_upper REAL, bb_lower REAL, rsi_14 REAL,
    PRIMARY KEY (date_id, ticker),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (ticker) REFERENCES dim_company(ticker));
"""


def to_rows(df):
    return df.astype(object).where(df.notna(), None).values.tolist()


def run(enriched, company):
    conn = sqlite3.connect(WAREHOUSE_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(SCHEMA)

        dc = company[["ticker", "name", "sector", "sub_industry", "headquarters"]]
        conn.executemany("""
            INSERT INTO dim_company VALUES (?,?,?,?,?)
            ON CONFLICT(ticker) DO UPDATE SET name=excluded.name, sector=excluded.sector,
              sub_industry=excluded.sub_industry, headquarters=excluded.headquarters
        """, to_rows(dc))

        dates = pd.to_datetime(enriched["date"]).drop_duplicates().sort_values()
        dd = pd.DataFrame({
            "date_id": dates.dt.strftime("%Y%m%d").astype(int),
            "date": dates.dt.strftime("%Y-%m-%d"),
            "year": dates.dt.year, "quarter": dates.dt.quarter,
            "month": dates.dt.month, "day": dates.dt.day, "weekday": dates.dt.weekday,
        })
        conn.executemany("INSERT OR IGNORE INTO dim_date VALUES (?,?,?,?,?,?,?)", to_rows(dd))

        fact = enriched.copy()
        fact["date_id"] = pd.to_datetime(fact["date"]).dt.strftime("%Y%m%d").astype(int)
        cols = ["date_id", "ticker", "open", "high", "low", "close", "volume",
                "daily_return", "volatility_20", "sma_20", "sma_50",
                "bb_upper", "bb_lower", "rsi_14"]
        conn.executemany(f"""
            INSERT INTO fact_prices ({",".join(cols)}) VALUES ({",".join("?"*len(cols))})
            ON CONFLICT(date_id, ticker) DO UPDATE SET
              {",".join(f"{c}=excluded.{c}" for c in cols[2:])}
        """, to_rows(fact[cols]))

        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM fact_prices").fetchone()[0]
        log.info("fact_prices : %d lignes au total", n)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
