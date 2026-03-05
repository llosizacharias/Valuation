import sqlite3

conn = sqlite3.connect("shipyard.db")
cursor = conn.cursor()

cursor.execute("""
SELECT ano, trimestre, receita, ebitda, lucro_liquido
FROM financials_quarterly
ORDER BY ano, trimestre
""")

rows = cursor.fetchall()

print("=== DADOS TRIMESTRAIS ===")
for row in rows:
    print(row)

conn.close()