import sqlite3
import datetime
import os

if os.getenv('RAILWAY') == '1':
    os.makedirs('/data', exist_ok=True)  # <--- Важно!
    db_path = '/data/fridge.db'
else:
    db_path = 'fridge.db'

conn = sqlite3.connect(db_path, check_same_thread=False)

cursor = conn.cursor()


def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            in_fridge INTEGER DEFAULT 0,
            added_date TEXT
        )
    ''')
    conn.commit()


def add_product(name, in_fridge=False):
    name = name.strip().lower()
    added_date = datetime.date.today().isoformat() if in_fridge else None

    try:
        cursor.execute(
            "INSERT INTO products (name, in_fridge, added_date) VALUES (?, ?, ?)",
            (name, int(in_fridge), added_date)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def remove_product(name):
    name = name.strip().lower()  # нормализуем имя
    cursor.execute("DELETE FROM products WHERE name = ?", (name,))
    conn.commit()
    return cursor.rowcount > 0


def list_fridge():
    cursor.execute("SELECT name FROM products WHERE in_fridge = 1")
    return [row[0] for row in cursor.fetchall()]


def list_shopping():
    cursor.execute("SELECT name FROM products WHERE in_fridge = 0")
    return [row[0] for row in cursor.fetchall()]


def mark_as_bought(name):
    name = name.strip().lower()  # нормализуем имя
    cursor.execute(
        "UPDATE products SET in_fridge = 1, added_date = ? WHERE name = ? AND in_fridge = 0",
        (datetime.date.today().isoformat(), name)
    )
    conn.commit()
    return cursor.rowcount > 0
