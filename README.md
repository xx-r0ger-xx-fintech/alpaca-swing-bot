# Alpaca Swing Bot

A lightweight Python swing trading bot that runs on DigitalOcean App Platform. Uses a confluence of technical indicators to scan a stock watchlist every morning and automatically place bracket orders via the Alpaca API.

---

## How It Works

Every weekday at **9:35 AM ET**, the bot:

1. Pulls 90 days of daily OHLCV data for each symbol in the watchlist
2. Runs the signal strategy — requires all three indicators to align before trading
3. Places bracket orders (with take profit and stop loss) for any BUY signals
4. Logs every decision to DigitalOcean logs, GitHub, and Discord

---

## Signal Strategy

Three indicators must confirm before a trade is placed:

| Indicator | Period | Buy Condition |
|---|---|---|
| **EMA crossover** | 20 / 50 | Short EMA > Long EMA (0.5% tolerance) |
| **RSI** | 14 | RSI > 55 |
| **VWAP** | Rolling 90-day | Price > VWAP |

Every skipped trade includes a reason explaining which condition failed.

---

## Risk Management

| Setting | Default |
|---|---|
| Trade size | 20% of account equity |
| Max trade size | $500 |
| Max open positions | 3 |
| Take profit | +10% |
| Stop loss | -4% |

Position sizing compounds automatically — as the account grows, trade size grows with it.

---

## Logging

After each scan:
- **DigitalOcean logs** — full detail, real-time
- **GitHub** — daily markdown summary committed to `storage/logs/YYYY-MM-DD.md`
- **Discord** — morning ping with account equity and all decisions

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
├── Dockerfile
└── requirements.txt
```

---

## Deployment

### Automated (recommended)

```bash
DO_TOKEN=xxx ALPACA_API_KEY=xxx ALPACA_API_SECRET=xxx python deploy.py
```

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
| `TAKE_PROFIT_PCT` | No | Take profit percentage (default: 0.10) |
| `STOP_LOSS_PCT` | No | Stop loss percentage (default: 0.04) |
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
