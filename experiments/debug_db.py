import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

print("=== TABELAS ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

print("\n=== FINANCIALS ANNUAL ===")
cursor.execute("SELECT * FROM financials_annual;")
for row in cursor.fetchall():
    print(row)

conn.close()