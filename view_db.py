import sqlite3

conn = sqlite3.connect("bot_database.db")
c = conn.cursor()

print("=== USERS ===")
for row in c.execute("SELECT * FROM users"):
    print(row)

print("\n=== ORDERS ===")
for row in c.execute("SELECT * FROM orders"):
    print(row)

conn.close()