import os
import requests
from pathlib import Path


class PDFDownloader:

    def __init__(self, base_folder="data/raw"):
        self.base_folder = Path(base_folder)
        self.base_folder.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------
    # 📂 Criar estrutura de pasta
    # ---------------------------------------------------

    def _build_path(self, empresa, ano, trimestre, titulo):

        safe_title = (
            titulo.replace("/", "_")
            .replace(" ", "_")
            .replace(":", "")
        )

        folder = self.base_folder / empresa / str(ano)
        folder.mkdir(parents=True, exist_ok=True)

        filename = f"{trimestre}T_{safe_title}.pdf"

        return folder / filename

    # ---------------------------------------------------
    # ⬇️ Download individual
    # ---------------------------------------------------

    def download_document(self, doc):

        url = doc.get("url")
        if not url:
            return None

        path = self._build_path(
            empresa=doc["empresa"],
            ano=doc["ano"],
            trimestre=doc.get("trimestre", 0),
            titulo=doc.get("titulo", "documento")
        )

        if path.exists():
            print(f"Já existe: {path.name}")
            return path

        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)

                print(f"Download concluído: {path.name}")
                return path
            else:
                print(f"Erro {response.status_code} ao baixar {url}")

        except Exception as e:
            print("Erro download:", e)

        return None

    # ---------------------------------------------------
    # ⬇️ Download em lote
    # ---------------------------------------------------

    def download_batch(self, documents):

        downloaded = []

        for doc in documents:
            path = self.download_document(doc)
            if path:
                downloaded.append(path)

        return downloaded