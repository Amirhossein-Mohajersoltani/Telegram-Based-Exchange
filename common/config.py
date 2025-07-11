# config.py
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")          # string
DB_USER = os.getenv("DB_USER")          # string
DB_PASSWORD = os.getenv("DB_PASSWORD")  # string
DB_NAME = os.getenv("DB_NAME")          # string

DB_PORT = int(os.getenv("DB_PORT", 3306))  # int



PANEL_BOT_TOKEN = os.getenv("PANEL_BOT_TOKEN")
GROUP_BOT_TOKEN = os.getenv('GROUP_BOT_TOKEN')


# Payment info
CARD = "123456"
WALLET = "123456"



CURRENT_TIME = ""
CURRENT_DATE = ""



# price info
BASE_PRICE = ""
PRICE_BOUND_RATE = 2000
CURRENT_PRICE = 0
OPEN_DAY_PRICE = 0
PRICE_UPPER_BOUND = 0
PRICE_LOWER_BOUND = 0



PACK_AMOUNT = 50000
THRESHOLD = 20


PACK_EXCHANGE_RATE = 2000000


IS_GAME_ON = True




DYNAMIC_TEXT_DEFAULTS = {
    "sign-up":
        {
            "text": "ثبت نام-نام خانوادگی را وارد کنید",
            "vars": ["{open_day_price}"]
        },
    "sign-up-success":
        {
            "text": "ثبت نام با موفقیت انجام شد.",
            "vars": ["{open_day_price}"]
        },
    "charge-panel":
        {
            "text": "لطفا نوع پرداختی را مشخص کنید:",
            "vars": ["{open_day_price}"]
        },
    "charge-panel-irr":
        {
            "text": "لطفا کارت به کارت کنید{card}",
            "vars": ["{card}","{open_day_price}"]
        },
    "charge-panel-usdt":
        {
            "text": "لطفا مبلغ مورد نظر را به آدرس زیر واریز کنید و رسید آن را ارسال کنید: {wallet}",
            "vars": ["{wallet}","{open_day_price}"]
        },
    "payment-doc-sent":
        {
            "text": "رسید شما ارسال شد و به زودی نتیجه آن توسط ادمین تایید می شود",
            "vars": ["{open_day_price}"]
        },
    "decline-deposit":
        {
            "text": "واریز شما در تاریخ {date} رد شد",
            "vars": ["{date}","{open_day_price}"]
        },
    "approve-deposit":
        {
            "text": "واریز شما در تاریخ {date} به مبلغ {price} تومان تایید شد",
            "vars": ["{date}","{price}","{open_day_price}"]
        },
    "delete-order":
        {
            "text": "{name}محترم سفارش شما کنسل شد ",
            "vars": ["{name}","{open_day_price}"]
        },
    "delete-orders":
        {
            "text": "{name}محترم سفارشات شما کنسل شد ",
            "vars": ["{name}","{open_day_price}"]
        },
    "order-cancelled":
        {
            "text": "سفارش منقضی شده است",
            "vars": ["{open_day_price}"]
        },
    "order-expired":
        {
            "text": "تایم",
            "vars": ["{open_day_price}"]
        },
    "order-filled":
        {
            "text": "تکمیل",
            "vars": ["{open_day_price}"]
        },
    "volume-overflow":
        {
            "text": "حجم باقی مانده: {remainder}",
            "vars": ["{remainder}","{open_day_price}"]
        },
    "pack-issue":
        {
            "text": "عدم موجودی",
            "vars": ["{open_day_price}"]
        },
    "simple-position-created":
        {
            "text": "پوزیشن ساده ایجاد شد",
            "vars": ["{seller_name}","{buyer_name}","{position_amount}","{open_price}","{date}","{expiration_date}","{open_day_price}"]
        },
    "advance-position-created":
        {
            "text": "پوزیشن حرفه ای ایجاد شد",
            "vars": ["{seller_name}","{buyer_name}","{position_amount}","{open_price}","{close_price}","{date}","{expiration_date}","{open_day_price}"]
        }
}

