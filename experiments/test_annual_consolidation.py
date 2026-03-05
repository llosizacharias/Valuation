from financial_engine.annual_consolidator import AnnualConsolidator
import sqlite3

# Pegar company_id manualmente
conn = sqlite3.connect("shipyard.db")
cursor = conn.cursor()

cursor.execute("SELECT id FROM companies WHERE ticker = 'WEGE3'")
company_id = cursor.fetchone()[0]

conn.close()

# Consolidar
consolidator = AnnualConsolidator()

result = consolidator.consolidate_all_years(company_id)

print("Resultado da consolidação:")
print(result)

consolidator.close()