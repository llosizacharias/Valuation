import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class RICrawler:

    def __init__(self, base_url, headless=True):
        self.base_url = base_url
        self.headless = headless
        self.driver = self._init_driver()

    # =====================================================
    # INIT DRIVER
    # =====================================================

    def _init_driver(self):

        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        return driver

    # =====================================================
    # NAVEGAR ATÉ RESULTADOS
    # =====================================================

    def go_to_results_page(self):

        self.driver.get(self.base_url)
        time.sleep(5)

        original_window = self.driver.current_window_handle
        links = self.driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            text = link.text.lower()

            if "resultado" in text:
                print("Clicando em:", link.text)

                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", link
                )
                time.sleep(1)

                self.driver.execute_script(
                    "arguments[0].click();", link
                )
                break

        time.sleep(5)

        # Verificar se abriu nova aba
        all_windows = self.driver.window_handles

        if len(all_windows) > 1:
            for window in all_windows:
                if window != original_window:
                    self.driver.switch_to.window(window)
                    print("Nova aba detectada:", self.driver.current_url)
                    break

    # =====================================================
    # EXTRAIR PDFs
    # =====================================================

    def extract_pdf_links(self):

        try:

            self.go_to_results_page()

            current_url = self.driver.current_url
            print("URL atual após clique:", current_url)

            # Caso seja PDF direto
            if ".pdf" in current_url.lower():
                print("PDF direto encontrado.")
                return [current_url]

            # Caso seja página HTML com vários PDFs
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            links = []

            for a in soup.find_all("a", href=True):
                href = a["href"]

                if ".pdf" in href.lower():
                    if href.startswith("http"):
                        links.append(href)
                    else:
                        links.append(
                            self.base_url.rstrip("/") + "/" + href.lstrip("/")
                        )

            print(f"Total PDFs encontrados: {len(links)}")

            return links

        finally:
            self.driver.quit()