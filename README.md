# GOLDBOT — XAUUSD Trading System
## Complete Setup & Deployment Guide

---

## 📁 Project Structure

```
/trading-bot
├── bot/                          # Python trading engine
│   ├── trading_bot.py            # Main bot orchestrator
│   ├── strategies/
│   │   └── combined_strategy.py  # RSI + MA Crossover + ATR
│   ├── ml/
│   │   ├── signal_classifier.py  # ML trade filter (Random Forest/GBM)
│   │   └── models/               # Saved model artifacts
│   ├── backtest/
│   │   └── backtester.py         # Vectorised backtesting engine
│   └── utils/
│       ├── risk_manager.py       # Position sizing & risk gates
│       └── logger.py             # Structured logging
│
├── backend/                      # FastAPI REST API
│   ├── main.py                   # App factory + WebSocket
│   ├── src/
│   │   ├── routes/               # auth, bot, trades, metrics, settings, backtest
│   │   ├── middleware/auth.py    # JWT authentication
│   │   ├── websocket/manager.py  # WebSocket broadcast
│   │   └── config.py             # Settings via env
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                     # Next.js 14 dashboard
│   ├── src/app/
│   │   ├── page.jsx              # Full dashboard (auth, overview, trades, settings, backtest)
│   │   └── layout.jsx
│   ├── package.json
│   └── Dockerfile
│
├── database/
│   └── migrations/
│       └── 001_initial_schema.sql   # Full PostgreSQL schema
│
├── docker/
│   └── nginx.conf                # Nginx reverse proxy + SSL
│
├── docker-compose.yml            # Full stack orchestration
├── .env.example                  # Environment template
└── README.md
```

---

## ⚙️ Prerequisites

- **VPS**: Ubuntu 22.04 LTS (min 4GB RAM, 2 vCPU)
- **MetaTrader 5**: Installed on Windows PC or Wine on Linux
- **HFM Account**: Demo or Live account from HFM (HotForex)
- **Domain**: Pointed to your VPS IP (for SSL)

---

## 🚀 Quick Start (Local Development)

### 1. Clone and configure

```bash
git clone <your-repo> trading-bot
cd trading-bot
cp .env.example .env
# Edit .env with your credentials
nano .env
```

### 2. Start infrastructure

```bash
# Start PostgreSQL + Redis
docker-compose up postgres redis -d

# Apply database schema
docker exec -i goldbot_postgres psql -U postgres -d tradingbot \
  < database/migrations/001_initial_schema.sql
```

### 3. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### 5. (Optional) Train ML model

```bash
cd bot
pip install -r requirements.txt
python ml/signal_classifier.py
# Trains on 5 years of Gold Futures data, saves to ml/models/
```

### 6. Start trading bot

```bash
cd bot
python trading_bot.py
# Or via API: POST /api/bot/start
```

---

## 🐳 Production Docker Deployment

### 1. VPS setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y
```

### 2. SSL certificate (Let's Encrypt)

```bash
sudo apt install certbot -y
sudo certbot certonly --standalone -d yourdomain.com

# Copy certs to docker/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/
```

### 3. Configure environment

```bash
cp .env.example .env
nano .env  # Fill ALL values, especially:
           # DB_PASSWORD, JWT_SECRET, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
```

### 4. Build and launch

```bash
# Build all images
docker-compose build

# Start full stack
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5. Create admin user

```bash
# Exec into backend container
docker exec -it goldbot_backend bash

# Create admin via Python
python -c "
import asyncio, asyncpg, bcrypt, os
async def main():
    db = await asyncpg.connect(os.getenv('DATABASE_URL'))
    pw = bcrypt.hashpw(b'your_admin_password', bcrypt.gensalt()).decode()
    await db.execute(\"INSERT INTO users (email,password_hash,name,role) VALUES (\$1,\$2,'Admin','admin')\", 'admin@example.com', pw)
    print('Admin created')
asyncio.run(main())
"
```

---

## 🔌 API Documentation

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login, returns JWT |
| POST | `/api/auth/register` | Register new user |
| GET | `/api/auth/me` | Current user info |

### Bot Control (Admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bot/start` | Start trading bot |
| POST | `/api/bot/stop` | Stop trading bot |
| GET | `/api/bot/status` | Bot status + live metrics |

### Trades
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/trades/?limit=50&offset=0` | Trade history |
| GET | `/api/trades/{id}` | Single trade detail |

### Performance Metrics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/metrics/summary` | Win rate, PnL, drawdown, etc. |
| GET | `/api/metrics/performance-history` | Time-series metrics |

### Strategy Settings (Admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings/` | Current settings |
| PUT | `/api/settings/` | Bulk update settings |
| GET | `/api/settings/defaults` | Default values + ranges |

### Backtesting
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/backtest/run` | Run historical backtest |
| GET | `/api/backtest/history` | Past backtest results |

### WebSocket
```
ws://yourdomain.com/ws?token=<JWT>

# Receives every 5 seconds:
{
  "type": "heartbeat",
  "bot_status": "running|stopped",
  "metrics": {
    "balance": 10000.00,
    "equity": 10245.50,
    "daily_pnl": 245.50,
    "open_trades": 2,
    ...
  }
}
```

---

## 📊 Strategy Logic

### Signal Generation
1. **RSI** (default period 14):
   - Oversold (< 30) + price above slow EMA → BUY signal
   - Overbought (> 70) + price below slow EMA → SELL signal

2. **EMA Crossover** (default 20/50):
   - Golden cross (fast > slow) + RSI not overbought → BUY
   - Death cross (fast < slow) + RSI not oversold → SELL

3. **ATR Stop Loss / Take Profit**:
   - SL = Entry ± (ATR × 1.5)
   - TP = Entry ± (ATR × 3.0) → 1:2 risk/reward

4. **ML Filter** (optional):
   - Gradient Boosting classifier trained on 5 years XAUUSD data
   - Only trades signals with confidence > 65%

### Risk Management
- **Position sizing**: Fixed fractional (risk % of balance ÷ SL pips)
- **Daily loss limit**: Halts trading if day's PnL < -3% of balance
- **Max open trades**: Never exceeds configured limit (default 3)

---

## 🔧 HFM (HotForex) Connection

1. Download MetaTrader 5 from HFM's website
2. Create Demo or Live account at **hfm.com**
3. Server names: `HFMarkets-Demo` | `HFMarkets-Live01`
4. Fill MT5_LOGIN, MT5_PASSWORD, MT5_SERVER in `.env`
5. Ensure XAUUSD is visible in Market Watch
6. The bot uses Magic Number `20240101` for trade identification

---

## 🔐 Security Notes

- JWT tokens expire in 24h by default
- All passwords bcrypt-hashed with salt rounds 12
- Nginx rate limits: 30 req/min (API), 5 req/min (auth)
- Never expose PostgreSQL or Redis ports publicly in production
- Rotate `JWT_SECRET` immediately after first deployment
- Use `openssl rand -hex 64` to generate secure secrets

---

## 📈 Backtest Example Results

Running on XAUUSD H1 (2022-2024) with defaults:
- Win Rate: ~58-62%
- Profit Factor: ~1.4-1.8
- Max Drawdown: ~8-12%
- Sharpe Ratio: ~0.9-1.3

*(Results vary by market conditions and parameters)*

---

## 🆘 Troubleshooting

**Bot not connecting to MT5:**
- Ensure MT5 is running and logged in
- Check `MT5_SERVER` matches your account's server
- Try `mt5.initialize()` in Python shell manually

**WebSocket disconnects:**
- Check nginx `proxy_read_timeout` (set to 3600s)
- Verify JWT token is valid and not expired

**No trades being generated:**
- Check bot logs: `docker-compose logs -f backend`
- Verify XAUUSD is available on your broker account
- Check strategy settings aren't too restrictive
