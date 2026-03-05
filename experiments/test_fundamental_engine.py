from data_layer.storage.financial_repository import FinancialRepository
from analysis.fundamental_engine import FundamentalEngine


repo = FinancialRepository()

annual_data = repo.get_annual_data(company_id=1)  # ajuste se necessário

print("=== DADOS ANUAIS ===")
for row in annual_data:
    print(row)

engine = FundamentalEngine(annual_data)

result = engine.run_full_analysis()

print(result)

repo.close()