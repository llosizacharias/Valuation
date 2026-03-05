from data_layer.providers.mz_api_provider import MZAPIProvider
from data_layer.download.pdf_downloader import PDFDownloader

provider = MZAPIProvider(
    empresa="COGNA",
    company_id="e1110a12-6e58-4cb0-be24-ed1d5f18049a",
    referer_url="https://ri.cogna.com.br"
)

docs = provider.get_all_available_documents(min_year=2014)

print(f"Total encontrados: {len(docs)}")

downloader = PDFDownloader()
paths = downloader.download_batch(docs)

print("Arquivos baixados:", len(paths))