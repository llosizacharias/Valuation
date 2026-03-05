import sqlite3

conn = sqlite3.connect("shipyard.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM financials_quarterly")
conn.commit()

print("Tabela financials_quarterly limpa.")

conn.close()