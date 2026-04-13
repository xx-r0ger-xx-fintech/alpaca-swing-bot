"""
test_notify.py — Send a test Discord notification with mock data.

Usage:
    python test_notify.py

Requires DISCORD_WEBHOOK_URL in .env (same as the bot uses).
"""

from dotenv import load_dotenv
load_dotenv()

from app import logger


class MockPosition:
    """Mimics the Alpaca Position object for test purposes."""
    def __init__(self, symbol, qty, entry, price, pl, plpc):
        self.symbol           = symbol
        self.qty              = str(qty)
        self.avg_entry_price  = str(entry)
        self.current_price    = str(price)
        self.unrealized_pl    = str(pl)
        self.unrealized_plpc  = str(plpc)   # decimal, e.g. 0.032 = 3.2%


def main():
    print("Sending test Discord notification...")

    # ── Mock account state ────────────────────────────────────────────────────
    mock_positions = {
        "NVDA": MockPosition("NVDA", qty=2,    entry=875.00, price=912.50, pl=75.00,  plpc=0.0429),
        "AAPL": MockPosition("AAPL", qty=3,    entry=182.00, price=178.30, pl=-11.10, plpc=-0.0204),
    }

    logger.log_scan_start(
        equity        = 12_450.00,
        cash          = 4_200.00,
        trade_size    = 500.00,
        positions     = mock_positions,
        watchlist_size= 10,
    )

    # ── Mock strategy signals ─────────────────────────────────────────────────
    logger.log_decision("MSFT",  "BUY",  "EMA20=412.30 / EMA50=398.10 | RSI=61.4 | Price=415.00 vs VWAP=409.50", 415.00)
    logger.log_decision("TSLA",  None,   "No signal — EMA not crossed (285.10 vs 291.40) | RSI too low (48.2 < 55.0)", 285.00)
    logger.log_decision("AMD",   None,   "No signal — Price below VWAP (162.40 < 165.20)", 162.40)
    logger.log_decision("GOOGL", "SELL", "EMA20=171.20 / EMA50=175.80 | RSI=42.1 | Price=170.50 vs VWAP=174.30", 170.50)

    # ── Mock orders ───────────────────────────────────────────────────────────
    logger.log_order("MSFT",  "BUY",  415.00, qty=1.2048, tp=456.50, sl=398.40)
    logger.log_order("GOOGL", "SELL", 170.50, qty=2.9326, tp=153.45, sl=177.32)

    # ── Mock pre-filter skips ─────────────────────────────────────────────────
    logger.log_skipped("META",  "Already in position")
    logger.log_skipped("AMZN",  "Max positions reached")
    logger.log_skipped("SPY",   "Insufficient cash ($4,200.00 < $500.00)")
    logger.log_skipped("QQQ",   "No price data returned")

    # ── Fire the notification ─────────────────────────────────────────────────
    logger.log_scan_end()
    print("Done.")


if __name__ == "__main__":
    main()
