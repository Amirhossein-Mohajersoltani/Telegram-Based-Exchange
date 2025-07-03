from telegram import Update
from telegram.ext import ContextTypes

from common.database import DataBase
from .logic import Logic
from .set_order import SetOrder


__all__ = [
    "Logic", "SetOrder", "Program"
]


class Program:
    def __init__(self, db: DataBase):
        """
        اکنون Program ورودی db (از نوع DataBase) می‌گیرد
        و SetOrder و Logic را با همین db مقداردهی می‌کند.
        """
        self.set_order = SetOrder(db)
        self.logic = Logic(db)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        این متد async است و به ترتیب:
         1. set_order.set_order (که async است) را صدا می‌زند.
         2. logic.make_position (که async است) را صدا می‌زند.
         3. خروجی‌ها را با هم ادغام کرده و برمی‌گرداند.
        """

        commands1 = await self.set_order.set_order(update)
        commands2 = []
        if commands1[0]["status"]:
            commands2 = await self.logic.make_position()

        # فرض می‌کنیم هر دو لیستی از دیکشنری‌ها هستند
        return commands1 + commands2
