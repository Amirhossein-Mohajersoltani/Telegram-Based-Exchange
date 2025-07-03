import datetime as dt

from telegram import ReplyKeyboardMarkup

import common.config as config

# additional_data = {"{model}": model}
# get_dynamic_text("sign-up", additional_data=additional_data)

# Create File if it doesn't exist
def get_dynamic_text(key, additional_data: dict=None):
    if additional_data is None:
        additional_data = {}

    additional_data["{open_day_price}"] = config.OPEN_DAY_PRICE

    text = config.DYNAMIC_TEXT_DEFAULTS[key]["text"]
    vars = config.DYNAMIC_TEXT_DEFAULTS[key]["vars"]
    if additional_data:
        for var in vars:
            text = text.replace(var, str(additional_data.get(var)))

    return text


def current_datetime():
    date = dt.datetime.now().replace(microsecond=0).isoformat()
    return date

def create_break_button():
    keyboard = [
        ["لغو عملیات!"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard,resize_keyboard=True)
    return reply_markup


def convert_numbers(text):
    fa_to_en = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return text.translate(fa_to_en)

def is_valid_number(value):
    return value.isdigit() and int(value) > 0