# Telegram Bot + Railway Postgres

A minimal FastAPI Telegram bot with webhook integration and PostgreSQL storage via SQLAlchemy.

## Prerequisites

1. Python 3.10+
2. A Telegram bot token from [@BotFather](https://t.me/BotFather)
3. Your Railway Postgres database (already provided)
4. A public HTTPS URL for webhook (Railway domain, ngrok, etc.)

## Local Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

Create `.env`:
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
WEBHOOK_URL=https://xxxx.ngrok.io  # or your public domain
DATABASE_URL=postgresql://user:pass@host:5432/dbname
PORT=8000
```

## Run Locally

```bash
uvicorn app.main:app --reload
```

## Test Webhook Locally

1. Start ngrok: `ngrok http 8000`
2. Set `WEBHOOK_URL` to the ngrok URL
3. Restart the app
4. In Railway dashboard or via curl, set the webhook:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<NGROK_URL>/webhook"
   ```

## Deploy to Railway

1. Push this project to GitHub
2. In Railway, create a new service from the repo
3. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `DATABASE_URL` (Railway provides this automatically if Postgres is in same project)
   - `WEBHOOK_URL` = `https://<your-service-name>.up.railway.app`
4. Railway auto-deploys using the included `railway.json`

## API

- `GET /health` - Health check
- `POST /webhook` - Telegram webhook endpoint

## Bot Commands

- `/start` - Register and get welcome message
- `/stats` - Show your message statistics
- Any text - Bot echoes it back and stores in Postgres

## Database Schema

Auto-created on first run:
- `users` - Telegram user info
- `messages` - Inbound/outbound messages with timestamps

## Security Note

The credentials you shared have been placed in `.env.example` as placeholders. In production, use Railway environment variables. Rotate any exposed passwords immediately.
