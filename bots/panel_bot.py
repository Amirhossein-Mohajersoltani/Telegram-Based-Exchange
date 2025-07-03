import common.config as config
import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import up
import ap

from common.database import DataBase, User

logging.basicConfig(level=logging.INFO)

# States
ADD_USER = range(1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    بررسی نقش کاربر و نمایش پنل مناسب یا
    هدایت به مرحله ثبت‌نام اگر کاربر نباشد.
    """
    db: DataBase = context.bot_data["db"]
    user_model = User(db)
    user_id = update.message.from_user.id

    # اگر مالک است
    if await db.is_owner(user_id):
        return ConversationHandler.END

    # اگر ادمین است
    if await db.is_admin(user_id):
        reply_markup = ap.create_admin_panel()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_markup=reply_markup,
            text=(
                "به ربات معاملاتی ما خوش آمدید\n\n"
                "درصورتی که سوال و یا احتیاج به راهنمایی داشتید، "
                "می‌توانید از طریق پشتیبانی ما را درجریان مشکل خود قرار بدهید:\n@ID_Test"
            ),
        )
        return ConversationHandler.END

    # اگر کاربر عادی است
    if await db.is_user(user_id):
        reply_markup = up.create_user_panel()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_markup=reply_markup,
            text=(
                "به ربات معاملاتی ما خوش آمدید\n\n"
                "درصورتی که سوال و یا احتیاج به راهنمایی داشتید، "
                "می‌توانید از طریق پشتیبانی ما را درجریان مشکل خود قرار بدهید:\n@ID_Test"
            ),
        )
        return ConversationHandler.END

    # اگر در دیتابیس وجود ندارد، به صفحه ثبت‌نام برو
    await up.sign_up(update, context)
    return ADD_USER

async def invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    اگر ورودی در مرحله ثبت‌نام نامعتبر باشد.
    """
    await update.message.reply_text("لطفاً فقط نام کاربری را به صورت متن وارد کنید.")
    return ADD_USER


def sign_up_handler():
    """
    ConversationHandler برای ثبت‌نام کاربر جدید.
    """
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ADD_USER: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), up.add_user),
                MessageHandler(~filters.TEXT, invalid_input),
            ]
        },
        fallbacks=[],
        allow_reentry=True,
    )


async def main(db: DataBase):
    """
    ساخت Application تلگرام و ثبت هندلرهای پنل:
      1. ثبت‌نام
      2. شارژ حساب
      3. تایید واریزی (ادمین)
      4. تغییر متون داینامیک (ادمین)
    """
    app = ApplicationBuilder().token(config.PANEL_BOT_TOKEN).concurrent_updates(True).build()

    # ذخیره‌ی db در bot_data تا تمام هندلرها به آن دسترسی داشته باشند
    app.bot_data["db"] = db

    # User Handlers:
    # 1- signing up
    app.add_handler(sign_up_handler())
    # 2- charge panel
    app.add_handler(up.get_charge_panel_handler())

    # Admin Handlers:
    # 1- Deposit Approval
    app.add_handler(ap.get_deposit_approval_handler())
    # 2- dynamic text handler
    app.add_handler(ap.dynamic_text_handler())

    print("پنل بات در حال اجراست...")
    return app


# اگر این ماژول به‌تنهایی اجرا شود، نیازی به ساخت Pool و فراخوانی main نیست.
# در فایل اصلی باید:
#   db = await DataBase.create_pool(...)
#   panel_app = await panel_bot.main(db)
#   await panel_app.initialize(); await panel_app.start(); await panel_app.updater.start_polling()
