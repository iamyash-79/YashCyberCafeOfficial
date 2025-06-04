import sqlite3

# Connect to your SQLite database
conn = sqlite3.connect("user.db")  # Change path if needed
cursor = conn.cursor()

# Step 1: Create the gender table
cursor.execute("""
CREATE TABLE IF NOT EXISTS gender (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
""")

# Step 2: Check if gender_id exists in users table
cursor.execute("PRAGMA table_info(users);")
columns = [col[1] for col in cursor.fetchall()]

# Step 3: Add gender_id column if it's not already in the users table
if "gender_id" not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN gender_id INTEGER REFERENCES gender(id);")

# Step 4: Insert sample gender values
cursor.execute("INSERT OR IGNORE INTO gender (name) VALUES ('Male');")
cursor.execute("INSERT OR IGNORE INTO gender (name) VALUES ('Female');")
cursor.execute("INSERT OR IGNORE INTO gender (name) VALUES ('Other');")

# Save and close
conn.commit()
conn.close()

print("Gender table created and linked to users table.")
