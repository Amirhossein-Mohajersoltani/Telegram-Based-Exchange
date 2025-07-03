from datetime import datetime, timedelta, time

from common.database import (
    DataBase,
    User,
    Order,
    AdvanceOrder,
    Position,
    AdvancePosition,
)
from .utilz import create_message


class Logic:
    def __init__(self, db: DataBase):
        self.db = db
        # در صورتی ‌که نیاز به ذخیره‌سازی‌ موقت داشته باشید:
        self.match_orders_dict = {}

    async def make_position(self):
        """
        این متد تمام سفارش‌های ساده و پیشرفته را می‌یابد،
        آن‌ها را با هم مطابقت می‌دهد و پوزیشن‌های جدید ایجاد می‌کند.
        """
        simple_pos_msgs = await self._match_simple_orders()
        advance_pos_msgs = await self._match_advance_orders()

        print(simple_pos_msgs + advance_pos_msgs)
        print(simple_pos_msgs)
        print(advance_pos_msgs)
        result = simple_pos_msgs + advance_pos_msgs
        # نتیجه به‌صورت لیستی از پیام‌های create_message برگردانده می‌شود
        return result[0] if len(result) == 1 else result

    # === توابع پرکردن جای خالی، بقیه منطق‌های معاملاتی ===
    async def update_trade_pack(self, trader_id: int):
        """
        این متد در صورت لزوم بسته‌های معاملاتی (trade_pack) کاربر را بروزرسانی می‌کند.
        """
        # پیاده‌سازیِ منطق اختصاصی خود را بنویسید
        pass

    async def check_threshold(self, trader_id: int):
        """
        چک کردن آستانه (مثلا حد ضرر یا حد سود) برای کاربر.
        """
        # پیاده‌سازیِ منطق اختصاصی خود را بنویسید
        pass

    async def calculate_swim_pnl(self, trader_id: int):
        """
        محاسبه P&L شناور (معاملات باز) برای کاربر.
        """
        # پیاده‌سازیِ منطق اختصاصی خود را بنویسید
        pass

    async def calculate_exact_pnl(self, trader_id: int):
        """
        محاسبه P&L دقیق (پس از بسته‌شدن پوزیشن) برای کاربر.
        """
        # پیاده‌سازیِ منطق اختصاصی خود را بنویسید
        pass

    async def close_position(self, position_id: int):
        """
        بستن یک پوزیشن مشخص (مثلا انتقال به تاریخچه یا مشتقات دیگر).
        """
        # پیاده‌سازیِ منطق اختصاصی خود را بنویسید
        pass

    def get_trade_date_range(self, now: datetime = None):
        """
        تعیین بازه‌ی معاملاتی (بین ساعت 12:30 دو روز پشت سر هم)
        اگر اکنون بعد از ساعت 12:30 باشد، بازه از ساعت 12:30 امروز تا فردا 12:30 است.
        وگرنه از دیروز 12:30 تا امروز 12:30.
        """
        if now is None:
            now = datetime.now()

        today = now.date()
        base_time = datetime.combine(today, time.min).replace(hour=12, minute=30)

        if now >= base_time:
            start_time = base_time
            end_time = base_time + timedelta(days=1)
        else:
            start_time = base_time - timedelta(days=1)
            end_time = base_time

        return start_time, end_time

    # ------------------------------------------------------------
    async def _match_simple_orders(self):
        """
        مطابق‌سازی سفارش‌های ساده (جدول orders).
        """
        all_orders = await self.db.fetch_data("orders")
        if not all_orders:
            return create_message(False, "no orders exists", "", {})

        simple_positions_msgs = []

        # هر زوج را بررسی می‌کنیم
        for i, base_order in enumerate(all_orders):
            for compared_order in all_orders[i + 1 :]:
                # بررسی شرایط: کاربر متفاوت، نوع مخالف (خرید/فروش)، قیمت یکسان، انقضا یکسان
                different_users = base_order["trader_id"] != compared_order["trader_id"]
                opposite_types = base_order["trade_type"] != compared_order["trade_type"]
                same_price = base_order["order_price"] == compared_order["order_price"]
                same_expiration = base_order["expiration_date"] == compared_order["expiration_date"]

                base_remaining = base_order["order_amount"] - base_order["volume_filled"]
                comp_remaining = compared_order["order_amount"] - compared_order["volume_filled"]

                print(base_order["expiration_order_time"])
                print(type(base_order["expiration_order_time"]))
                # کنترل زمان: زمان انقضای ثبت سفارش اولیه باید بعد از تاریخ ثبت سفارش دوم باشد
                time_valid = (
                    base_order["expiration_order_time"]
                    > compared_order["date"]
                )


                if all(
                    [
                        different_users,
                        opposite_types,
                        same_price,
                        same_expiration,
                        base_remaining > 0,
                        comp_remaining > 0,
                        time_valid,
                    ]
                ):
                    # تعیین خریدار و فروشنده
                    if base_order["trade_type"] == 1:
                        buyer_data, seller_data = base_order, compared_order
                    else:
                        buyer_data, seller_data = compared_order, base_order

                    # ایجاد پوزیشن جدید
                    position = Position(
                        self.db,
                        seller_id=seller_data["trader_id"],
                        buyer_id=buyer_data["trader_id"],
                        open_price=buyer_data["order_price"],
                        position_amount=min(
                            buyer_data["order_amount"] - buyer_data["volume_filled"],
                            seller_data["order_amount"] - seller_data["volume_filled"],
                        ),
                        expiration_date=buyer_data["expiration_date"],
                    )
                    created_position = await position.add_record()

                    # به‌روزرسانی سفارش‌ها (volume_filled)
                    await self._update_orders_simple_position(buyer_data, seller_data, created_position["position_amount"])

                    # به‌روزرسانی frozen_pack برای خریدار و فروشنده
                    await self._update_trader_frozen_pack_after_make_position(seller_data["trader_id"])
                    await self._update_trader_frozen_pack_after_make_position(buyer_data["trader_id"])

                    # دریافت نام‌ها و ارسال پیام نهایی
                    seller_name = await User(self.db).get_name(created_position["seller_id"])
                    buyer_name = await User(self.db).get_name(created_position["buyer_id"])
                    additional_data = {
                        "{seller_name}": seller_name,
                        "{buyer_name}": buyer_name,
                        "{position_amount}": created_position["position_amount"],
                        "{open_price}": created_position["open_price"],
                        "{date}": created_position["date"],
                        "{expiration_date}": created_position["expiration_date"],
                    }
                    pos_message = create_message(
                        True,
                        "position had been created",
                        "simple-position-created",
                        additional_data,
                        command="send-message",
                    )
                    simple_positions_msgs += pos_message

        return simple_positions_msgs

    # ------------------------------------------------------------
    async def _match_advance_orders(self):
        """
        مطابق‌سازی سفارش‌های پیشرفته (جدول advance_orders).
        """
        all_adv_orders = await self.db.fetch_data("advance_orders")
        if not all_adv_orders:
            return create_message(False, "no orders exists", "", {}, command="nothing")

        advance_positions_msgs = []

        for i, base_order in enumerate(all_adv_orders):
            for compared_order in all_adv_orders[i + 1 :]:
                # بررسی شرایط: زوجِ خریدار/فروشنده (یکی seller_id و دیگری buyer_id)، قیمت باز و قیمت بسته‌ شدن یکسان، انقضا یکسان
                match_traders = (
                    (base_order["seller_id"] is not None and compared_order["buyer_id"] is not None)
                    or (base_order["buyer_id"] is not None and compared_order["seller_id"] is not None)
                )
                different_traders = (
                    base_order["seller_id"] != compared_order["buyer_id"]
                    or base_order["buyer_id"] != compared_order["seller_id"]
                )
                same_open_price = base_order["open_price"] == compared_order["open_price"]
                same_close_price = base_order["close_price"] == compared_order["close_price"]
                same_expiration = base_order["expiration_date"] == compared_order["expiration_date"]

                base_remaining = base_order["order_amount"] - base_order["volume_filled"]
                comp_remaining = compared_order["order_amount"] - compared_order["volume_filled"]

                time_valid = (
                    base_order["expiration_order_time"]
                    > compared_order["date"]
                )

                if all(
                    [
                        match_traders,
                        different_traders,
                        same_open_price,
                        same_close_price,
                        same_expiration,
                        base_remaining > 0,
                        comp_remaining > 0,
                        time_valid,
                    ]
                ):
                    # تعیین خریدار و فروشنده
                    if base_order["buyer_id"] is not None:
                        buyer_data, seller_data = base_order, compared_order
                    else:
                        buyer_data, seller_data = compared_order, base_order

                    # ایجاد پوزیشن جدید
                    advance_position = AdvancePosition(
                        self.db,
                        seller_id=seller_data["seller_id"],
                        buyer_id=buyer_data["buyer_id"],
                        open_price=buyer_data["open_price"],
                        close_price=seller_data["close_price"],
                        position_amount=min(
                            buyer_data["order_amount"] - buyer_data["volume_filled"],
                            seller_data["order_amount"] - seller_data["volume_filled"],
                        ),
                        expiration_date=buyer_data["expiration_date"],
                    )
                    created_position = await advance_position.add_record()

                    # به‌روزرسانی سفارش‌ها (volume_filled)
                    await self._update_orders_advance_position(buyer_data, seller_data, created_position["position_amount"])

                    # به‌روزرسانی frozen_pack برای خریدار و فروشنده
                    await self._update_trader_frozen_pack_after_make_position(seller_data["seller_id"])
                    await self._update_trader_frozen_pack_after_make_position(buyer_data["buyer_id"])

                    # دریافت نام‌ها و ارسال پیام نهایی
                    seller_name = await User(self.db).get_name(created_position["seller_id"])
                    buyer_name = await User(self.db).get_name(created_position["buyer_id"])
                    additional_data = {
                        "{seller_name}": seller_name,
                        "{buyer_name}": buyer_name,
                        "{position_amount}": created_position["position_amount"],
                        "{open_price}": created_position["open_price"],
                        "{close_price}": created_position["close_price"],
                        "{date}": created_position["date"],
                        "{expiration_date}": created_position["expiration_date"],
                    }
                    pos_message = create_message(
                        True,
                        "position had been created",
                        "advance-position-created",
                        additional_data,
                        command="send-message",
                    )
                    advance_positions_msgs+=pos_message

        return advance_positions_msgs

    # ------------------------------------------------------------
    async def _update_orders_simple_position(self, buyer, seller, position_amount: int):
        """
        وقتی پوزیشن برای سفارش‌های ساده ساخته می‌شود،
        مقدار volume_filled را در هر دو سفارش (خریدار و فروشنده) به‌روز کنید.
        """
        new_buyer_filled = buyer["volume_filled"] + position_amount
        new_seller_filled = seller["volume_filled"] + position_amount

        # به‌روزرسانی ردیف خریدار
        buyer_order = Order(
            self.db,
            volume_filled=new_buyer_filled,
        )
        await buyer_order.update_record({"id": buyer["id"]})

        # به‌روزرسانی ردیف فروشنده
        seller_order = Order(
            self.db,
            volume_filled=new_seller_filled,
        )
        await seller_order.update_record({"id": seller["id"]})

    # ------------------------------------------------------------
    async def _update_orders_advance_position(self, buyer, seller, position_amount: int):
        """
        وقتی پوزیشن برای سفارش‌های پیشرفته ساخته می‌شود،
        مقدار volume_filled را در هر دو سفارش (خریدار و فروشنده) به‌روز کنید.
        """
        new_buyer_filled = buyer["volume_filled"] + position_amount
        new_seller_filled = seller["volume_filled"] + position_amount

        buyer_order = AdvanceOrder(
            self.db,
            volume_filled=new_buyer_filled,
        )
        await buyer_order.update_record({"id": buyer["id"]})

        seller_order = AdvanceOrder(
            self.db,
            volume_filled=new_seller_filled,
        )
        await seller_order.update_record({"id": seller["id"]})

    # ------------------------------------------------------------
    async def _update_trader_frozen_pack_after_make_position(self, trader_id: int):
        """
        بعد از ایجاد یک پوزیشن (چه ساده چه پیشرفته)،
        frozen_pack را بر اساس مجموع position_amountهای باز برای آن کاربر کاهش دهید.
        """
        # اول، همه پوزیشن‌های فروشی و خریدی که کاربر در آن نقش دارد را بگیرید
        sell_positions = await Position(self.db).fetch_data({"seller_id": trader_id})
        buy_positions = await Position(self.db).fetch_data({"buyer_id": trader_id})

        total_sell = sum(pos["position_amount"] for pos in sell_positions) if sell_positions else 0
        total_buy = sum(pos["position_amount"] for pos in buy_positions) if buy_positions else 0

        reduction_pack = min(total_sell, total_buy)

        trader = User(self.db)
        trader_info = (await trader.fetch_data({"trader_id": trader_id}))[0]
        new_frozen = max(0, trader_info["frozen_pack"] - reduction_pack)

        trader.frozen_pack = new_frozen
        await trader.update_record({"trader_id": trader_id})
