import requests
from pathlib import Path


class PDFDownloader:

    def __init__(self, base_folder="data/raw"):
        self.base_folder = Path(base_folder)
        self.base_folder.mkdir(parents=True, exist_ok=True)

    def _build_path(self, empresa, ano, trimestre, titulo):

        safe_title = (
            str(titulo)
            .replace("/", "_")
            .replace(" ", "_")
            .replace(":", "")
            .replace("\\", "_")
        )[:80]  # ✅ MELHORIA: limita tamanho do nome para evitar paths longos demais

        folder = self.base_folder / empresa / str(ano)
        folder.mkdir(parents=True, exist_ok=True)

        filename = f"{trimestre}T_{safe_title}.pdf"
        return folder / filename

    def download_document(self, doc):

        url = doc.get("url")
        if not url:
            print(f"[WARN] Documento sem URL: {doc.get('titulo', 'sem título')}")
            return None

        path = self._build_path(
            empresa=doc["empresa"],
            ano=doc["ano"],
            trimestre=doc.get("trimestre", 0),
            titulo=doc.get("titulo", "documento")
        )

        if path.exists():
            print(f"[SKIP] Já existe: {path.name}")
            return path

        try:
            # ✅ CORREÇÃO BUG: download sem streaming carrega o PDF inteiro na RAM
            # PDFs grandes (10MB+) podiam travar o processo
            # stream=True + iter_content escreve em partes
            response = requests.get(url, timeout=30, stream=True)

            if response.status_code == 200:
                with open(path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                print(f"[OK] Download: {path.name}")
                return path

            else:
                print(f"[ERROR] Status {response.status_code} ao baixar: {url}")

        except requests.exceptions.Timeout:
            print(f"[ERROR] Timeout ao baixar: {url}")
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] Sem conexão ao baixar: {url}")
        except Exception as e:
            print(f"[ERROR] Falha no download: {e}")

        return None

    def download_batch(self, documents):

        downloaded = []
        failed = []

        for doc in documents:
            path = self.download_document(doc)
            if path:
                downloaded.append(path)
            else:
                failed.append(doc.get("url", "sem url"))

        # ✅ MELHORIA: resumo ao final do batch
        print(f"\n[BATCH] Concluído: {len(downloaded)} baixados, {len(failed)} falhas.")

        if failed:
            print("[BATCH] URLs com falha:")
            for url in failed:
                print(f"  - {url}")

        return downloaded
