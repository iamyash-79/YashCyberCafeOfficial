import sqlite3

def add_temp_password_uses_column():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "temp_password_uses" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN temp_password_uses INTEGER DEFAULT 0")
        conn.commit()
        print("✅ Column 'temp_password_uses' added successfully.")
    else:
        print("ℹ️ Column 'temp_password_uses' already exists. No action needed.")

    conn.close()

# Call the function
add_temp_password_uses_column()
