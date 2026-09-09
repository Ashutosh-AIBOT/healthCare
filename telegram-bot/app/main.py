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

bot_application: Application | None = None
if settings.telegram_bot_token:
    bot_application = Application.builder().token(settings.telegram_bot_token).build()
    bot_application.add_handler(start_command)
    bot_application.add_handler(stats_command)
    from telegram.ext import MessageHandler, filters
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
else:
    logger.warning("TELEGRAM_BOT_TOKEN not set. Webhook disabled; /health stays ok (per-user bots connect via main backend).")

app = FastAPI(title="Telegram Bot API")

@app.get("/health")
async def health():
    return {"status": "ok", "bot_configured": bot_application is not None}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    if bot_application is None:
        raise HTTPException(status_code=503, detail="Bot token not configured on this service.")
    try:
        data = await request.json()
        update = Update.de_json(data, bot_application.bot)
        await bot_application.process_update(update)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.on_event("startup")
async def on_startup():
    try:
        await init_db()
    except Exception as e:
        logger.warning(f"DB init skipped/failed: {e}")
    if bot_application is not None and settings.webhook_url:
        try:
            await bot_application.bot.set_webhook(url=f"{settings.webhook_url}/webhook", drop_pending_updates=True)
            logger.info(f"Webhook set to {settings.webhook_url}/webhook")
        except Exception as e:
            logger.warning(f"set_webhook failed (check token): {e}")
    else:
        logger.warning("WEBHOOK_URL or token not set. Webhook registration skipped.")

@app.on_event("shutdown")
async def on_shutdown():
    if bot_application is not None:
        await bot_application.shutdown()
