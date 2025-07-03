from telegram import ReplyKeyboardMarkup


def create_admin_panel():
    keyboards = [
        ["نمایش اطلاعات من", "ویرایش اطلاعات من"],
        ["لیست واریز های در انتظار تایید"],
        ["تغییر محتوای نوشته ها"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard=keyboards, one_time_keyboard=True, resize_keyboard=True)

    return reply_markup