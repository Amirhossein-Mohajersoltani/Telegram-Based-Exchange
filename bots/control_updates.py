from bs4 import BeautifulSoup
import requests
import common.config as config
import datetime as dt
import asyncio



def set_price_info():
    # Update Price Info
    response = requests.get("https://www.tgju.org/profile/afghan_usd")
    html_doc = response.text


    soup = BeautifulSoup(html_doc, 'html.parser')
    current_price = soup.select(selector="#main > div.stocks-profile > div.stocks-header > div.stocks-header-main > div > div.fs-cell.fs-xl-3.fs-lg-3.fs-md-6.fs-sm-12.fs-xs-12.top-header-item-block-2.mobile-top-item-hide > div > h3.line.clearfix.mobile-hide-block > span.value > span:nth-child(1)")[0].get_text()
    current_price = current_price.replace(',', '')[0:5]
    config.BASE_PRICE = current_price[0:2]
    current_price = int(current_price)
    print(current_price)


    try:
        open_day_price = soup.select(selector="#main > div.stocks-profile > div.fs-row.bootstrap-fix.widgets.full-w-set.profile-social-share-box > div.row.tgju-widgets-row > div.tgju-widgets-block.col-md-12.col-lg-4.tgju-widgets-block-bottom-unset.overview-first-block > div > div:nth-child(2) > div > div.tables-default.normal > table > tbody > tr:nth-child(6) > td.text-left")[0].get_text()
        open_day_price = int(open_day_price.replace(',', '')[0:5])
        print(open_day_price)
        config.OPEN_DAY_PRICE = open_day_price
    except ValueError:
        config.OPEN_DAY_PRICE = current_price
        open_day_price = current_price

    config.CURRENT_PRICE = current_price

    config.PRICE_UPPER_BOUND = open_day_price + config.PRICE_BOUND_RATE
    config.PRICE_LOWER_BOUND = open_day_price - config.PRICE_BOUND_RATE


    print(config.PRICE_UPPER_BOUND)
    print(config.PRICE_LOWER_BOUND)


def set_datetime():
    now = dt.datetime.now()

    current_time = now.time().replace(microsecond=0).isoformat()
    current_date = now.date().isoformat()


    config.CURRENT_TIME = current_time
    config.CURRENT_DATE = current_date


async def control_updates():
    while True:
        set_price_info()
        set_datetime()
        # config.IS_GAME_ON = True if 22 > int(config.CURRENT_TIME.split(":")[0]) >= 8 else False
        await asyncio.sleep(10)




