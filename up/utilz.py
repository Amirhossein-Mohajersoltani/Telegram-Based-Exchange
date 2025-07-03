from telegram import ReplyKeyboardMarkup, Update
from random import choice, shuffle

from telegram.ext import ConversationHandler, ContextTypes

from common.database import DataBase


def create_user_panel():
    keyboards = [
        ["نمایش اطلاعات من", "ویرایش اطلاعات من"],
        ["تسویه موقت", "معاملات"],
        ["کسب درآمد", "گزارش ماهانه"],
        ["ظرفیت خرید و فروش", "صورت حساب"],
        ["قوانین گروه", "شارژ حساب"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard=keyboards, one_time_keyboard=True, resize_keyboard=True)

    return reply_markup

async def user_break_conversation(update:Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    reply_markup = create_user_panel()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="عملیات لغو شد!", reply_markup=reply_markup)
    return ConversationHandler.END



async def generate_referral_code(db: DataBase):


    is_valid_ref = True
    while is_valid_ref:
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']


        password_letters = [choice(letters) for _ in range(10)]
        password_numbers = [choice(numbers) for _ in range(5)]

        password_list = password_letters + password_numbers
        shuffle(password_list)

        referral = "".join(password_list)
        is_valid_ref = not await db.is_valid_referral_code(referral)

    return referral