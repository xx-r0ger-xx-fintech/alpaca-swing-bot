# Alpaca Swing Bot

A lightweight Python swing trading bot that runs on DigitalOcean App Platform. Uses a confluence of technical indicators to scan a stock watchlist every morning and automatically place fractional orders via the Alpaca API.

---

## How It Works

Every weekday at **9:35 AM ET**, the bot:

1. Pulls 90 days of daily OHLCV data for each symbol in the watchlist
2. Runs the signal strategy — requires all three indicators to align before trading
3. Places fractional market orders for any BUY signals, then attaches a GTC stop-loss as a safety net
4. Exits positions via SELL signal (trend reversal) — profits are taken when the strategy says the trend has turned, not at a fixed percentage
5. Logs every decision to DigitalOcean logs, GitHub, and Discord

---

## Signal Strategy

Three indicators must confirm before a trade is placed:

| Indicator | Period | Buy Condition |
|---|---|---|
| **EMA crossover** | 20 / 50 | Short EMA > Long EMA (0.5% tolerance) |
| **RSI** | 14 | RSI > 55 |
| **VWAP** | Rolling 20-day | Price > VWAP |

Every skipped trade includes a reason explaining which condition failed.

---

## Risk Management

| Setting | Default |
|---|---|
| Trade size | 20% of account equity |
| Max trade size | $500 |
| Max open positions | 3 |
| Stop loss | -4% GTC safety net (primary exit is signal-based) |

Position sizing compounds automatically — as the account grows, trade size grows with it. Fractional shares mean the full trade size is deployed regardless of share price.

---

## Logging

After every scan a Discord notification is always sent, regardless of whether trades were placed. It uses multiple color-coded embeds:

| Embed | Color | Content |
|---|---|---|
| Account Snapshot | Blue | Equity, cash, trade size, open positions with unrealized P&L |
| Buy Orders | Green | Any buy orders executed this scan |
| Sell Orders | Red | Any sell orders executed this scan |
| Signals Evaluated | Yellow | Every symbol that reached strategy evaluation with reason |
| Pre-filter Skips | Purple | Symbols skipped before strategy (max positions, no cash, etc.) |
| Scan Summary | Blue | Total counts + next scan time |

Pre-filter and trade embeds are omitted when empty. The summary is always present.

- **DigitalOcean logs** — full detail, real-time
- **GitHub** — daily markdown summary committed to `storage/logs/YYYY-MM-DD.md`

---

## Project Structure

```
alpaca-swing-bot/
├── app/
│   ├── config.py      # All settings, configurable via env vars
│   ├── strategy.py    # EMA + RSI + VWAP signal logic
│   ├── logger.py      # DO logs, GitHub commit, Discord webhook
│   └── main.py        # Orchestration and daily scan loop
├── storage/
│   └── logs/          # Daily trade log markdown files
├── deploy.py          # Automated DigitalOcean deployment script
├── test_notify.py     # Send a test Discord notification with mock data
├── Dockerfile
└── requirements.txt
```

---

## Deployment

### Automated (recommended)

1. Copy `.env.example` to `.env` and fill in your credentials
2. Run:

```bash
python deploy.py
```

The script creates the DO app, sets all secrets, and tails the deployment automatically.

### Manual (DigitalOcean App Platform)

1. Connect this repo to DigitalOcean App Platform
2. Set component type to **Worker**
3. Set run command to `python -m app.main`
4. Add environment variables (see below)

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ALPACA_API_KEY` | Yes | Alpaca live trading API key |
| `ALPACA_API_SECRET` | Yes | Alpaca live trading API secret |
| `GITHUB_TOKEN` | Yes | GitHub token with `repo` scope (for log commits) |
| `DISCORD_WEBHOOK_URL` | Yes | Discord channel webhook URL |
| `WATCHLIST` | No | Comma-separated symbols (default: AAPL,MSFT,NVDA,TSLA,AMZN,META,AMD,GOOGL,SPY,QQQ) |
| `TRADE_SIZE_PCT` | No | Fraction of equity per trade (default: 0.20) |
| `MAX_TRADE_SIZE` | No | Hard cap per trade in dollars (default: 500) |
| `MAX_POSITIONS` | No | Max concurrent positions (default: 3) |
| `STOP_LOSS_PCT` | No | Stop loss percentage for GTC safety net (default: 0.04) |
| `EMA_SHORT` | No | Short EMA period (default: 20) |
| `EMA_LONG` | No | Long EMA period (default: 50) |
| `RSI_BUY_THRESHOLD` | No | RSI buy threshold (default: 55) |
| `RSI_SELL_THRESHOLD` | No | RSI sell threshold (default: 45) |

---

## Requirements

- Python 3.12+
- Alpaca account (live trading enabled)
- DigitalOcean account
- Discord server with a webhook configured
- GitHub personal access token (repo scope)
