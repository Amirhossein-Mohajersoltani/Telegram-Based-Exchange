from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, ContextTypes, MessageHandler, filters, CommandHandler
import common.utilz as cutils
from .utilz import generate_referral_code, create_user_panel
from common.database import DataBase, User





# Start Point
async def sign_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    # get parent id
    parent_id = None
    if context.args:
        parent_id = context.args[0]
    context.user_data['parent_id'] = parent_id

    text = cutils.get_dynamic_text('sign-up')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)




async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if not username:
        from bots.panel_bot import ADD_USER
        await context.bot.send_message(chat_id=update.effective_chat.id, text="لطفاً یک نام کاربری معتبر وارد کنید.")
        return ADD_USER

    db: DataBase = context.bot_data["db"]
    user = User(
        db=db,
        trader_id=update.message.from_user.id,
        access_level=2,
        username=username,
        margin=0,
        referral_code= await generate_referral_code(db),
        parent_id=context.user_data['parent_id'],
        children=0,
        frozen_pack=0,
        trade_pack=0,
        card_number=None,
        wallet_address=None,
    )
    await user.add_record()

    user_panel = create_user_panel()
    text = cutils.get_dynamic_text('sign-up-success')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=user_panel)
    return ConversationHandler.END




