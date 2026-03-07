"""
cvm_downloader.py — versão final
─────────────────────────────────
Baixa dados DFP da CVM via dados abertos (dados.cvm.gov.br).
ZIPs anuais contendo CSVs de todas as empresas, filtrado por CD_CVM.
"""

import io
import time
import zipfile
import requests
from pathlib import Path
from datetime import datetime

TABELAS       = ["DRE", "BPA", "BPP", "DFC_MD", "DFC_MI", "DVA"]
BASE_URL      = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/"
BASE_URL_HIST = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/HIST/"

KNOWN_CVM_CODES = {
    "COGN3": "17973", "COGN3.SA": "17973",
    "WEGE3": "5410",  "WEGE3.SA": "5410",
    "VALE3": "4170",  "VALE3.SA": "4170",
    "ITUB4": "19348", "ITUB4.SA": "19348",
    "PETR4": "9512",  "PETR4.SA": "9512",
    "BBDC4": "906",   "BBDC4.SA": "906",
    "ABEV3": "21610", "ABEV3.SA": "21610",
    "MGLU3": "17264", "MGLU3.SA": "17264",
    "RENT3": "20258", "RENT3.SA": "20258",
    "RADL3": "20001", "RADL3.SA": "20001",
}


def _detect_tabela(filename: str) -> str | None:
    """
    Detecta qual tabela financeira um arquivo ZIP representa.
    Exemplos de nomes reais da CVM:
      dfp_cia_aberta_DRE_con_2024.csv
      dfp_cia_aberta_BPA_con_2024.csv
      dfp_cia_aberta_DFC_MD_con_2024.csv
    """
    upper = filename.upper()
    for t in TABELAS:
        # Compara tudo em maiúsculo
        if f"_{t.upper()}_CON_" in upper:
            return t
    return None


def _filter_lines_for_company(content: str, cvm_code: str) -> tuple[str, list]:
    """
    Filtra linhas de um CSV pelo CD_CVM da empresa.
    Retorna (header, linhas_filtradas).
    """
    lines  = content.splitlines()
    if not lines:
        return "", []

    header = lines[0]
    cols   = [c.strip().upper() for c in header.split(";")]

    # Posição da coluna CD_CVM
    cd_cvm_idx = cols.index("CD_CVM") if "CD_CVM" in cols else None

    # Valor a comparar (sem zeros à esquerda)
    target = cvm_code.lstrip("0")

    filtered = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(";")

        # Método preciso: coluna CD_CVM
        if cd_cvm_idx is not None and cd_cvm_idx < len(parts):
            val = parts[cd_cvm_idx].strip().lstrip("0")
            if val == target:
                filtered.append(line)
                continue

        # Fallback: busca `;017973;` ou `;17973;` na linha
        if f";{target};" in line or f";0{target};" in line:
            filtered.append(line)

    return header, filtered


class CVMDownloader:

    def __init__(self, base_folder: str = "data/raw"):
        self.base_folder = base_folder
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        })

    def _download_zip_bytes(self, year: int) -> bytes | None:
        """Baixa o ZIP e retorna os bytes brutos (nunca abre como ZipFile aqui)."""
        for url in [f"{BASE_URL}dfp_cia_aberta_{year}.zip",
                    f"{BASE_URL_HIST}dfp_cia_aberta_{year}.zip"]:
            try:
                print(f"    GET {url} ...", end=" ", flush=True)
                resp = self.session.get(url, timeout=120, stream=True)
                if resp.status_code == 200:
                    data = b"".join(resp.iter_content(65536))
                    if len(data) > 10_000:
                        print(f"OK ({len(data)//1024} KB)")
                        return data
                    print(f"vazio ({len(data)} B)")
                else:
                    print(f"HTTP {resp.status_code}")
            except Exception as e:
                print(f"erro: {e}")
        return None

    def _extract_all_csvs(self, zip_bytes: bytes) -> dict[str, str]:
        """
        Abre o ZIP, lê TODOS os CSVs relevantes para memória de uma vez,
        fecha o ZIP e retorna {tabela: conteudo_csv}.
        """
        result = {}
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for name in zf.namelist():
                    tabela = _detect_tabela(name)
                    if tabela and tabela not in result:
                        result[tabela] = zf.read(name).decode("latin-1")
        except Exception as e:
            print(f"    [ERRO] Leitura ZIP: {e}")
        return result

    def download_dfps_empresa(self, ticker: str, empresa: str,
                               min_year: int = 2019,
                               cvm_code: str = None) -> list:
        # Resolve código CVM
        if not cvm_code:
            cvm_code = KNOWN_CVM_CODES.get(ticker.upper())
        if not cvm_code:
            cvm_code = self._lookup_cvm_code(ticker)
        if not cvm_code:
            print(f"  [ERRO] Código CVM não encontrado para {ticker}")
            return []

        print(f"  Código CVM: {cvm_code} | Fonte: dados.cvm.gov.br")

        arquivos     = []
        current_year = datetime.now().year

        for year in range(current_year, min_year - 1, -1):
            print(f"\n  → Ano {year}:")

            folder   = Path(self.base_folder) / empresa / str(year)
            existing = list(folder.glob("dfp_cia_aberta_*_con_*.csv")) if folder.exists() else []
            if existing:
                print(f"    {len(existing)} CSVs já existem — pulando")
                arquivos.append(str(folder))
                continue

            # 1. Baixa bytes do ZIP
            zip_bytes = self._download_zip_bytes(year)
            if not zip_bytes:
                print(f"    ZIP não disponível")
                continue

            # 2. Extrai TODOS os CSVs para memória (ZIP fechado após isso)
            csvs = self._extract_all_csvs(zip_bytes)
            if not csvs:
                print(f"    Nenhum CSV encontrado no ZIP")
                continue

            print(f"    Tabelas no ZIP: {list(csvs.keys())}")

            # 3. Filtra por empresa e salva
            folder.mkdir(parents=True, exist_ok=True)
            found_any = False

            for tabela, content in csvs.items():
                header, filtered = _filter_lines_for_company(content, cvm_code)

                if filtered:
                    dest = folder / f"dfp_cia_aberta_{tabela}_con_{year}.csv"
                    with open(dest, "w", encoding="latin-1") as f:
                        f.write(header + "\n")
                        f.write("\n".join(filtered))
                    found_any = True

            if found_any:
                print(f"    ✓ Dados salvos → {folder}")
                arquivos.append(str(folder))
            else:
                print(f"    Empresa {cvm_code} não encontrada no ZIP de {year}")
                # Remove pasta vazia
                try:
                    folder.rmdir()
                except Exception:
                    pass

            time.sleep(0.3)

        return arquivos

    def _lookup_cvm_code(self, ticker: str) -> str:
        try:
            resp = self.session.get(
                "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv",
                timeout=30
            )
            resp.encoding = "latin-1"
            ticker_clean  = ticker.upper().replace(".SA", "").rstrip("0123456789")
            for line in resp.text.splitlines()[1:]:
                cols = line.split(";")
                if len(cols) < 3:
                    continue
                code, nome = cols[0].strip(), cols[2].upper()
                if ticker_clean in nome and code.isdigit():
                    print(f"  CVM code lookup: {code} ({cols[2].strip()})")
                    return code
        except Exception as e:
            print(f"  [WARN] lookup: {e}")
        return None