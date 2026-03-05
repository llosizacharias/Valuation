import requests
from datetime import datetime


class MZAPIProvider:

    def __init__(self, empresa: str, company_id: str, referer_url: str):
        self.empresa = empresa
        self.company_id = company_id
        self.referer_url = referer_url

        self.session = requests.Session()
        self.session.headers.update({
            "Referer": referer_url,
            "Origin": referer_url,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        })

        self.endpoint = "https://apicatalog.mziq.com/filemanager/search"

        self.categories = [
            "central_de_resultados_release_resultados",
            "central_de_resultados_itr_dfp",
            "central_de_resultados_apresentacao_resultados"
        ]

    # ---------------------------------------------------
    # 🔎 Buscar documentos por ano (com paginação)
    # ---------------------------------------------------

    def get_documents_by_year(self, year):

        page = 1
        page_size = 100
        documentos = []

        while True:

            payload = {
                "companyId": self.company_id,
                "categories": self.categories,
                "language": "pt_BR",
                "published": True,
                "year": str(year),
                "page": page,
                "pageSize": page_size
            }

            response = self.session.post(self.endpoint, json=payload)

            if response.status_code != 200:
                print(f"Erro {response.status_code} no ano {year}")
                return documentos

            try:
                data = response.json()
            except Exception:
                return documentos

            if (
                not isinstance(data, dict)
                or "data" not in data
                or "document_metas" not in data["data"]
            ):
                return documentos

            items = data["data"]["document_metas"]

            if not items:
                break

            for item in items:
                documentos.append({
                    "empresa": self.empresa,
                    "ano": year,
                    "titulo": item.get("file_title"),
                    "categoria": item.get("internal_name"),
                    "data_publicacao": item.get("file_published_date"),
                    "url": item.get("file_url"),
                    "trimestre": item.get("file_quarter")
                })

            if len(items) < page_size:
                break

            page += 1

        return documentos

    # ---------------------------------------------------
    # 📚 Histórico completo
    # ---------------------------------------------------

    def get_all_available_documents(self, min_year=2010):

        current_year = datetime.now().year
        historico = []

        for year in range(current_year, min_year - 1, -1):

            docs = self.get_documents_by_year(year)

            if docs:
                print(f"{year} -> {len(docs)} documentos")
                historico.extend(docs)

        return historico