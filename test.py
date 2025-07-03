import asyncio
import aiomysql
from prettytable import PrettyTable

# پارامترهای اتصال به MySQL را مطابق تنظیمات خود وارد کنید
DB_CONFIG = {
    "host": "188.34.178.143",
    "port": 3306,
    "user": "amirhossein",
    "password": "g9x76Z!8W]Co1",
    "db": "modem",
    "charset": "utf8mb4",
    "autocommit": True,
    "minsize": 1,
    "maxsize": 5,
}

# لیست نام جداولی که می‌خواهید محتویات‌شان را چاپ کنید
TABLES = [
    "app_users",
    "orders",
    "advance_orders",
    "positions",
    "advance_positions",
    "reply_chain",
    "payment",
    "order_history",
]


async def fetch_and_print_table(pool: aiomysql.Pool, table_name: str):
    """
    این تابع همه رکوردهای table_name را می‌خواند و با استفاده
    از PrettyTable در کنسول چاپ می‌کند.
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # دریافت ستون‌ها
            await cur.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            columns = [row[0] for row in await cur.fetchall()]

            # دریافت تمام رکوردها
            await cur.execute(f"SELECT * FROM `{table_name}`;")
            rows = await cur.fetchall()

            # اگر جدول خالی نباشد، آن را چاپ می‌کنیم
            if columns:
                table = PrettyTable()
                table.field_names = columns
                for row in rows:
                    table.add_row(row)
                print(f"\n=== محتویات جدول `{table_name}` ===")
                print(table)
            else:
                print(f"\nجدول `{table_name}` ستونی ندارد یا وجود ندارد.")


async def main():
    # ایجاد یک اتصال Pool
    pool = await aiomysql.create_pool(**DB_CONFIG)

    # برای هر جدول، محتویاتش را چاپ کن
    for tbl in TABLES:
        try:
            await fetch_and_print_table(pool, tbl)
        except Exception as e:
            print(f"\nخطا در خواندن جدول `{tbl}`: {e}")

    pool.close()
    await pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
