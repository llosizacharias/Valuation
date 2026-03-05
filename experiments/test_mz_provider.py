from data_layer.providers.mz_api_provider import MZAPIProvider

provider = MZAPIProvider(
    empresa="WEG",
    company_id="50c1bd3e-8ac6-42d9-884f-b9d69f690602",
    referer_url="https://ri.weg.net/"
)

history = provider.get_full_history(2024, 2024)

print("Total documentos:", len(history))

for doc in history[:5]:
    print(doc)