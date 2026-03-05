from playwright.sync_api import sync_playwright


def main():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        def log_response(response):
            if "document" in response.url.lower():
                print("\n=== DOCUMENT REQUEST ===")
                print("URL:", response.url)
                print("Status:", response.status)

        page.on("response", log_response)

        page.goto(
            "https://ri.cogna.com.br/central-de-resultados",
            timeout=60000
        )

        print("\nClique manualmente em 2023 e depois em uma categoria.")
        print("Observe o terminal.\n")

        page.wait_for_timeout(30000)

        browser.close()


if __name__ == "__main__":
    main()