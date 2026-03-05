from playwright.sync_api import sync_playwright
from datetime import datetime


class MZPlaywrightProvider:

    def __init__(self, empresa: str, company_id: str, ri_url: str):
        self.empresa = empresa
        self.company_id = company_id
        self.ri_url = ri_url

    # ---------------------------------------------------
    # 🔎 Buscar documentos por ano
    # ---------------------------------------------------

    def get_documents_by_year(self, year):

        documentos = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Escuta requisição real da API
            with page.expect_response(
                lambda response: "filemanager/search" in response.url
            ) as response_info:

                page.goto(
                    f"{self.ri_url}/central-de-resultados",
                    timeout=60000
                )

                page.wait_for_load_state("networkidle")

                # Força clique no ano via JS (ajustável se necessário)
                page.evaluate(
                    f"""
                    const elements = Array.from(document.querySelectorAll('*'));
                    elements.forEach(el => {{
                        if (el.innerText && el.innerText.trim() === "{year}") {{
                            el.click();
                        }}
                    }});
                    """
                )

            response = response_info.value

            try:
                data = response.json()
            except:
                browser.close()
                return []

            browser.close()

        if (
            isinstance(data, dict)
            and "data" in data
            and "document_metas" in data["data"]
        ):
            for item in data["data"]["document_metas"]:
                documentos.append({
                    "empresa": self.empresa,
                    "ano": year,
                    "titulo": item.get("file_title"),
                    "categoria": item.get("internal_name"),
                    "data_publicacao": item.get("file_published_date"),
                    "url": item.get("file_url"),
                    "trimestre": item.get("file_quarter")
                })

        return documentos

    # ---------------------------------------------------
    # 📚 Histórico completo
    # ---------------------------------------------------

    def get_all_available_documents(self, min_year=2014):

        current_year = datetime.now().year
        historico = []

        for year in range(current_year, min_year - 1, -1):
            print(f"Buscando ano {year}...")
            docs = self.get_documents_by_year(year)

            if docs:
                print(f"{year} -> {len(docs)} documentos")
                historico.extend(docs)

        return historico