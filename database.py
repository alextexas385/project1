import sqlite3

DB_NAME = "bot_database.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # --- users ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT
    )
    """)

    # --- sneakers ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sneakers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        image_path TEXT
    )
    """)

    # --- orders ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sneaker_id INTEGER,
        size TEXT,
        color TEXT,
        phone TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(sneaker_id) REFERENCES sneakers(id)
    )
    """)

    # ✅ schema upgrades
    try:
        cur.execute("ALTER TABLE sneakers ADD COLUMN price INTEGER DEFAULT 0")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE orders ADD COLUMN paid INTEGER DEFAULT 0")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE orders ADD COLUMN payment_charge_id TEXT")
    except Exception:
        pass

    # ✅ Статус замовлення: pending / paid / canceled
    try:
        cur.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'pending'")
    except Exception:
        pass
    # ✅ Додаємо photo_file_id до sneakers (для фото з Telegram)
    try:
         cur.execute("ALTER TABLE sneakers ADD COLUMN photo_file_id TEXT")
    except Exception:
        pass
        
    # ✅ seed sneakers if empty
    cur.execute("SELECT COUNT(*) FROM sneakers")
    if cur.fetchone()[0] == 0:
        sneakers = [
            ("Nike Air Zoom", "Легкі бігові кросівки для щоденного використання.", "sneakers/model1.jpg", 249900),
            ("Adidas Ultraboost", "М’яка підошва для максимального комфорту під час ходьби.", "sneakers/model2.jpg", 319900),
            ("Puma RS-X", "Стильна модель для міського стилю.", "sneakers/model3.jpg", 279900),
        ]
        cur.executemany(
            "INSERT INTO sneakers (name, description, image_path, price) VALUES (?, ?, ?, ?)",
            sneakers
        )

    conn.commit()
    conn.close()


def add_user(user):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user.id, user.username)
    )
    conn.commit()
    conn.close()


def get_sneakers():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, image_path, price, photo_file_id FROM sneakers")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_sneaker_by_id(sneaker_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, description, image_path, price, photo_file_id FROM sneakers WHERE id = ?",
        (sneaker_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row




def add_order_pending(user_id, sneaker_id, size, color, phone):
    """Створюємо замовлення зі статусом pending (paid=0)."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (user_id, sneaker_id, size, color, phone, paid, payment_charge_id, status)
        VALUES (?, ?, ?, ?, ?, 0, NULL, 'pending')
    """, (user_id, sneaker_id, size, color, phone))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_order_status(order_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def cancel_order(order_id: int):
    """Скасовуємо замовлення тільки якщо воно pending."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        UPDATE orders
        SET status = 'canceled'
        WHERE id = ? AND status = 'pending'
    """, (order_id,))
    conn.commit()
    conn.close()


def mark_order_paid(order_id: int, payment_charge_id: str):
    """Позначаємо paid тільки якщо було pending (якщо canceled — не чіпаємо)."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        UPDATE orders
        SET paid = 1, payment_charge_id = ?, status = 'paid'
        WHERE id = ? AND status = 'pending'
    """, (payment_charge_id, order_id))
    conn.commit()
    conn.close()

def get_order_for_payment(order_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id, o.user_id, o.sneaker_id, o.size, o.color, o.phone, o.status,
               s.name, s.description, s.price
        FROM orders o
        JOIN sneakers s ON s.id = o.sneaker_id
        WHERE o.id = ?
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_sneaker(name: str, description: str, price: int, photo_file_id: str = None, image_path: str = None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sneakers (name, description, image_path, price, photo_file_id)
        VALUES (?, ?, ?, ?, ?)
    """, (name, description, image_path, price, photo_file_id))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id

def remove_sneaker(sneaker_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM sneakers WHERE id = ?", (sneaker_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok

def list_orders(limit: int = 20):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT o.id, o.user_id, u.username, s.name, o.size, o.color, o.phone,
               o.status, o.paid, o.payment_charge_id
        FROM orders o
        LEFT JOIN users u ON u.user_id = o.user_id
        LEFT JOIN sneakers s ON s.id = o.sneaker_id
        ORDER BY o.id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows
