from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from datetime import datetime


class MZPlaywrightProvider:

    def __init__(self, empresa: str, company_id: str, ri_url: str):
        self.empresa = empresa
        self.company_id = company_id
        self.ri_url = ri_url

    def get_documents_by_year(self, year):

        documentos = []

        # ✅ CORREÇÃO BUG: except nu capturava todos os erros silenciosamente
        # Playwright tem erros específicos que devem ser tratados separadamente
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                try:
                    with page.expect_response(
                        lambda response: "filemanager/search" in response.url,
                        timeout=30000  # ✅ MELHORIA: timeout explícito (era infinito)
                    ) as response_info:

                        page.goto(
                            f"{self.ri_url}/central-de-resultados",
                            timeout=60000
                        )
                        page.wait_for_load_state("networkidle")

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
                    except Exception:
                        print(f"[WARN] Resposta não-JSON para ano {year}")
                        return []

                    if (
                        isinstance(data, dict)
                        and "data" in data
                        and "document_metas" in data["data"]
                    ):
                        for item in data["data"]["document_metas"]:
                            documentos.append({
                                "empresa":          self.empresa,
                                "ano":              year,
                                "titulo":           item.get("file_title"),
                                "categoria":        item.get("internal_name"),
                                "data_publicacao":  item.get("file_published_date"),
                                "url":              item.get("file_url"),
                                "trimestre":        item.get("file_quarter")
                            })

                except PlaywrightTimeout:
                    print(f"[WARN] Timeout aguardando API para ano {year} em {self.ri_url}")

                finally:
                    browser.close()

        except Exception as e:
            print(f"[ERROR] Playwright falhou para ano {year}: {e}")

        return documentos

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
