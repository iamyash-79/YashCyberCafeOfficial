import sqlite3

DB_PATH = "messages.db"  # Ya aapka catalog.db ya jo bhi aap use kar rahe ho

def create_messages_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_email TEXT NOT NULL,
        receiver_email TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()
    print(f"Database and messages table created at {DB_PATH}")

if __name__ == "__main__":
    create_messages_db()
