import os
import time
import datetime
from datetime import timedelta

import pytz
from dotenv import load_dotenv

load_dotenv()

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from app import config
from app.strategy import calculate_signals
from app import logger

ET = pytz.timezone("America/New_York")

STRATEGY_CONFIG = {
    "EMA_SHORT":          config.EMA_SHORT,
    "EMA_LONG":           config.EMA_LONG,
    "RSI_PERIOD":         config.RSI_PERIOD,
    "RSI_BUY_THRESHOLD":  config.RSI_BUY_THRESHOLD,
    "RSI_SELL_THRESHOLD": config.RSI_SELL_THRESHOLD,
}


# ── Alpaca client setup ────────────────────────────────────────────────────────

def get_clients():
    api_key    = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("ALPACA_API_KEY and ALPACA_API_SECRET must be set")
    trading = TradingClient(api_key, api_secret, paper=False)
    data    = StockHistoricalDataClient(api_key, api_secret)
    return trading, data


# ── Data fetching ──────────────────────────────────────────────────────────────

def get_bars(data_client, symbol: str):
    end   = datetime.datetime.now(ET) - timedelta(days=1)
    start = end - timedelta(days=config.BARS_TO_FETCH)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
    )
    bars = data_client.get_stock_bars(request)

    if symbol not in bars or len(bars[symbol]) == 0:
        return None

    df = bars[symbol].df.reset_index()
    return df


# ── Market hours ───────────────────────────────────────────────────────────────

def is_scan_window() -> bool:
    """Returns True between 9:35–10:00 AM ET on weekdays."""
    now = datetime.datetime.now(ET)
    if now.weekday() >= 5:
        return False
    window_open  = now.replace(hour=9,  minute=35, second=0, microsecond=0)
    window_close = now.replace(hour=10, minute=0,  second=0, microsecond=0)
    return window_open <= now <= window_close


# ── Core scan logic ────────────────────────────────────────────────────────────

def run_scan(trading_client, data_client):
    logger.log("=== Alpaca Swing Bot — daily scan ===")

    account        = trading_client.get_account()
    equity         = float(account.equity)
    cash           = float(account.cash)
    open_positions = {p.symbol: p for p in trading_client.get_all_positions()}
    trade_size     = min(equity * config.TRADE_SIZE_PCT, config.MAX_TRADE_SIZE)

    logger.log_scan_start(equity, cash, trade_size, open_positions, len(config.WATCHLIST))

    for symbol in config.WATCHLIST:

        # Guard: max positions
        if len(open_positions) >= config.MAX_POSITIONS:
            logger.log_skipped(symbol, "Max positions reached")
            continue

        # Guard: already holding
        if symbol in open_positions:
            logger.log_skipped(symbol, "Already in position")
            continue

        # Guard: insufficient cash
        if cash < trade_size:
            logger.log_skipped(symbol, f"Insufficient cash (${cash:.2f} < ${trade_size:.2f})")
            break

        try:
            df = get_bars(data_client, symbol)
            if df is None:
                logger.log_skipped(symbol, "No price data returned")
                continue

            signal, reason = calculate_signals(df, STRATEGY_CONFIG)
            current_price  = float(df.iloc[-1]["close"])

            logger.log_decision(symbol, signal, reason, current_price)

            if signal != "BUY":
                continue

            # Calculate order parameters
            qty      = round(trade_size / current_price, 4)
            tp_price = round(current_price * (1 + config.TAKE_PROFIT_PCT), 2)
            sl_price = round(current_price * (1 - config.STOP_LOSS_PCT),   2)

            order = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.BRACKET,
                take_profit=TakeProfitRequest(limit_price=tp_price),
                stop_loss=StopLossRequest(stop_price=sl_price),
            )

            trading_client.submit_order(order)
            logger.log_order(symbol, "BUY", current_price, qty, tp_price, sl_price)

            open_positions[symbol] = True  # track locally so loop stays accurate
            cash -= trade_size

        except Exception as e:
            logger.log_error(f"{symbol}: {e}")

    logger.log_scan_end()


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    logger.log("Alpaca Swing Bot started")
    trading_client, data_client = get_clients()

    scanned_today  = False
    last_scan_date = None

    while True:
        now   = datetime.datetime.now(ET)
        today = now.date()

        # Reset flag at midnight
        if last_scan_date != today:
            scanned_today  = False
            last_scan_date = today

        if not scanned_today and is_scan_window():
            try:
                run_scan(trading_client, data_client)
            except Exception as e:
                logger.log_error(f"Scan failed: {e}")
            scanned_today = True

        time.sleep(60)  # check every minute


if __name__ == "__main__":
    main()
