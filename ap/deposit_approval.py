import math
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes, MessageHandler, filters

from common.database import DataBase, Payment, User
from common.utilz import is_valid_number, get_dynamic_text, current_datetime
from common.config import PACK_EXCHANGE_RATE

from .utilz import create_admin_panel

# حذف ایجاد مستقیم DataBase در سطح ماژول
# database = DataBase()

# States
UPDATE_MARGIN = range(1)


# --- Start Point ---
async def deposit_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    نمایش اولین واریز در انتظار تایید برای ادمین/مالک.
    """
    db: DataBase = context.bot_data["db"]
    user_model = User(db)

    # چک می‌کنیم که کاربر ادمین یا مالک باشد
    user_id = update.effective_user.id
    if not (await db.is_admin(user_id) or await db.is_owner(user_id)):
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["deposit_approval"] = True

    # خواندن اولین واریز با وضعیت 'pending'
    pending_list = await db.fetch_data("payment", conditions={"status": "pending"})
    if not pending_list:
        text = "هیچ واریزی یافت نشد."
        reply_markup = create_admin_panel()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
        return ConversationHandler.END

    active_deposit = pending_list[0]
    context.user_data["trader_id_da"] = active_deposit["trader_id"]
    context.user_data["deposit_id_da"] = active_deposit["id"]

    keyboard = [
        ["اتمام عملیات!", "رد واریزی!"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # نمایش تصویر یا متن رسید
    if active_deposit["file_id"]:
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=active_deposit["file_id"],
                caption="لطفا مبلغ واریز را به تومان وارد کنید:",
                reply_markup=reply_markup,
            )
        except Exception:
            # اگر ارسال عکس مشکل داشت، متن را بدون عکس ارسال می‌کنیم
            text = f"{active_deposit.get('deposit_text', '')}\n\n\nلطفا مبلغ واریز را به تومان وارد کنید:"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)
    else:
        # اگر عکس ندارد، متن رسید را نشان می‌دهیم
        text = f"{active_deposit.get('deposit_text', '')}\n\n\nلطفا مبلغ واریز را به تومان وارد کنید:"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=reply_markup)

    return UPDATE_MARGIN


# --- UPDATE_MARGIN ---
async def update_margin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این متد وقتی ادمین/مالک مبلغ را ارسال یا رد می‌کند اجرا می‌شود.
    """
    db: DataBase = context.bot_data["db"]
    user_id = update.effective_user.id

    # دکمه "رد واریزی!"
    if update.message.text == "رد واریزی!":
        declined_date = current_datetime()

        payment = Payment(
            db=db,
            status="rejected",
            confirmed_by=user_id,
            confirmation_date=declined_date,
        )
        await payment.update_record(conditions={"id": context.user_data["deposit_id_da"]})

        text_to_user = get_dynamic_text(
            "decline-deposit",
            additional_data={"{date}": declined_date.split("T")[0]},
        )
        await context.bot.send_message(chat_id=context.user_data["trader_id_da"], text=text_to_user)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="واریز رد شد!",
            reply_markup=create_admin_panel(),
        )
        # دوباره به ابتدای تابع باز می‌گردیم تا واریز بعدی را نشان دهیم
        return await deposit_approval(update, context)

    # دکمه "اتمام عملیات!"
    if update.message.text == "اتمام عملیات!":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="عملیات اتمام یافت!",
            reply_markup=create_admin_panel(),
        )
        return ConversationHandler.END

    # در غیر این صورت، فرض می‌کنیم مبلغ را کاربر وارد کرده
    price_text = update.message.text.strip()
    if not is_valid_number(price_text):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="مقدار وارد شده باید یک عدد صحیح باشد. لطفاً مجدداً وجه واریزی را ارسال کنید:",
        )
        return UPDATE_MARGIN

    price = int(price_text)
    approved_date = datetime.fromisoformat(current_datetime())

    # بروزرسانی وضعیت پرداخت
    payment = Payment(
        db=db,
        status="approved",
        confirmed_by=user_id,
        confirmation_date=approved_date,
        deposit_amount=price,
    )
    await payment.update_record(conditions={"id": context.user_data["deposit_id_da"]})

    # بروزرسانی margin و trade_pack برای کاربر
    pack = math.floor(price / PACK_EXCHANGE_RATE)
    user_model = User(db)
    await user_model.update_margin(
        trader_id=context.user_data["trader_id_da"], delta=price
    )
    await user_model.update_trade_pack(
        trader_id=context.user_data["trader_id_da"], pack_delta=pack
    )

    text_to_user = get_dynamic_text(
        "approve-deposit",
        additional_data={
            "{date}": approved_date.isoformat().split("T")[0],
            "{price}": str(price),
        },
    )
    await context.bot.send_message(chat_id=context.user_data["trader_id_da"], text=text_to_user)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="واریز تایید شد!",
        reply_markup=create_admin_panel(),
    )
    # مجدداً شروع مراحل تأیید بعدی
    return await deposit_approval(update, context)


# Pending Approval Conversation Handler
def get_deposit_approval_handler():
    """
    ConversationHandler برای مدیریت صف واریزهای در انتظار تأیید.
    """
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^لیست واریز های در انتظار تایید$"), deposit_approval)
        ],
        states={
            UPDATE_MARGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_margin),
            ],
        },
        fallbacks=[],
    )
