# database.py
import aiomysql
import asyncio
import json


with open('config.json', 'r') as config_file:
    config = json.load(config_file)

host = config['DB_HOST']
user = config['DB_USER']
password = config['DB_PASSWORD']
db = config['DB_NAME']

async def create_connection(host, user, password, db):
    for attempt in range(3):  
        try:
            conn = await aiomysql.connect(host=host, user=user, password=password, db=db, autocommit=True)
            return conn
        except Exception as e:
            print(f"Error creating connection (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2)  
    return None

async def ensure_connection(conn):
    try:
        await conn.ping()
    except Exception:
        print("Connection lost, attempting to reconnect...")
        conn = await create_connection(host, user, password, db)
    return conn

async def create_table(conn):
    if conn is None:
        print("Connection is not established.")
        return

    async with conn.cursor() as cursor:
        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT UNSIGNED PRIMARY KEY,
            vip INTEGER DEFAULT 0,
            admin INTEGER DEFAULT 0,
            username TEXT
        )
        """)

async def alter_table(conn):
    if conn is None:
        print("Connection is not established.")
        return

    async with conn.cursor() as cursor:
        await cursor.execute("""
        ALTER TABLE users 
        MODIFY COLUMN user_id BIGINT UNSIGNED
        """)