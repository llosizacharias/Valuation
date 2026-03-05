from data_layer.providers.mz_api_provider import MZAPIProvider
from data_layer.storage.document_repository import DocumentRepository


# 🔹 Inicializa provider
provider = MZAPIProvider(
    empresa="COGNA",
    company_id="e1110a12-6e58-4cb0-be24-ed1d5f18049a",
    referer_url="https://ri.cogna.com.br"
)

# 🔹 Buscar histórico
documents = provider.get_full_history(2024, 2024)

# 🔹 Inicializa repositório
repo = DocumentRepository()

company_id = repo.get_or_create_company(
    ticker="COGN3",
    nome="Cogna Educação S.A.",
    ri_url="https://ri.cogna.com.br",
    provider="MZ",
    company_id_mz="e1110a12-6e58-4cb0-be24-ed1d5f18049a"
)

repo.save_documents(company_id, documents)

print("Pipeline executado com sucesso para COGNA.")

repo.close()