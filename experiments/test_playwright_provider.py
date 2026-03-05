from data_layer.providers.mz_playwright_provider import MZPlaywrightProvider

provider = MZPlaywrightProvider(
    empresa="COGNA",
    company_id="e1110a12-6e58-4cb0-be24-ed1d5f18049a",
    ri_url="https://ri.cogna.com.br"
)

docs = provider.get_all_available_documents(min_year=2023)

print(len(docs))