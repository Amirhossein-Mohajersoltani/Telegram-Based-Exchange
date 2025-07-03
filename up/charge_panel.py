from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, ContextTypes, MessageHandler, filters, CommandHandler, CallbackQueryHandler
import common.utilz as cutils
from .utilz import create_user_panel, user_break_conversation
from common.database import Payment, DataBase, User
from common.config import CARD, WALLET

# حذف ایجادِ همزمان DataBase در سطح ماژول
# database = DataBase()

PAYMENT_TYPE, PAYMENT_DOC = range(2)


# --- Start Point ---
async def charge_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    نمایش منوی انتخاب نوع پرداخت و ورود به وضعیت PAYMENT_TYPE.
    """
    context.user_data.clear()

    db: DataBase = context.bot_data["db"]

    # چک می‌کنیم کاربر عضو باشد (متد is_user حالا async است)
    if not await db.is_user(update.message.from_user.id):
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("تتر(USDT)", callback_data="deposit-USDT cp"),
            InlineKeyboardButton("تومان(IRR)", callback_data="deposit-IRR cp")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = cutils.get_dynamic_text("charge-panel")
    await update.message.reply_text(text, reply_markup=reply_markup)
    return PAYMENT_TYPE


async def payment_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    دریافت نوع پرداخت (USDT یا IRR)، ذخیره در context.user_data و هدایت به PAYMENT_DOC.
    """
    await update.callback_query.answer()
    data = update.callback_query.data

    if data == "deposit-USDT cp":
        currency = "USDT"
        text_key = "charge-panel-usdt"
        additional_data = {"{wallet}": WALLET}

    elif data == "deposit-IRR cp":
        currency = "IRR"
        text_key = "charge-panel-irr"
        additional_data = {"{card}": CARD}

    else:
        return ConversationHandler.END

    context.user_data["currency-cp"] = currency

    reply_markup = cutils.create_break_button()
    text = cutils.get_dynamic_text(text_key, additional_data)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
    return PAYMENT_DOC


async def invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    در صورت دریافت ورودی نامعتبر در مرحله PAYMENT_DOC.
    """
    await update.message.reply_text("لطفاً فقط رسید پرداخت را به صورت متن یا عکس ارسال کنید.")
    return PAYMENT_DOC


async def save_payment_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ذخیره‌ی رسید پرداخت در دیتابیس و پایان Conversation.
    """
    db: DataBase = context.bot_data["db"]
    user_id = update.message.from_user.id

    file_id = None
    deposit_text = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    else:
        deposit_text = cutils.convert_numbers(update.message.text.strip())

    payment = Payment(
        db=db,
        trader_id=user_id,
        file_id=file_id,
        deposit_text=deposit_text,
        type="deposit",
        status="pending",
        currency=context.user_data.get("currency-cp"),
        date=datetime.fromisoformat(cutils.current_datetime())
    )
    # متد add_record اکنون async است
    await payment.add_record()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=cutils.get_dynamic_text("payment-doc-sent"),
        reply_markup=create_user_panel()
    )
    return ConversationHandler.END


def get_charge_panel_handler():
    """
    بازگشت یک ConversationHandler با سه state:
    1. PAYMENT_TYPE: انتخاب نوع پرداخت
    2. PAYMENT_DOC: ارسال رسید پرداخت
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("charge", charge_panel),
            MessageHandler(filters.Regex("^شارژ حساب$"), charge_panel)
        ],
        states={
            PAYMENT_TYPE: [
                CallbackQueryHandler(payment_type, pattern=r"^deposit-(USDT|IRR) cp$")
            ],
            PAYMENT_DOC: [
                MessageHandler(filters.Regex("^لغو عملیات!$"), user_break_conversation),
                MessageHandler(filters.PHOTO, save_payment_doc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_payment_doc),
                MessageHandler(filters.ALL, invalid_input)
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )
