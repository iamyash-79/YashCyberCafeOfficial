import sqlite3

def add_item_id_column():
    conn = sqlite3.connect('catalog.db')  # Use your actual DB filename
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN item_id INTEGER;")
        conn.commit()
        print("✅ 'item_id' column added successfully.")
    except sqlite3.OperationalError as e:
        print("⚠️", e)  # This error means column exists already; no problem
    finally:
        conn.close()

add_item_id_column()
