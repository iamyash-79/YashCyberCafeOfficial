import sqlite3

conn = sqlite3.connect("bill.db")
cur = conn.cursor()

# Step 1: Rename old tables
cur.execute("ALTER TABLE bills RENAME TO bills_old")
cur.execute("ALTER TABLE bill_items RENAME TO bill_items_old")

# Step 2: Create corrected bills table
cur.execute("""
CREATE TABLE bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    contact TEXT,
    address1 TEXT,
    address2 TEXT,
    city TEXT,
    pincode TEXT,
    total REAL,
    created_at TEXT
)
""")

# Step 3: Create corrected bill_items table
cur.execute("""
CREATE TABLE bill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER,
    item_type TEXT,
    item_name TEXT,
    quantity INTEGER,
    price REAL,
    FOREIGN KEY(bill_id) REFERENCES bills(id)
)
""")

# Step 4: Copy valid data (excluding product/service columns)
cur.execute("""
INSERT INTO bills (id, name, contact, address1, address2, city, pincode, total, created_at)
SELECT id, name, contact, address1, address2, city, pincode, total, created_at FROM bills_old
""")

# Step 5: Copy old bill_items if possible (skip price if missing)
cur.execute("PRAGMA table_info('bill_items_old')")
columns = [row[1] for row in cur.fetchall()]
if 'price' in columns:
    cur.execute("""
    INSERT INTO bill_items (id, bill_id, item_type, item_name, quantity, price)
    SELECT id, bill_id, item_type, item_name, quantity, price FROM bill_items_old
    """)
else:
    cur.execute("""
    INSERT INTO bill_items (id, bill_id, item_type, item_name, quantity, price)
    SELECT id, bill_id, item_type, item_name, quantity, 0 FROM bill_items_old
    """)

# Step 6: Drop old tables
cur.execute("DROP TABLE bills_old")
cur.execute("DROP TABLE bill_items_old")

conn.commit()
conn.close()
print("✅ Schema fixed. You can now use the corrected /bill route.")
