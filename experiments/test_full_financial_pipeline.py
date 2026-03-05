from data_layer.providers.mz_api_provider import MZAPIProvider
from data_layer.storage.document_repository import DocumentRepository
from data_layer.storage.financial_repository import FinancialRepository
from data_layer.download.pdf_downloader import PDFDownloader
from data_layer.parsing.financial_pdf_parser import FinancialPDFParser


# =====================================================
# 1️⃣ Provider
# =====================================================

provider = MZAPIProvider(
    empresa="WEG",
    company_id="50c1bd3e-8ac6-42d9-884f-b9d69f690602",
    referer_url="https://ri.weg.net"
)

documents = provider.get_all_available_documents()


# =====================================================
# 2️⃣ Repository - Empresa
# =====================================================

doc_repo = DocumentRepository()

company_id = doc_repo.get_or_create_company(
    ticker="WEGE3",
    nome="WEG S.A.",
    ri_url="https://ri.weg.net",
    provider="MZ",
    company_id_mz="50c1bd3e-8ac6-42d9-884f-b9d69f690602"
)

doc_repo.save_documents(company_id, documents)


# =====================================================
# 3️⃣ Filtrar apenas Releases
# =====================================================

release_docs = [
    doc for doc in documents
    if doc.get("categoria") == "central_de_resultados_release_resultados"
    and doc.get("trimestre") is not None
]

print(f"Total Releases encontrados: {len(release_docs)}")


# =====================================================
# 4️⃣ Downloader
# =====================================================

downloader = PDFDownloader()
paths = downloader.download_batch(release_docs)


# =====================================================
# 5️⃣ Parser + Save Quarterly
# =====================================================

fin_repo = FinancialRepository()

for doc, path in zip(release_docs, paths):

    print(f"Processando Release: {doc['titulo']}")

    if not path:
        continue

    parser = FinancialPDFParser(path)
    data = parser.parse_financials()

    if not data:
        continue

    fin_repo.save_quarterly(
        company_id=company_id,
        ano=doc["ano"],
        trimestre=doc["trimestre"],
        receita=data.get("receita_milhoes"),
        ebitda=data.get("ebitda_milhoes"),
        lucro_liquido=data.get("lucro_liquido_milhoes")
    )

print("Pipeline trimestral executado com sucesso.")

fin_repo.close()
doc_repo.close()