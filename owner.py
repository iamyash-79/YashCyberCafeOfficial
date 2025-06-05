import sqlite3
from werkzeug.security import generate_password_hash

# User info
full_name = "Yashwant Kumar Sahu"
email = "syashwant682@gmail.com"
plain_password = "Yash@7987"
contact = "7987190554"
role = "owner"

# Hash the password
password_hash = generate_password_hash(plain_password)

# Connect to DB
conn = sqlite3.connect("user.db")
conn.execute("""
    INSERT INTO users (full_name, email, password, role, contact)
    VALUES (?, ?, ?, ?, ?)
""", (full_name, email, password_hash, role, contact))
conn.commit()
conn.close()

print("Owner added successfully.")
