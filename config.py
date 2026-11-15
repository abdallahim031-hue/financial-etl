from pathlib import Path

TICKERS = ["AAPL", "MSFT", "TSLA", "JPM", "XOM"]
START_DATE = "2020-01-01"

RAW = Path("raw")
DATA = Path("data")
WAREHOUSE_DB = DATA / "warehouse.db"
PORTFOLIO_DB = Path("portfolio.db")

for p in (RAW, DATA):
    p.mkdir(exist_ok=True)
