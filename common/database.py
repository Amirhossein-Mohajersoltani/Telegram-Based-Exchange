from typing import Dict, Any

import aiomysql
from datetime import datetime, timedelta

class DataBase:
    """
    Async base class for MySQL operations using aiomysql pool.
    """

    def __init__(self, pool: aiomysql.Pool):
        self._pool = pool

    @classmethod
    async def create_pool(
        cls,
        host: str,
        user: str,
        password: str,
        db: str,
        port: int = 3306,
        minsize: int = 1,
        maxsize: int = 10,
        charset: str = "utf8mb4",
        autocommit: bool = True,
    ) -> "DataBase":
        """
        Initialize and return a DataBase instance with an aiomysql pool.
        """
        pool = await aiomysql.create_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            db=db,
            minsize=minsize,
            maxsize=maxsize,
            charset=charset,
            autocommit=autocommit,
        )
        return cls(pool)

    async def close_pool(self):
        """
        Gracefully close the connection pool.
        """
        self._pool.close()
        await self._pool.wait_closed()

    async def add_record(self, table: str, record_obj) -> int:
        """
        Insert a new record into `table`. The object's __dict__ is filtered
        to ignore None values and internal attributes.
        Returns the last inserted ID.
        """
        # Filter out None values and internal attrs
        exclude_fields = {"_pool","db"}
        data = {
            k: v
            for k, v in record_obj.__dict__.items()
            if v is not None and k not in exclude_fields
        }

        if not data:
            raise ValueError("No data fields provided for insertion.")

        columns = ", ".join(f"`{col}`" for col in data.keys())
        placeholders = ", ".join("%s" for _ in data)
        values = tuple(data.values())

        query = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders});"

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, values)
                last_id = cur.lastrowid
                return last_id

    async def fetch_data(self, table: str, conditions: dict = None) -> list[dict]:
        """
        Fetch rows from `table` matching all key=value in conditions.
        If conditions is None or empty, fetches all rows.
        Returns a list of dicts.
        """
        if conditions:
            where_clauses = " AND ".join(f"`{k}`=%s" for k in conditions.keys())
            sql = f"SELECT * FROM `{table}` WHERE {where_clauses};"
            params = tuple(conditions.values())
        else:
            sql = f"SELECT * FROM `{table}`;"
            params = ()

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
                return [dict(row) for row in rows]

    async def update_record(
        self, table: str, conditions: dict, new_values: dict
    ) -> None:
        """
        UPDATE `table` SET new_values WHERE conditions.
        Only non-None values in new_values are applied.
        """
        filtered = {k: v for k, v in new_values.items() if v is not None}
        if not filtered:
            return  # Nothing to update

        set_clause = ", ".join(f"`{k}`=%s" for k in filtered.keys())
        where_clause = " AND ".join(f"`{k}`=%s" for k in conditions.keys())
        sql = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause};"
        params = tuple(filtered.values()) + tuple(conditions.values())

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)

    async def delete_record(self, table: str, conditions: dict) -> None:
        """
        DELETE FROM `table` WHERE conditions.
        """
        where_clause = " AND ".join(f"`{k}`=%s" for k in conditions.keys())
        sql = f"DELETE FROM `{table}` WHERE {where_clause};"
        params = tuple(conditions.values())

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)

    # ---------------------------------------------------------------------------
    # Role/Access control methods
    # ---------------------------------------------------------------------------

    async def get_access_level(self, user_id: int) -> int:
        """
        Returns the access_level of a user (or 0 if none found).
        """
        sql = "SELECT `access_level` FROM `app_users` WHERE `trader_id`=%s;"
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (user_id,))
                row = await cur.fetchone()
                return int(row["access_level"]) if row else 0

    async def has_role(self, user_id: int, required_level: int) -> bool:
        level = await self.get_access_level(user_id)
        return level == required_level

    async def is_user(self, user_id: int) -> bool:
        return await self.has_role(user_id, 1)

    async def is_admin(self, user_id: int) -> bool:
        return await self.has_role(user_id, 2)

    async def is_owner(self, user_id: int) -> bool:
        return await self.has_role(user_id, 3)

    async def is_valid_referral_code(self, ref_code: str) -> bool:
        """
        Checks if ref_code exists in app_users.referral_code.
        Returns True if code is NOT already used (i.e., valid to assign).
        """
        sql = "SELECT COUNT(1) AS cnt FROM `app_users` WHERE `referral_code`=%s;"
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (ref_code,))
                row = await cur.fetchone()
                # If count == 0, it's valid (no existing record has this code)
                return row["cnt"] == 0  # True if not found

    # ---------------------------------------------------------------------------
    # Utility: fetch single order by message_id
    # ---------------------------------------------------------------------------

    async def get_order_by_message_id(self, table: str, message_id: int) -> dict | None:
        """
        SELECT * FROM `table` WHERE message_id = %s LIMIT 1;
        Returns a dict if found, or None.
        """
        sql = f"SELECT * FROM `{table}` WHERE `message_id`=%s LIMIT 1;"
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (message_id,))
                row = await cur.fetchone()
                return dict(row) if row else None


# -------------------------------------------------------------------------------
# Model Classes: Each derives from DataBase and calls its async methods.
# Note: All add/fetch/update/delete methods are now async.
# -------------------------------------------------------------------------------

class Position:
    def __init__(
        self,
        db: DataBase,
        seller_id: int | None = None,
        buyer_id: int | None = None,
        position_amount: int | None = None,
        open_price: int | None = None,
        expiration_date: datetime  = None,
    ):
        self.db = db
        self.seller_id = seller_id
        self.buyer_id = buyer_id
        self.position_amount = position_amount
        self.open_price = open_price
        self.date = datetime.now().replace(microsecond=0).isoformat()
        self.expiration_date = expiration_date

    async def add_record(self) -> dict:
        last_id = await self.db.add_record("positions", self)
        rows = await self.db.fetch_data("positions", {"id": last_id})
        return rows[0] if rows else {}

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("positions", conditions)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("positions", conditions)


class AdvancePosition:
    def __init__(
        self,
        db: DataBase,
        seller_id: int | None = None,
        buyer_id: int | None = None,
        position_amount: int | None = None,
        open_price: int | None = None,
        close_price: int | None = None,
        expiration_date: datetime | None = None,
    ):
        self.db = db
        self.seller_id = seller_id
        self.buyer_id = buyer_id
        self.position_amount = position_amount
        self.open_price = open_price
        self.close_price = close_price
        self.date = datetime.now().replace(microsecond=0).isoformat()
        self.expiration_date = expiration_date.isoformat()


    async def add_record(self) -> dict:
        last_id = await self.db.add_record("advance_positions", self)
        rows = await self.db.fetch_data("advance_positions", {"id": last_id})
        return rows[0] if rows else {}

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("advance_positions", conditions)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("advance_positions", conditions)


class Order:
    def __init__(
        self,
        db: DataBase,
        trader_id: int | None = None,
        message_id: int | None = None,
        trade_type: bool | None = None,
        order_price: int | None = None,
        date: datetime | None = None,
        expiration_date: datetime | None = None,
        needs_extra_day: bool = None,
        order_amount: int | None = None,
        volume_filled: int | None = None,
    ):
        self.db = db
        self.trader_id = trader_id
        self.message_id = message_id
        self.trade_type = trade_type
        self.order_price = order_price
        self.order_amount = order_amount
        self.volume_filled = volume_filled

        # Set date and compute expirations
        self.date = date or datetime.now().replace(microsecond=0)
        self.expiration_order_time = (
            self.date + timedelta(minutes=1)
        ).replace(microsecond=0)

        needs_extra_day = needs_extra_day or (
            self.date.hour > 12 or (self.date.hour == 12 and self.date.minute >= 30)
        )
        exp_base = self.date + timedelta(days=1 if needs_extra_day else 0)
        self.expiration_date = (
            expiration_date
            if expiration_date
            else exp_base.replace(hour=12, minute=30, second=0, microsecond=0)
        )

        # Convert datetimes to ISO strings
        self.date = self.date.isoformat()
        self.expiration_order_time = self.expiration_order_time.isoformat()
        self.expiration_date = self.expiration_date.isoformat()

    async def add_record(self) -> dict | dict[Any, Any]:
        """
        Inserts into the `orders` table. Returns None, since
        existing logic didn’t use the returned ID.
        """
        last_id = await self.db.add_record("orders", self)
        rows = await self.db.fetch_data("orders", {"id": last_id})
        return rows[0] if rows else {}

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("orders", conditions)

    async def update_record(self, conditions: dict) -> None:
        info = {"volume_filled": self.volume_filled}
        await self.db.update_record("orders", conditions, info)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("orders", conditions)


class AdvanceOrder:
    def __init__(
        self,
        db: DataBase,
        seller_id: int | None = None,
        buyer_id: int | None = None,
        message_id: int | None = None,
        open_price: int | None = None,
        close_price: int | None = None,
        expiration_date: datetime | None = None,
        order_amount: int | None = None,
        volume_filled: int | None = None,
        date: datetime | None = None,
    ):
        self.db = db
        self.seller_id = seller_id
        self.buyer_id = buyer_id
        self.message_id = message_id
        self.open_price = open_price
        self.close_price = close_price
        self.order_amount = order_amount
        self.volume_filled = volume_filled

        self.date = date or datetime.now().replace(microsecond=0)
        self.expiration_order_time = (
            self.date + timedelta(minutes=1)
        ).replace(microsecond=0)

        needs_extra_day = (
            self.date.hour > 12 or (self.date.hour == 12 and self.date.minute >= 30)
        )
        exp_base = self.date + timedelta(days=1 if needs_extra_day else 0)
        self.expiration_date = (
            expiration_date
            if expiration_date
            else exp_base.replace(hour=12, minute=30, second=0, microsecond=0)
        )

        # Convert to ISO strings
        self.date = self.date.isoformat()
        self.expiration_order_time = self.expiration_order_time.isoformat()
        self.expiration_date = self.expiration_date.isoformat()

    async def add_record(self) -> dict | dict[Any, Any]:
        last_id = await self.db.add_record("advance_orders", self)
        rows = await self.db.fetch_data("advance_orders", {"id": last_id})
        return rows[0] if rows else {}

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("advance_orders", conditions)

    async def update_record(self, conditions: dict) -> None:
        info = {"volume_filled": self.volume_filled}
        await self.db.update_record("advance_orders", conditions, info)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("advance_orders", conditions)


class OrderHistory:
    def __init__(
        self,
        db: DataBase,
        trader_id: int | None = None,
        trade_type: bool | None = None,
        order_amount: float | None = None,
        entry_price: float | None = None,
        stop_price: float | None = None,
        leverage: int = 1,
        date: datetime | None = None,
    ):
        self.db = db
        self.trader_id = trader_id
        self.date = (date or datetime.now()).replace(microsecond=0).isoformat()
        self.trade_type = trade_type
        self.order_amount = order_amount
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.leverage = leverage

    async def add_record(self) -> dict | dict[Any, Any]:
        last_id = await self.db.add_record("order_history", self)
        rows = await self.db.fetch_data("order_history", {"id": last_id})
        return rows[0] if rows else {}

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("order_history", conditions)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("order_history", conditions)


class User:
    def __init__(
        self,
        db: DataBase,
        trader_id: int | None = None,
        access_level: int | None = None,
        username: str | None = None,
        register_date: datetime | None = None,
        margin: float | None = None,
        referral_code: str | None = None,
        parent_id: int | None = None,
        children: int | None = None,
        frozen_pack: int | None = None,
        trade_pack: int | None = None,
        card_number: str | None = None,
        wallet_address: str | None = None,
    ):
        self.db = db
        self.trader_id = trader_id
        self.username = username
        self.card_number = card_number
        self.wallet_address = wallet_address
        self.register_date = (
            register_date or datetime.now().replace(microsecond=0)
        ).isoformat()
        self.margin = margin
        self.access_level = access_level
        self.referral_code = referral_code
        self.parent_id = parent_id
        self.children = children
        self.trade_pack = trade_pack
        self.frozen_pack = frozen_pack

    async def add_record(self) -> None:
        await self.db.add_record("app_users", self)

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("app_users", conditions)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("app_users", conditions)

    async def update_record(self, conditions: dict) -> None:
        info = {
            "username": self.username,
            "access_level": self.access_level,
            "card_number": self.card_number,
            "wallet_address": self.wallet_address,
            "margin": self.margin,
            "children": self.children,
            "trade_pack": self.trade_pack,
            "frozen_pack": self.frozen_pack,
        }
        await self.db.update_record("app_users", conditions, info)

    async def update_margin(self, trader_id: int, delta: float) -> None:
        """
        Atomically update margin by adding delta. Fetches current margin,
        calculates new value, and updates the row. Uses a transaction to
        avoid race conditions.
        """
        async with self.db._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await conn.begin()
                # Lock the row for update
                await cur.execute(
                    "SELECT `margin` FROM `app_users` WHERE `trader_id`=%s FOR UPDATE;",
                    (trader_id,),
                )
                row = await cur.fetchone()
                if not row:
                    await conn.rollback()
                    raise ValueError(f"User {trader_id} not found.")
                new_margin = float(row["margin"]) + delta
                await cur.execute(
                    "UPDATE `app_users` SET `margin`=%s WHERE `trader_id`=%s;",
                    (new_margin, trader_id),
                )
                await conn.commit()

    async def update_trade_pack(self, trader_id: int, pack_delta: int) -> None:
        """
        Atomically update trade_pack by adding pack_delta. Uses row-level lock.
        """
        async with self.db._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await conn.begin()
                await cur.execute(
                    "SELECT `trade_pack` FROM `app_users` WHERE `trader_id`=%s FOR UPDATE;",
                    (trader_id,),
                )
                row = await cur.fetchone()
                if not row:
                    await conn.rollback()
                    raise ValueError(f"User {trader_id} not found.")
                new_pack = int(row["trade_pack"]) + pack_delta
                await cur.execute(
                    "UPDATE `app_users` SET `trade_pack`=%s WHERE `trader_id`=%s;",
                    (new_pack, trader_id),
                )
                await conn.commit()

    async def get_name(self, trader_id: int) -> str | None:
        rows = await self.db.fetch_data("app_users", {"trader_id": trader_id})
        return rows[0]["username"] if rows else None


class ReplyChain:
    def __init__(
        self,
        db: DataBase,
        trader_id: int | None = None,
        message_id: int | None = None,
        order_table: str | None = None,
        order_message_id: int | None = None,
        order_amount: int | None = None,
    ):
        self.db = db
        self.trader_id = trader_id
        self.message_id = message_id
        self.order_table = order_table
        self.order_message_id = order_message_id
        self.order_amount = order_amount

    async def add_record(self) -> None:
        await self.db.add_record("reply_chain", self)

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("reply_chain", conditions)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("reply_chain", conditions)


class Payment:
    def __init__(
        self,
        db: DataBase,
        trader_id: int | None = None,
        owner_name: str | None = None,
        address: str | None = None,
        file_id: int | None = None,
        deposit_text: str | None = None,
        deposit_amount: float | None = None,
        type: str | None = None,  # 'deposit' or 'withdrawal'
        status: str | None = None,
        transaction_id: str | None = None,
        currency: str | None = None,
        confirmed_by: int | None = None,
        confirmation_date: datetime | None = None,
        date: datetime | None = None,
    ):
        self.db = db
        self.trader_id = trader_id
        self.owner_name = owner_name
        self.address = address
        self.file_id = file_id
        self.deposit_text = deposit_text
        self.deposit_amount = deposit_amount
        self.type = type
        self.status = status
        self.transaction_id = transaction_id
        self.currency = currency
        self.confirmed_by = confirmed_by
        self.confirmation_date = (
            confirmation_date.isoformat() if confirmation_date else None
        )
        self.date = (date or datetime.now().replace(microsecond=0)).isoformat()

    async def add_record(self) -> None:
        await self.db.add_record("payment", self)

    async def fetch_data(self, conditions: dict = None) -> list[dict]:
        return await self.db.fetch_data("payment", conditions)

    async def update_record(self, conditions: dict) -> None:
        info = {
            "owner_name": self.owner_name,
            "address": self.address,
            "file_id": self.file_id,
            "deposit_text": self.deposit_text,
            "deposit_amount": self.deposit_amount,
            "type": self.type,
            "status": self.status,
            "transaction_id": self.transaction_id,
            "currency": self.currency,
            "confirmed_by": self.confirmed_by,
            "confirmation_date": self.confirmation_date,
        }
        await self.db.update_record("payment", conditions, info)

    async def delete_record(self, conditions: dict) -> None:
        await self.db.delete_record("payment", conditions)


# -------------------------------------------------------------------------------
# Example Usage (within an async context)
# -------------------------------------------------------------------------------
#
# async def main():
#     # 1. Create shared async pool
#     db = await DataBase.create_pool(
#         host="188.34.178.143",
#         user="amirhossein",
#         password="g9x76Z!8W]Co1",
#         db="modem",
#         port=3306,
#         minsize=1,
#         maxsize=10
#     )
#
#     # 2. Create a new user
#     new_user = User(
#         db=db,
#         trader_id=123,
#         access_level=1,
#         username="amir",
#         margin=1000.0,
#         referral_code="ABC123"
#     )
#     await new_user.add_record()
#
#     # 3. Fetch user data
#     app_users = await new_user.fetch_data({"trader_id": 123})
#     print(app_users)
#
#     # 4. Update margin safely
#     await new_user.update_margin(trader_id=123, delta=500.0)
#
#     # 5. Close pool when shutting down
#     await db.close_pool()
#
# # Run the example
# asyncio.run(main())
