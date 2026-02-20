import aiosqlite

DB_NAME = "courier.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
            (user_id INTEGER PRIMARY KEY, full_name TEXT, phone TEXT, region TEXT, status TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS groups 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, chat_id TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS orders 
            (message_id INTEGER, chat_id TEXT, courier_id INTEGER)''')
        await db.commit()

async def add_user(user_id, full_name, phone, region):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, full_name, phone, region, status) VALUES (?, ?, ?, ?, 'pending')",
                         (user_id, full_name, phone, region))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT status, full_name, region FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def update_user_status(user_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

async def get_all_couriers():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, full_name FROM users WHERE status = 'approved'") as cursor:
            return await cursor.fetchall()

async def get_user_details(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT full_name, phone, region FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def delete_courier(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

async def add_group(name, chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO groups (name, chat_id) VALUES (?, ?)", (name, str(chat_id)))
        await db.commit()

async def get_all_groups():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, name, chat_id FROM groups") as cursor:
            return await cursor.fetchall()

async def get_group_details(group_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name, chat_id FROM groups WHERE id = ?", (group_id,)) as cursor:
            return await cursor.fetchone()

async def delete_group(group_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        await db.commit()

async def save_order_msg(message_id, chat_id, courier_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO orders (message_id, chat_id, courier_id) VALUES (?, ?, ?)", 
                         (message_id, str(chat_id), courier_id))
        await db.commit()

async def get_courier_by_msg(chat_id, message_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT courier_id FROM orders WHERE chat_id = ? AND message_id = ?", 
                              (str(chat_id), message_id)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None