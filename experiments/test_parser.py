from data_layer.parsing.financial_pdf_parser import FinancialPDFParser

file_path = "data/raw/WEG/2024/4T_Release_de_Resultados_4T24.pdf"

parser = FinancialPDFParser(file_path)

financials = parser.parse_financials()

print("Resultado extraído:")
print(financials)