import math
import re
from datetime import datetime, time

from telegram import Update
import common.config as config
from common.database import DataBase, User, Order, AdvanceOrder, ReplyChain
from common.utilz import convert_numbers
from .utilz import create_message


class SetOrder:
    def __init__(self, db: DataBase):
        self.db = db

    async def set_order(self, update: Update):
        text = convert_numbers(update.message.text.strip())
        replied_message = update.message.reply_to_message

        advance_order = re.search(r"^(\d+)\s*ب\s*(\d+)\s*(خپ|خب|فپ|فب|فمع|خمع|خش|فش)\s*(\d+)?$", text)
        simple_order = re.search(r"^(\d+)\s*(خف|فف|خ|ف)\s*(\d+)?$", text)
        b_order = re.search(r"^(ب)?\s*(\d+)?$", text)

        result = create_message(False, "invalid_message", "", {})
        if advance_order:
            result = await self._advance_order(advance_order, update)
        elif simple_order:
            result = await self._simple_order(simple_order, update)
        elif b_order and replied_message:
            result = await self._b_order(b_order, update, replied_message)
        elif text == "ن" and replied_message:
            result = await self._cancel_one_order(update)
        elif text == "ن" and not replied_message:
            result = await self._cancel_all_orders(update)

        return result

    # ------------------------------------------------------------
    async def _cancel_one_order(self, update: Update):
        message_id = update.message.reply_to_message.message_id
        trader_id = update.message.from_user.id

        # ابتدا در جدول orders بگردیم
        order = await self.db.get_order_by_message_id("orders", message_id)
        order_table = "orders"

        # اگر پیدا نشد، در advance_orders بگرد
        if not order:
            order = await self.db.get_order_by_message_id("advance_orders", message_id)
            order_table = "advance_orders"

        # اگر پیدا نشد یا متعلق به کاربر نیست
        if not order or trader_id not in (
            order.get("trader_id"),
            order.get("buyer_id"),
            order.get("seller_id"),
        ):
            return create_message(False, "order_not_found", "", {}, command="delete-message")

        # حذف سفارش
        await self.db.delete_record(order_table, {"message_id": message_id})

        # حذف reply_chainهای مرتبط
        await self.db.delete_record("reply_chain", {"order_message_id": message_id})

        # آزادسازی بسته‌ی فریز شده
        user = User(self.db)
        user_data = (await user.fetch_data({"trader_id": trader_id}))[0]

        order_amount = order.get("order_amount", 0)
        volume_filled = order.get("volume_filled", 0)
        frozen_release = order_amount - volume_filled

        user.frozen_pack = max(0, user_data["frozen_pack"] - frozen_release)
        await user.update_record({"trader_id": trader_id})

        name = await user.get_name(trader_id)
        return create_message(True, "order deleted", key="delete-order", additional_data={"{name}": name}, command="reply-message")

    # ------------------------------------------------------------
    async def _cancel_all_orders(self, update: Update):
        trader_id = update.message.from_user.id
        total_frozen_release = 0

        # سفارش‌های معمولی
        normal_orders = await self.db.fetch_data("orders", {"trader_id": trader_id})
        for order in normal_orders:
            frozen_release = max(0, order["order_amount"] - order["volume_filled"])
            total_frozen_release += frozen_release
            await self.db.delete_record("orders", {"message_id": order["message_id"]})

        # سفارش‌های پیشرفته (advance_orders)
        adv_buy = await self.db.fetch_data("advance_orders", {"buyer_id": trader_id})
        adv_sell = await self.db.fetch_data("advance_orders", {"seller_id": trader_id})
        advanced_orders = adv_buy + adv_sell
        for order in advanced_orders:
            if order.get("seller_id") == trader_id or order.get("buyer_id") == trader_id:
                frozen_release = max(0, order["order_amount"] - order["volume_filled"])
                total_frozen_release += frozen_release
                await self.db.delete_record("advance_orders", {"message_id": order["message_id"]})

        # حذف ReplyChain کاربر
        reply_chain = ReplyChain(self.db)
        await reply_chain.delete_record({"trader_id": trader_id})

        # آزادسازی بسته‌ها
        if total_frozen_release > 0:
            user = User(self.db)
            user_data = (await user.fetch_data({"trader_id": trader_id}))[0]
            user.frozen_pack = max(0, user_data["frozen_pack"] - total_frozen_release)
            await user.update_record({"trader_id": trader_id})

        name = await User(self.db).get_name(trader_id)
        return create_message(True, "all orders cancelled", "delete-orders", {"{name}": name}, command="reply-message")

    # ------------------------------------------------------------
    async def _b_order(self, b_order, update: Update, replied_message):
        trader_id = update.message.from_user.id
        message_id = update.message.message_id
        order_id = replied_message.message_id
        order_amount = None
        order_table = None
        check_expiration = True

        if trader_id == replied_message.from_user.id:
            return create_message(False, "same traders", "", {}, command="delete-message")

        # در بخش Indirect Address
        if convert_numbers(update.message.text.strip()) == "ب" and re.match(r"^(ب)?\s*(\d*)?$", convert_numbers(replied_message.text)):
            reply_chain = ReplyChain(self.db)
            result = await reply_chain.fetch_data({"message_id": order_id})
            if result:
                order_id = result[0]["order_message_id"]
                order_table = result[0]["order_table"]
                order_amount = result[0]["order_amount"]
                trader_id = result[0]["trader_id"]
                check_expiration = False
            else:
                return create_message(False, "order cancelled", "order-cancelled", {}, command="reply-message")

        # بخش direct address
        if re.search(r"^(\d+)\s*ب\s*(\d+)\s*(خپ|خب|فپ|فب|فمع|خمع|خش|فش)\s*(\d+)?$", convert_numbers(replied_message.text)):
            order_table = "advance_orders"
        elif re.search(r"^(\d+)\s*(خف|فف|خ|ف)\s*(\d+)?$", convert_numbers(replied_message.text)):
            order_table = "orders"

        # پیدا کردن سفارش اصلی
        original_order = await self.db.get_order_by_message_id(order_table, order_id)
        if original_order:
            original_remain = original_order["order_amount"] - original_order["volume_filled"]
            if order_amount:
                pass
            elif b_order.group(2):
                order_amount = int(b_order.group(2))
            else:
                order_amount = original_remain

            if not check_expiration:
                if order_table == "advance_orders":
                    original_trader_id = original_order["buyer_id"] if original_order["buyer_id"] is not None else original_order["seller_id"]
                else:
                    original_trader_id = original_order["trader_id"]
                if update.message.from_user.id != original_trader_id:
                    return create_message(False, "another trader reply b with melodious activity", "", {}, command="delete-message")

            current_time = datetime.now()
            expiration_time = original_order["expiration_order_time"]
            if current_time > expiration_time and check_expiration:
                reply_chain = ReplyChain(self.db,
                                         trader_id=trader_id,
                                         message_id=message_id,
                                         order_table=order_table,
                                         order_amount=order_amount,
                                         order_message_id=original_order["message_id"])
                await reply_chain.add_record()
                return create_message(False, "order_expired", "order-expired", {}, command="reply-message")

            if original_remain == 0:
                return create_message(False, "order_filled", "order-filled", {}, command="reply-message")

            if order_amount > original_remain:
                return create_message(False, "volume_overflow", "volume-overflow", {"{remainder}": original_remain}, command="reply-message")

            # چک پک
            if order_table == "orders":
                is_available, _ = await self._check_and_increment_order_amount(trader_id, order_amount)
            else:
                is_available, _ = await self._check_advance_order_validation(
                    buyer_id=None if original_order["buyer_id"] else trader_id,
                    seller_id=None if original_order["seller_id"] else trader_id,
                    order_amount=order_amount,
                    open_price=original_order["open_price"],
                    close_price=original_order["close_price"]
                )
            if not is_available:
                return create_message(False, "pack issue", "pack-issue", {}, command="reply-message")

            # ثبت سفارش جدید
            if order_table == "advance_orders":
                adv = AdvanceOrder(
                    self.db,
                    seller_id=None if original_order["seller_id"] else trader_id,
                    buyer_id=None if original_order["buyer_id"] else trader_id,
                    message_id=message_id,
                    open_price=original_order["open_price"],
                    close_price=original_order["close_price"],
                    order_amount=order_amount,
                    volume_filled=0,
                    expiration_date=original_order["expiration_date"],
                    date=original_order["date"]
                )
                await adv.add_record()
            else:  # orders
                ord_obj = Order(
                    self.db,
                    trader_id=trader_id,
                    message_id=message_id,
                    trade_type=(original_order["trade_type"] == 0),
                    order_price=original_order["order_price"],
                    expiration_date=original_order["expiration_date"],
                    order_amount=order_amount,
                    volume_filled=0,
                    date=original_order["date"],
                )
                await ord_obj.add_record()

            # اگر سوابق reply_chain وجود داشت، پاکش کن
            if 'reply_chain' in locals():  # در واقع اگر تعریف شده بود
                await reply_chain.delete_record({"message_id": replied_message.message_id})

            return create_message(True, "success")

        return create_message(False, "order_cancelled", "order-cancelled", {}, command="reply-message")

    # ------------------------------------------------------------
    async def _advance_order(self, advance_order_match, update: Update):
        trader_id = update.message.from_user.id
        message_id = update.message.message_id

        order_type = advance_order_match.group(3)
        order_amount = int(advance_order_match.group(4)) if advance_order_match.group(4) else 1

        if len(advance_order_match.group(1)) == 3:
            open_price = int(config.BASE_PRICE + advance_order_match.group(1))
        else:
            open_price = int(advance_order_match.group(1))
        if len(advance_order_match.group(2)) == 3:
            close_price = int(config.BASE_PRICE + advance_order_match.group(2))
        else:
            close_price = int(advance_order_match.group(2))

        # اعتبارسنجی قیمت
        if open_price > close_price:
            return create_message(False, "invalid_price", command="delete-message")
        if not (config.PRICE_LOWER_BOUND <= open_price <= config.PRICE_UPPER_BOUND):
            return create_message(False, "price_outside", command="delete-message")
        if not (config.PRICE_LOWER_BOUND <= close_price <= config.PRICE_UPPER_BOUND):
            return create_message(False, "price_outside", command="delete-message")

        buyer_id = None
        seller_id = None
        if order_type in ("فمع", "فپ", "خش", "خب"):
            seller_id = trader_id
        else:
            buyer_id = trader_id

        is_available, _ = await self._check_advance_order_validation(
            buyer_id=buyer_id,
            seller_id=seller_id,
            order_amount=order_amount,
            open_price=open_price,
            close_price=close_price,
        )
        if not is_available:
            return create_message(False, "pack issue", "pack-issue", command="reply-message")

        adv_order = AdvanceOrder(
            self.db,
            seller_id=seller_id,
            buyer_id=buyer_id,
            message_id=message_id,
            open_price=open_price,
            close_price=close_price,
            order_amount=order_amount,
            volume_filled=0
        )
        await adv_order.add_record()
        return create_message(True, "success")

    # ------------------------------------------------------------
    async def _simple_order(self, simple_order_match, update: Update):
        trader_id = update.message.from_user.id
        message_id = update.message.message_id

        if len(simple_order_match.group(1)) == 3:
            open_price = int(config.BASE_PRICE + simple_order_match.group(1))
        else:
            open_price = int(simple_order_match.group(1))


        print(config.PRICE_UPPER_BOUND)
        print(config.PRICE_LOWER_BOUND)
        print(open_price)
        if not (config.PRICE_LOWER_BOUND <= open_price <= config.PRICE_UPPER_BOUND):
            return create_message(False, "price_outside", command="delete-message")

        type_char = simple_order_match.group(2)
        order_amount = int(simple_order_match.group(3)) if simple_order_match.group(3) else 1

        # اعتبارسنجی زمان برای خف/فف
        if type_char in ("خف", "فف"):
            now = datetime.now().time()
            start = time(11, 30)
            end = time(12, 30)
            tomorrow_contract = start <= now < end
            if not tomorrow_contract:
                return create_message(False, "tomorrow_contract_time_invalid", command="delete-message")

        needs_extra_day = None
        trade_type = None
        if type_char in ("فف", "ف"):
            trade_type = False
            if type_char == "فف":
                needs_extra_day = True
        elif type_char in ("خف", "خ"):
            trade_type = True
            if type_char == "خف":
                needs_extra_day = True

        is_available, _ = await self._check_and_increment_order_amount(trader_id, order_amount)
        if not is_available:
            return create_message(False, "pack issue", "pack-issue", command="reply-message")

        order = Order(
            self.db,
            trader_id=trader_id,
            message_id=message_id,
            trade_type=trade_type,
            order_price=open_price,
            needs_extra_day=needs_extra_day,
            order_amount=order_amount,
            volume_filled=0
        )
        await order.add_record()
        return create_message(True, "success")

    # ------------------------------------------------------------
    async def _check_and_increment_order_amount(self, trader_id, amount):
        trader = User(self.db)
        trader_data = (await trader.fetch_data({"trader_id": trader_id}))[0]
        available_pack = trader_data["trade_pack"] - trader_data["frozen_pack"]
        if available_pack >= amount:
            trader.frozen_pack = trader_data["frozen_pack"] + amount
            await trader.update_record({"trader_id": trader_id})
            return True, "success"
        return False, "pack_issue"

    # ------------------------------------------------------------
    async def _check_advance_order_validation(self, buyer_id=None, seller_id=None, order_amount=None, open_price=None, close_price=None):
        trader_id = buyer_id if buyer_id else seller_id
        loss = (order_amount * config.PACK_AMOUNT) * (close_price - open_price)
        if buyer_id:
            loss *= 2

        trader = User(self.db)
        trader_info = (await trader.fetch_data({"trader_id": trader_id}))[0]
        available_pack = trader_info["trade_pack"] - trader_info["frozen_pack"]
        frozen_pack = math.ceil(loss / config.PACK_EXCHANGE_RATE)
        if available_pack >= frozen_pack:
            trader.frozen_pack = trader_info["frozen_pack"] + frozen_pack
            await trader.update_record({"trader_id": trader_id})
            return True, "success"
        return False, "pack_issue"
