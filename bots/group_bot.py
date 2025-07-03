import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from common.utilz import get_dynamic_text
from program import Program

import common.config as config
from common.database import DataBase, User  # Import async DataBase and User


TOKEN = config.GROUP_BOT_TOKEN

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{update.effective_user.id}")


async def mirror_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این هندلر پیام‌های گروه را می‌گیرد و اگر بازی فعال باشد
    و کاربر در جدول users باشد، پیام را به Program می‌سپارد؛
    در غیر این صورت پیام کاربر را حذف می‌کند.
    """
    db: DataBase = context.bot_data["db"]
    user_model = User(db)

    # چک می‌کنیم که بازی فعال باشد و کاربر نقش 'user' داشته باشد:
    if config.IS_GAME_ON and await db.is_user(update.effective_user.id):
        # اکنون که db را در bot_data داریم، Program را هم از bot_data می‌خوانیم
        program: Program = context.bot_data["program"]
        commands = await program.handle_message(update, context)
        for com in commands:
            print(com)
            key = com["key"]
            additional_data = com["additional_data"]
            status = com["status"]
            status_info = com["status_info"]
            print(status)
            print(status_info)
            command = com["command"]

            if command == "reply-message":
                message = get_dynamic_text(key, additional_data)
                await update.message.reply_text(message)

            elif command == "send-message":
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=get_dynamic_text(key, additional_data),
                )

            elif command == "delete-message":
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.effective_message.message_id,
                )

    else:
        # اگر بازی فعال نیست یا کاربر در جدول users نیست، پیام را حذف می‌کنیم
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
        )


async def main(db: DataBase):
    """
    این تابع یک Application تلگرام می‌سازد و شیء دیتابیس async را در bot_data نگه می‌دارد.
    """
    # ساخت یک Application با اجازه‌ی پردازش هم‌زمان (concurrent_updates=True)
    app = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()

    # ذخیره‌ی db در bot_data تا در هندلرها قابل دسترسی باشد
    app.bot_data["db"] = db

    # ساخت Program و ذخیره در bot_data
    app.bot_data["program"] = Program(db)

    # هندلرها را ثبت می‌کنیم
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, mirror_message))

    print("ربات گروه در حال اجراست...")
    return app
