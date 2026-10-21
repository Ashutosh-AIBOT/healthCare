from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import User, Message
from app.schemas import StatsResponse
import logging

logger = logging.getLogger(__name__)

async def ensure_user(session: AsyncSession, telegram_user) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

async def save_message(session: AsyncSession, user_id: int, text: str, direction: str):
    msg = Message(user_id=user_id, text=text, direction=direction)
    session.add(msg)
    await session.commit()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async for session in get_db():
        user = await ensure_user(session, update.effective_user)
        break
    await update.message.reply_text(
        f"Hello {user.first_name or 'there'}! I'm your Telegram bot connected to Postgres.\n"
        "Send me any message and I'll echo it back.\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/stats - Show your message stats"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async for session in get_db():
        user = await ensure_user(session, update.effective_user)
        total = await session.scalar(
            select(func.count()).where(Message.user_id == user.telegram_id)
        )
        inbound = await session.scalar(
            select(func.count()).where(Message.user_id == user.telegram_id, Message.direction == "in")
        )
        outbound = await session.scalar(
            select(func.count()).where(Message.user_id == user.telegram_id, Message.direction == "out")
        )
        break
    await update.message.reply_text(
        f"Stats for {user.first_name or 'you'}:\n"
        f"Total messages: {total or 0}\n"
        f"Inbound: {inbound or 0}\n"
        f"Outbound: {outbound or 0}"
    )

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    async for session in get_db():
        user = await ensure_user(session, update.effective_user)
        await save_message(session, user.telegram_id, text, "in")
        break
    await update.message.reply_text(f"Echo: {text}")
    async for session in get_db():
        await save_message(session, user.telegram_id, f"Echo: {text}", "out")
        break
