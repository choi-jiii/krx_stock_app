import sqlite3

DB_PATH = "favorites.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT NOT NULL,
        market TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, stock_code)
    )
    """)

    conn.commit()
    conn.close()


def add_favorite(user_id, stock_code, stock_name, market):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT INTO favorites (user_id, stock_code, stock_name, market)
        VALUES (?, ?, ?, ?)
        """, (user_id, stock_code, stock_name, market))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_favorites(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    SELECT stock_code, stock_name, market
    FROM favorites
    WHERE user_id = ?
    ORDER BY created_at ASC
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    return rows


def delete_favorite(user_id, stock_code):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    DELETE FROM favorites
    WHERE user_id = ? AND stock_code = ?
    """, (user_id, stock_code))

    conn.commit()
    conn.close()