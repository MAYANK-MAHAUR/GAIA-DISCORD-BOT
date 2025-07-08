import aiosqlite
import datetime
import os

DATABASE_FILE = 'bot_data.db'
LAST_CLEAR_FILE = 'last_clear_date.txt'

async def connect_db():
    return await aiosqlite.connect(DATABASE_FILE)

async def initialize_db():
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('''
        CREATE TABLE IF NOT EXISTS multi_embeds (
            message_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            title_en TEXT NOT NULL,
            description_en TEXT NOT NULL,
            title_hi TEXT,
            description_hi TEXT,
            base_color TEXT NOT NULL,
            image_url TEXT,
            thumbnail_url TEXT,
            button1_label TEXT,
            button1_url TEXT,
            button2_label TEXT,
            button2_url TEXT,
            sent_by_user_id INTEGER NOT NULL,
            sent_at TEXT NOT NULL
        )
    ''')
    await conn.commit()
    await conn.close()

async def save_embed_data(
    message_id: int,
    channel_id: int,
    title_en: str,
    description_en: str,
    title_hi: str,
    description_hi: str,
    base_color: str,
    image_url: str,
    thumbnail_url: str,
    button1_label: str,
    button1_url: str,
    button2_label: str,
    button2_url: str,
    sent_by_user_id: int,
    sent_at: str
):
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('''
        INSERT OR REPLACE INTO multi_embeds (
            message_id, channel_id, title_en, description_en,
            title_hi, description_hi, base_color, image_url,
            thumbnail_url, button1_label, button1_url,
            button2_label, button2_url, sent_by_user_id, sent_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        message_id, channel_id, title_en, description_en,
        title_hi, description_hi, base_color, image_url,
        thumbnail_url, button1_label, button1_url,
        button2_label, button2_url, sent_by_user_id, sent_at
    ))
    await conn.commit()
    await conn.close()

async def get_embed_data(message_id: int):
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('SELECT * FROM multi_embeds WHERE message_id = ?', (message_id,))
    data = await cursor.fetchone()
    await conn.close()
    if data:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, data))
    return None

async def get_all_embed_data():
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('SELECT * FROM multi_embeds')
    all_data = await cursor.fetchall()
    await conn.close()
    if all_data:
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in all_data]
    return []

async def delete_embed_data(message_id: int):
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('DELETE FROM multi_embeds WHERE message_id = ?', (message_id,))
    await conn.commit()
    await conn.close()

async def initialize_text_message_db():
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('''
        CREATE TABLE IF NOT EXISTS text_messages (
            message_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            english_content TEXT NOT NULL,
            hindi_content TEXT,
            sender_name TEXT,
            sender_avatar_url TEXT,
            sent_by_user_id INTEGER NOT NULL,
            sent_at TEXT NOT NULL
        )
    ''')
    await conn.commit()
    await conn.close()

async def save_text_message_data(
    message_id: int,
    channel_id: int,
    english_content: str,
    hindi_content: str,
    sender_name: str,
    sender_avatar_url: str,
    sent_by_user_id: int,
    sent_at: str
):
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('''
        INSERT OR REPLACE INTO text_messages (
            message_id, channel_id, english_content, hindi_content,
            sender_name, sender_avatar_url, sent_by_user_id, sent_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        message_id, channel_id, english_content, hindi_content,
        sender_name, sender_avatar_url, sent_by_user_id, sent_at
    ))
    await conn.commit()
    await conn.close()

async def get_text_message_data(message_id: int):
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('SELECT * FROM text_messages WHERE message_id = ?', (message_id,))
    data = await cursor.fetchone()
    await conn.close()
    if data:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, data))
    return None

async def get_all_text_message_data():
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('SELECT * FROM text_messages')
    all_data = await cursor.fetchall()
    await conn.close()
    if all_data:
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in all_data]
    return []

async def delete_text_message_data(message_id: int):
    conn = await connect_db()
    cursor = await conn.cursor()
    await cursor.execute('DELETE FROM text_messages WHERE message_id = ?', (message_id,))
    await conn.commit()
    await conn.close()

async def check_and_clear_db_monthly():
    current_date = datetime.date.today()
    current_month_year = f"{current_date.year}-{current_date.month:02d}"

    last_clear_month_year = None
    if os.path.exists(LAST_CLEAR_FILE):
        with open(LAST_CLEAR_FILE, 'r') as f:
            last_clear_month_year = f.read().strip()

    if last_clear_month_year != current_month_year:
        print(f"New month detected ({current_month_year}). Clearing database.")
        if os.path.exists(DATABASE_FILE):
            os.remove(DATABASE_FILE)
            print(f"Database file '{DATABASE_FILE}' deleted.")
        
        with open(LAST_CLEAR_FILE, 'w') as f:
            f.write(current_month_year)
        print(f"Last clear date updated to {current_month_year}.")
    else:
        print(f"Database not cleared. Still in month: {current_month_year}.")

async def init_database_module():
    await check_and_clear_db_monthly()
    await initialize_db()
    await initialize_text_message_db()

if __name__ == '__main__':
    import asyncio
    async def run_test_init():
        print("Running standalone database initialization test...")
        await init_database_module()
        print("Standalone database initialization test complete.")
    asyncio.run(run_test_init()) 