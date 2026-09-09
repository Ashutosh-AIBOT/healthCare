from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application
from app.config import settings
from app.telegram_bot import start_command, stats_command, echo_message
from app.database import init_db
import app.models  # noqa: F401 - register tables for Base.metadata.create_all
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot_application: Application = Application.builder().token(settings.telegram_bot_token).build()
bot_application.add_handler(start_command)
bot_application.add_handler(stats_command)
from telegram.ext import MessageHandler, filters
bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))

app = FastAPI(title="Telegram Bot API")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot_application.bot)
        await bot_application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.on_event("startup")
async def on_startup():
    await init_db()
    if settings.webhook_url:
        await bot_application.bot.set_webhook(url=f"{settings.webhook_url}/webhook", drop_pending_updates=True)
        logger.info(f"Webhook set to {settings.webhook_url}/webhook")
    else:
        logger.warning("WEBHOOK_URL not set. Set it and restart to register webhook.")

@app.on_event("shutdown")
async def on_shutdown():
    await bot_application.shutdown()
