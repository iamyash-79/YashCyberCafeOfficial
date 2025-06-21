import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

email = "syashwant681@gmail.com"

# Check if email already exists
cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
existing = cursor.fetchone()

if existing:
    print("❌ Owner already exists with this email.")
else:
    hashed_pw = generate_password_hash("Yash@7987")
    cursor.execute("""
        INSERT INTO users (full_name, contact, email, password, role)
        VALUES (?, ?, ?, ?, ?)
    """, ("Yash Owner", "7987190554", email, hashed_pw, "owner"))
    conn.commit()
    print("✅ Owner account created successfully.")

conn.close()
