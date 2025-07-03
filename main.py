import bots.group_bot as group_bot
import bots.panel_bot as panel_bot
import bots.control_updates as control_updates
import asyncio
from common.database import DataBase
from common.config import *


async def main():
    # 1. ساخت Connection Pool
    db = await DataBase.create_pool(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        port=DB_PORT,
        minsize=1,
        maxsize=10
    )

    # 2. راه‌اندازی گروه بات
    group_application = await group_bot.main(db)
    await group_application.initialize()
    await group_application.start()
    await group_application.updater.start_polling()
    print("ربات گروه با موفقیت شروع شد.")

    # 3. راه‌اندازی پنل بات
    panel_application = await panel_bot.main(db)
    await panel_application.initialize()
    await panel_application.start()
    await panel_application.updater.start_polling()
    print("پنل بات با موفقیت شروع شد.")

    # 4. اجرای concurrent تسک کنترل آپدیت‌ها (بدون ارجاع db)
    try:
        await asyncio.gather(
            control_updates.control_updates()
        )
    finally:
        # 5. در پایان، حتماً Pool را ببندید
        await db.close_pool()


if __name__ == '__main__':
    asyncio.run(main())
