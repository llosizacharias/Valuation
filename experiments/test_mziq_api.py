import requests

COMPANY_ID = "50c1bd3e-8ac6-42d9-884f-b9d69f690602"

url = f"https://apicatalog.mziq.com/filemanager/company/{COMPANY_ID}/filter/categories/year/meta"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://ri.weg.net",
    "Referer": "https://ri.weg.net/",
    "Content-Type": "application/json"
}

all_documents = []

for year in range(2000, 2025):

    payload = {
        "categories": [
            "central_de_resultados_release_resultados",
            "central_de_resultados_itr_dfp",
            "central_de_resultados_apresentacao_resultados"
        ],
        "year": str(year),
        "language": "pt_BR",
        "published": True
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        if data:
            print(f"{year} -> {len(data)} documentos")
            all_documents.extend(data)

print("Total histórico:", len(all_documents))