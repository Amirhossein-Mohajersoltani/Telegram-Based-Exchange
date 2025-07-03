from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

from common.config import DYNAMIC_TEXT_DEFAULTS

# States
SHOW_OPTIONS, GET_NEW_TEXT_DYNAMIC, EDIT_TEXT_DYNAMIC = range(3)

USER_VISIBLE_MESSAGES = {
    "sign-up": "ورود اطلاعات ثبت‌نام",
    "sign-up-success": "ثبت‌نام موفق",
    "charge-panel": "انتخاب روش شارژ",
    "charge-panel-irr": "شارژ با کارت به کارت",
    "charge-panel-usdt": "شارژ با تتر",
    "payment-doc-sent": "ثبت رسید پرداخت",
    "decline-deposit": "رد واریز",
    "approve-deposit": "تأیید واریز",
    "delete-order": "لغو سفارش",
    "delete-orders": "لغو سفارشات",
    "order-cancelled": "سفارش منقضی شده",
    "order-expired": "انقضای سفارش",
    "order-filled": "تکمیل سفارش",
    "volume-overflow": "خطای حجم باقی‌مانده",
    "pack-issue": "کمبود موجودی",
    "simple-position-created": "ایجاد پوزیشن ساده",
    "advance-position-created": "ایجاد پوزیشن حرفه‌ای"
}


# --- Start Point ---
async def dynamic_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    نمایش گزینه‌های تغییر متن برای ادمین/مالک.
    """
    db = context.bot_data["db"]
    from common.database import User
    user_model = User(db)

    user_id = update.effective_user.id
    if not (await user_model.is_admin(user_id) or await user_model.is_owner(user_id)):
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["dynamic_text"] = True

    keyboard = [
        [InlineKeyboardButton(value, callback_data=f"{key} -dt")]
        for key, value in USER_VISIBLE_MESSAGES.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "لطفا پیام مدنظر خود را انتخاب کنید:"

    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

    return GET_NEW_TEXT_DYNAMIC


# --- GET_NEW_TEXT_DYNAMIC ---
async def get_new_text_dynamic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    گرفتن کلید پیام انتخاب‌شده و نمایش متن فعلی برای ویرایش.
    """
    query = update.callback_query
    await query.answer()

    query_data = query.data.split()[0]
    context.user_data["key-part"] = query_data

    # دکمه‌های بازگشت و لغو
    keyboard = [
        [
            InlineKeyboardButton("بازگشت", callback_data="return_show_available_parts_dynamic -dt"),
            InlineKeyboardButton("لغو عملیات", callback_data="cancel -dt")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    current_entry = DYNAMIC_TEXT_DEFAULTS[query_data]
    current_text = current_entry["text"]
    current_vars = current_entry["vars"]

    text = (
        f"{current_text}\n\n"
        f"لطفا متن جدید را وارد کنید:\n\n"
        f"متغیرهای در دسترس:\n{current_vars}"
    )

    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return EDIT_TEXT_DYNAMIC


# --- EDIT_TEXT_DYNAMIC ---
async def edit_text_dynamic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ذخیره‌ی متن جدید یا لغو عملیات.
    """
    # اگر کاربر دکمه لغو را زده باشد
    if update.callback_query and update.callback_query.data == "cancel -dt":
        await update.callback_query.edit_message_text(text="عملیات لغو شد!")
        return ConversationHandler.END

    # اگر کاربر پیام متنی ارسال کرده
    if update.message and update.message.text:
        new_text = update.message.text
        key = context.user_data.get("key-part")
        # به‌روزرسانی در DYNAMIC_TEXT_DEFAULTS
        DYNAMIC_TEXT_DEFAULTS[key]["text"] = new_text

        confirmation = "متن با موفقیت به‌روز شد."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=confirmation)
        return ConversationHandler.END

    return ConversationHandler.END


def dynamic_text_handler():
    """
    ConversationHandler برای مدیریت تغییر متون داینامیک:
    1. SHOW_OPTIONS: انتخاب پیام
    2. GET_NEW_TEXT_DYNAMIC: نمایش متن فعلی و دریافت آن
    3. EDIT_TEXT_DYNAMIC: ذخیره متن جدید یا لغو
    """
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^تغییر محتوای نوشته ها$"), dynamic_text_start)],
        states={
            GET_NEW_TEXT_DYNAMIC: [
                CallbackQueryHandler(get_new_text_dynamic, pattern=r"^.* -dt$")
            ],
            EDIT_TEXT_DYNAMIC: [
                CallbackQueryHandler(dynamic_text_start, pattern=r"^return_show_available_parts_dynamic -dt$"),
                CallbackQueryHandler(edit_text_dynamic, pattern=r"^cancel -dt$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text_dynamic),
            ],
        },
        fallbacks=[],
        allow_reentry=True
    )
