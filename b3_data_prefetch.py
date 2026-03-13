"""
b3_data_prefetch.py
─────────────────────────────────────────────────────────────────
Baixa os ZIPs anuais da CVM UMA única vez e pré-extrai os dados
de TODAS as empresas em paralelo — eliminando o problema de
baixar 450× o mesmo arquivo de 150MB.

Estrutura gerada:
  data/cvm_zips/{year}/dfp_cia_aberta_{year}.zip   ← download único
  data/cvm_cache/{cvm_code}/dfp_{year}.csv          ← cache por empresa

Etapas:
  1. download_zips(years)         — baixa ZIPs anuais
  2. extract_all_companies(years) — extrai TODAS as empresas dos ZIPs
  3. verify_cache(cvm_codes)      — verifica quais empresas têm dados

Uso:
  python b3_data_prefetch.py         # baixa e extrai tudo
  python b3_data_prefetch.py --test  # só verifica o cache
"""

import argparse
import io
import json
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

# ── Caminhos ─────────────────────────────────────────────────────
ZIP_DIR   = Path("data/cvm_zips")
CACHE_DIR = Path("data/cvm_cache")
BASE_URL  = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS"
DEFAULT_YEARS = list(range(2019, 2025))   # 2019–2024

# ── Mapa de contas CVM → categoria interna ───────────────────────
# (Cópia do cvm_csv_parser para ser independente)
ACCOUNT_MAP = {
    "3.01": "REVENUE", "3.02": "COGS", "3.03": "GROSS_PROFIT",
    "3.04.01": "SELLING_EXPENSES", "3.04.02": "GA_EXPENSES",
    "3.05": "EBIT", "3.06.01": "FIN_INCOME", "3.06.02": "FIN_EXPENSE",
    "3.07": "EBT", "3.08": "TAXES",
    "3.09": "NET_INCOME_CONT", "3.11": "NET_INCOME",
    "6.01": "OPER_CF", "6.02": "INVEST_CF", "6.03": "FIN_CF",
    "6.01.01.02": "DEPRECIATION",
    "6.02.02": "CAPEX_FIXED", "6.02.03": "CAPEX_INTANGIBLE",
    "1.01.01": "CASH", "1.01.02": "FIN_INVESTMENTS",
    "1.02.01": "FIN_INVESTMENTS_LT", "1": "TOTAL_ASSETS",
    "2.01.04": "DEBT_SHORT", "2.02.01": "DEBT_LONG",
    "2.01.04.01": "DEBT_SHORT_FIN", "2.02.01.01": "DEBT_LONG_FIN",
    "2.01.04.02": "LEASE_SHORT", "2.02.01.02": "LEASE_LONG",
    "2.03": "EQUITY", "2": "TOTAL_LIABILITIES",
}

CSV_TARGETS = ["DRE_con", "BPA_con", "BPP_con", "DFC_MD_con", "DFC_MI_con"]


# ─────────────────────────────────────────────────────────────────
# STEP 1 — Download ZIPs
# ─────────────────────────────────────────────────────────────────
def download_zips(years: list[int] = None) -> dict[int, Path]:
    """
    Baixa os ZIPs anuais da CVM para data/cvm_zips/{year}/.
    Retorna {year: zip_path} para os anos com sucesso.
    """
    years = years or DEFAULT_YEARS
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    result = {}

    for year in years:
        dest = ZIP_DIR / str(year) / f"dfp_cia_aberta_{year}.zip"
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            size_mb = dest.stat().st_size / 1e6
            print(f"[DL] {year}: já existe ({size_mb:.0f}MB) ✓")
            result[year] = dest
            continue

        url = f"{BASE_URL}/dfp_cia_aberta_{year}.zip"
        print(f"[DL] {year}: baixando de {url}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
            with open(dest, "wb") as f:
                f.write(data)
            size_mb = len(data) / 1e6
            print(f"[DL] {year}: ✅ {size_mb:.0f}MB")
            result[year] = dest
        except Exception as e:
            print(f"[DL] {year}: ❌ {e}")

    return result


# ─────────────────────────────────────────────────────────────────
# STEP 2 — Extrai todas as empresas de um ZIP
# ─────────────────────────────────────────────────────────────────
def _read_csv_from_zip(zf: zipfile.ZipFile, csv_target: str) -> pd.DataFrame | None:
    """Lê um CSV específico do ZIP aberto."""
    names = zf.namelist()
    match = next((n for n in names if csv_target.lower() in n.lower()), None)
    if not match:
        return None
    try:
        with zf.open(match) as f:
            return pd.read_csv(
                io.TextIOWrapper(f, encoding="latin-1"),
                sep=";", dtype=str, low_memory=False,
            )
    except Exception as e:
        print(f"[EXT] WARN: erro lendo {csv_target}: {e}")
        return None


def _extract_year_from_zip(zip_path: Path, year: int) -> dict[str, pd.DataFrame]:
    """
    Extrai dados de TODAS as empresas de um ZIP anual.
    Retorna dict {cvm_code: DataFrame(year, category, value)}
    """
    print(f"[EXT] {year}: extraindo empresas do ZIP...")
    company_records: dict[str, list] = {}

    with zipfile.ZipFile(zip_path) as zf:
        for csv_target in CSV_TARGETS:
            df = _read_csv_from_zip(zf, csv_target)
            if df is None:
                continue

            df.columns = [c.strip().upper() for c in df.columns]
            code_col  = next((c for c in df.columns if "CD_CVM" in c), None)
            conta_col = next((c for c in df.columns if "CD_CONTA" in c), None)
            valor_col = next((c for c in df.columns if "VL_CONTA" in c), None)
            date_col  = next((c for c in df.columns if "DT_FIM" in c), None)
            ordem_col = next((c for c in df.columns if "ORDEM_EXERC" in c), None)

            if not all([code_col, conta_col, valor_col]):
                continue

            # Filtra pelo ano e pela data mais recente
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df[df[date_col].dt.year == year]
                if df.empty:
                    continue
                max_date = df[date_col].max()
                df = df[df[date_col] == max_date]

            # Prefere exercício "ÚLTIMO" (não reapresentação)
            if ordem_col:
                df_ult = df[df[ordem_col].str.upper().str.strip() == "ÚLTIMO"]
                if not df_ult.empty:
                    df = df_ult

            # Processa cada linha
            for _, row in df.iterrows():
                cvm_code = str(row[code_col]).strip().lstrip("0")
                conta    = str(row[conta_col]).strip()
                if conta not in ACCOUNT_MAP:
                    continue
                category = ACCOUNT_MAP[conta]
                try:
                    value = float(str(row[valor_col]).replace(",", ".")) * 1000
                except (ValueError, TypeError):
                    continue

                if cvm_code not in company_records:
                    company_records[cvm_code] = []
                company_records[cvm_code].append({
                    "year": year, "category": category, "value": value
                })

    # Converte para DataFrames e agrega
    result = {}
    for cvm_code, records in company_records.items():
        df_co = pd.DataFrame(records)
        df_co = df_co.groupby(["year", "category"])["value"].sum().reset_index()
        result[cvm_code] = df_co

    print(f"[EXT] {year}: {len(result)} empresas extraídas")
    return result


def extract_all_companies(
    zip_paths: dict[int, Path],
    save_cache: bool = True,
) -> dict[str, dict[int, pd.DataFrame]]:
    """
    Extrai dados de todas as empresas de todos os ZIPs.
    Estrutura: {cvm_code: {year: df(year, category, value)}}
    """
    all_data: dict[str, dict[int, pd.DataFrame]] = {}

    for year, zip_path in sorted(zip_paths.items()):
        year_data = _extract_year_from_zip(zip_path, year)

        for cvm_code, df in year_data.items():
            if cvm_code not in all_data:
                all_data[cvm_code] = {}
            all_data[cvm_code][year] = df

        # Salva CSV por empresa (para não perder em crash)
        if save_cache:
            for cvm_code, df in year_data.items():
                out_dir = CACHE_DIR / cvm_code
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"dfp_{year}.csv"
                df.to_csv(out_path, index=False)

    print(f"\n[EXT] Total de empresas com dados: {len(all_data)}")
    if save_cache:
        print(f"[EXT] Cache salvo em {CACHE_DIR}/{{cvm_code}}/dfp_{{year}}.csv")

    return all_data


# ─────────────────────────────────────────────────────────────────
# STEP 3 — Carrega dados do cache (usado pelo b3_runner)
# ─────────────────────────────────────────────────────────────────
def load_company_data(cvm_code: str, years: list[int] = None) -> pd.DataFrame:
    """
    Carrega e concatena dados de uma empresa do cache CSV.
    Retorna DataFrame com colunas: year, category, value
    """
    years = years or DEFAULT_YEARS
    frames = []
    company_dir = CACHE_DIR / str(cvm_code)

    if not company_dir.exists():
        return pd.DataFrame(columns=["year", "category", "value"])

    for year in years:
        p = company_dir / f"dfp_{year}.csv"
        if p.exists():
            frames.append(pd.read_csv(p))

    if not frames:
        return pd.DataFrame(columns=["year", "category", "value"])

    return pd.concat(frames, ignore_index=True)


def has_cache(cvm_code: str, min_years: int = 3) -> bool:
    """Verifica se empresa tem dados suficientes no cache."""
    company_dir = CACHE_DIR / str(cvm_code)
    if not company_dir.exists():
        return False
    parquets = list(company_dir.glob("dfp_*.csv"))
    return len(parquets) >= min_years


def verify_cache(cvm_codes: list[str]) -> dict:
    """
    Verifica quais empresas têm dados no cache.
    Retorna dict {cvm_code: n_anos_disponíveis}
    """
    result = {}
    for code in cvm_codes:
        company_dir = CACHE_DIR / str(code)
        n = len(list(company_dir.glob("dfp_*.csv"))) if company_dir.exists() else 0
        result[code] = n
    return result


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CVM Data Prefetch para pipeline B3")
    parser.add_argument("--years", nargs="+", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--test", action="store_true",
                        help="Apenas verifica cache existente")
    parser.add_argument("--skip-download", action="store_true",
                        help="Pula download, só extrai ZIPs já presentes")
    args = parser.parse_args()

    if args.test:
        print("[TEST] Verificando cache existente...")
        from b3_catalog import load_catalog
        cat = load_catalog()
        cvm_codes = [v["cvm_code"] for v in cat.values()]
        status = verify_cache(cvm_codes)
        with_data = {k: v for k, v in status.items() if v >= 3}
        without   = {k: v for k, v in status.items() if v < 3}
        print(f"\nCom ≥3 anos de dados : {len(with_data)}/{len(cvm_codes)}")
        print(f"Sem dados suficientes: {len(without)}")
    else:
        print(f"[PREFETCH] Anos: {args.years}")
        print("="*55)

        # Step 1: Download
        if not args.skip_download:
            zip_paths = download_zips(args.years)
        else:
            zip_paths = {}
            for year in args.years:
                p = ZIP_DIR / str(year) / f"dfp_cia_aberta_{year}.zip"
                if p.exists():
                    zip_paths[year] = p
                    print(f"[DL] {year}: já existe ✓")
                else:
                    print(f"[DL] {year}: não encontrado, pulando")

        # Step 2: Extração
        if zip_paths:
            print(f"\n[PREFETCH] Extraindo {len(zip_paths)} anos de ZIPs...")
            extract_all_companies(zip_paths, save_cache=True)
            print("\n✅ Prefetch concluído!")
        else:
            print("[PREFETCH] Nenhum ZIP disponível.")