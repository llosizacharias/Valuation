from playwright.sync_api import sync_playwright


def main():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Abrindo Central de Resultados...")

        # Loga todas as respostas relevantes
        def log_response(response):
            url = response.url

            if (
                "mziq" in url
                or "filemanager" in url
                or "api" in url
            ):
                print("\n--- REQUEST DETECTADO ---")
                print("URL:", url)
                print("Status:", response.status)

        page.on("response", log_response)

        page.goto(
            "https://ri.cogna.com.br/central-de-resultados",
            timeout=60000
        )

        print("\nInteraja manualmente com o filtro de ano...")
        print("Clique no ano 2023, 2022 etc.")
        print("Observe o terminal para ver qual endpoint é chamado.\n")

        page.wait_for_timeout(20000)

        browser.close()


if __name__ == "__main__":
    main()