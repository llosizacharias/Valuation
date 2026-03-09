"""
cvm_csv_parser.py — extrai dados financeiros dos CSVs da CVM dados abertos.

Estrutura dos arquivos CVM:
  dfp_cia_aberta_{ANO}.zip → contém vários CSVs por demonstração:
    dfp_cia_aberta_BPA_con_{ANO}.csv  — Balanço Patrimonial Ativo (consolidado)
    dfp_cia_aberta_BPP_con_{ANO}.csv  — Balanço Patrimonial Passivo (consolidado)
    dfp_cia_aberta_DRE_con_{ANO}.csv  — DRE (consolidado)
    dfp_cia_aberta_DFC_MD_con_{ANO}.csv — DFC método direto
    dfp_cia_aberta_DFC_MI_con_{ANO}.csv — DFC método indireto

Coluna CD_CONTA: código hierárquico da conta contábil (ex: "3.01", "1.01.01")
Coluna VL_CONTA: valor em R$ mil (multiplicar por 1000 para reais)
Coluna DT_FIM_EXERC: data de encerramento do exercício (ex: "2024-12-31")
"""

import os
import zipfile
import io
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# MAPA DE CONTAS CVM → CATEGORIA INTERNA
# ─────────────────────────────────────────────────────────────
#
# Separação IFRS 16:
#   DEBT_SHORT     = dívida financeira CP (empréstimos, debêntures)
#   DEBT_LONG      = dívida financeira LP (empréstimos, debêntures)
#   LEASE_SHORT    = arrendamentos CP (IFRS 16 — passivo de arrendamento CP)
#   LEASE_LONG     = arrendamentos LP (IFRS 16 — passivo de arrendamento LP)
#
# O mercado reporta "dívida líquida financeira" excluindo LEASE.
# O modelo pode calcular ambas as versões.
#
# Contas típicas COGNA/educação (verificar no BPP individual):
#   2.01.04     = Empréstimos e Financiamentos CP (total)
#   2.01.04.01  = Empréstimos e Financiamentos CP (financeiros)
#   2.01.04.02  = Arrendamentos CP (IFRS 16)
#   2.02.01     = Empréstimos e Financiamentos LP (total)
#   2.02.01.01  = Empréstimos e Financiamentos LP (financeiros)
#   2.02.01.02  = Arrendamentos LP (IFRS 16)
#
# Quando as subcategorias .01/.02 existem, usamos elas diretamente.
# Quando não existem (empresa não segrega), usamos o total (2.01.04 / 2.02.01)
# e o ajuste IFRS 16 fica pendente (marcado como estimativa).

ACCOUNT_MAP = {
    # ── DRE ─────────────────────────────────────────────────
    "3.01":     "REVENUE",
    "3.02":     "COGS",
    "3.03":     "GROSS_PROFIT",
    "3.04.01":  "SELLING_EXPENSES",
    "3.04.02":  "GA_EXPENSES",
    "3.05":     "EBIT",
    "3.06.01":  "FIN_INCOME",
    "3.06.02":  "FIN_EXPENSE",
    "3.07":     "EBT",
    "3.08":     "TAXES",
    "3.09":     "NET_INCOME_CONT",
    "3.11":     "NET_INCOME",

    # ── DFC ─────────────────────────────────────────────────
    "6.01":         "OPER_CF",
    "6.02":         "INVEST_CF",
    "6.03":         "FIN_CF",
    "6.01.01.02":   "DEPRECIATION",
    "6.02.02":      "CAPEX_FIXED",
    "6.02.03":      "CAPEX_INTANGIBLE",

    # ── BPA — Ativo ──────────────────────────────────────────
    "1.01.01":  "CASH",               # caixa e equivalentes
    "1.01.02":  "FIN_INVESTMENTS",    # aplicações financeiras CP
    "1.02.01":  "FIN_INVESTMENTS_LT", # investimentos financeiros LP
    "1":        "TOTAL_ASSETS",

    # ── BPP — Passivo (dívida total, sem segregação IFRS 16) ─
    "2.01.04":  "DEBT_SHORT",         # empréstimos CP (total: financeiro + arrendamento)
    "2.02.01":  "DEBT_LONG",          # empréstimos LP (total: financeiro + arrendamento)

    # ── BPP — Passivo (dívida financeira pura, sem IFRS 16) ──
    # Presente quando a empresa segrega subcategorias no CVM
    "2.01.04.01": "DEBT_SHORT_FIN",   # empréstimos e debêntures CP (puro)
    "2.02.01.01": "DEBT_LONG_FIN",    # empréstimos e debêntures LP (puro)

    # ── BPP — Arrendamentos IFRS 16 (separados) ──────────────
    "2.01.04.02": "LEASE_SHORT",      # passivo de arrendamento CP
    "2.02.01.02": "LEASE_LONG",       # passivo de arrendamento LP

    # ── BPP — Patrimônio ─────────────────────────────────────
    "2.03":     "EQUITY",
    "2":        "TOTAL_LIABILITIES",
}

# Contas que precisam ter sinal invertido (valores negativos no CVM)
NEGATE_ACCOUNTS = {
    "COGS", "SELLING_EXPENSES", "GA_EXPENSES",
    "FIN_EXPENSE", "TAXES", "CAPEX_FIXED", "CAPEX_INTANGIBLE",
}

BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS"


def _download_zip(year: int, base_folder: str) -> str | None:
    """Baixa o ZIP da CVM para o ano dado. Retorna path local ou None."""
    import urllib.request

    url       = f"{BASE_URL}/dfp_cia_aberta_{year}.zip"
    dest_dir  = Path(base_folder) / str(year)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"dfp_cia_aberta_{year}.zip"

    if dest_path.exists():
        return str(dest_path)

    try:
        print(f"  Baixando CVM {year}...")
        urllib.request.urlretrieve(url, dest_path)
        return str(dest_path)
    except Exception as e:
        print(f"  [WARN] Falha download {year}: {e}")
        return None


def _read_csv_from_zip(zip_path: str, csv_name: str) -> pd.DataFrame | None:
    """Lê um CSV específico de dentro do ZIP."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            match = next((n for n in names if csv_name.lower() in n.lower()), None)
            if not match:
                return None
            with zf.open(match) as f:
                return pd.read_csv(
                    io.TextIOWrapper(f, encoding="latin-1"),
                    sep=";",
                    dtype=str,
                    low_memory=False,
                )
    except Exception as e:
        print(f"  [WARN] Erro lendo {csv_name} de {zip_path}: {e}")
        return None


def _extract_year_data(zip_path: str, cvm_code: str, year: int) -> pd.DataFrame:
    """
    Extrai todas as categorias mapeadas para um ano/empresa.
    Retorna DataFrame com colunas: year, category, value
    """
    # CSVs a processar por tipo de demonstração
    csv_targets = [
        "DRE_con",
        "BPA_con",
        "BPP_con",
        "DFC_MD_con",
        "DFC_MI_con",
    ]

    records = []

    for csv_name in csv_targets:
        df = _read_csv_from_zip(zip_path, csv_name)
        if df is None:
            continue

        # Filtra empresa pelo código CVM
        code_col = next((c for c in df.columns if "CD_CVM" in c.upper()), None)
        if code_col is None:
            continue

        df = df[df[code_col].astype(str).str.strip() == str(cvm_code)].copy()
        if df.empty:
            continue

        # Seleciona exercício mais recente do ano
        date_col  = next((c for c in df.columns if "DT_FIM" in c.upper()), None)
        conta_col = next((c for c in df.columns if "CD_CONTA" in c.upper()), None)
        valor_col = next((c for c in df.columns if "VL_CONTA" in c.upper()), None)

        if not all([date_col, conta_col, valor_col]):
            continue

        # Filtra pelo ano correto
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df[df[date_col].dt.year == year]
        if df.empty:
            continue

        # Pega apenas a data mais recente (última reapresentação)
        max_date = df[date_col].max()
        df = df[df[date_col] == max_date]

        # Processa contas
        for _, row in df.iterrows():
            conta = str(row[conta_col]).strip()
            if conta not in ACCOUNT_MAP:
                continue

            category = ACCOUNT_MAP[conta]

            try:
                value = float(str(row[valor_col]).replace(",", ".")) * 1000  # R$ mil → R$
            except (ValueError, TypeError):
                continue

            records.append({
                "year":     year,
                "category": category,
                "value":    value,
            })

    if not records:
        return pd.DataFrame(columns=["year", "category", "value"])

    df_out = pd.DataFrame(records)

    # Agrega duplicatas (ex: CAPEX_FIXED + CAPEX_INTANGIBLE → CAPEX via CVM_TO_PIPELINE)
    df_out = df_out.groupby(["year", "category"])["value"].sum().reset_index()

    print(f"  {year}: {len(df_out)} categorias extraídas")
    return df_out


def _read_prefiltered_csvs(folder: Path, year: int) -> pd.DataFrame:
    """
    Lê CSVs já filtrados por empresa (gerados pelo CVMDownloader).
    Formato: data/raw/{EMPRESA}/{year}/dfp_cia_aberta_{TABELA}_con_{year}.csv
    Esses arquivos já contêm apenas as linhas da empresa — não precisa filtrar por CD_CVM.
    """
    import re as _re

    records = []

    csv_files = list(folder.glob("dfp_cia_aberta_*_con_*.csv"))
    if not csv_files:
        return pd.DataFrame()

    for csv_path in csv_files:
        # Extrai nome da tabela: dfp_cia_aberta_DFC_MD_con_2024.csv → DFC_MD
        m = _re.search(r'dfp_cia_aberta_(.+)_con_\d{4}', csv_path.stem)
        if not m:
            continue

        try:
            df = pd.read_csv(csv_path, sep=";", dtype=str,
                             encoding="latin-1", low_memory=False)
        except Exception as e:
            print(f"  [WARN] Erro lendo {csv_path.name}: {e}")
            continue

        # Normaliza nomes de colunas
        df.columns = [c.strip().upper() for c in df.columns]

        conta_col = next((c for c in df.columns if "CD_CONTA"   in c), None)
        valor_col = next((c for c in df.columns if "VL_CONTA"   in c), None)
        date_col  = next((c for c in df.columns if "DT_FIM"     in c), None)
        ordem_col = next((c for c in df.columns if "ORDEM_EXERC" in c), None)

        if not all([conta_col, valor_col]):
            continue

        # Filtra pelo exercício mais recente do ano
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df[df[date_col].dt.year == year]
            if df.empty:
                continue
            max_date = df[date_col].max()
            df = df[df[date_col] == max_date]

        # Prefere ÚLTIMO exercício (não reapresentação)
        if ordem_col and "ÚLTIMO" in df[ordem_col].str.upper().values:
            df = df[df[ordem_col].str.upper() == "ÚLTIMO"]

        for _, row in df.iterrows():
            conta = str(row[conta_col]).strip()
            if conta not in ACCOUNT_MAP:
                continue
            category = ACCOUNT_MAP[conta]
            try:
                value = float(str(row[valor_col]).replace(",", ".")) * 1000
            except (ValueError, TypeError):
                continue
            records.append({"year": year, "category": category, "value": value})

    if not records:
        return pd.DataFrame()

    df_out = pd.DataFrame(records)
    df_out = df_out.groupby(["year", "category"])["value"].sum().reset_index()
    print(f"  {year}: {len(df_out)} categorias extraídas")
    return df_out


def parse_multiple_years(
    base_folder: str,
    empresa: str,
    cvm_code: str,
    years: list[int] = None,
) -> pd.DataFrame:
    """
    Extrai dados de múltiplos anos para uma empresa.

    Modo 1 (preferencial): CSVs pré-filtrados pelo CVMDownloader em
      base_folder/empresa/{year}/dfp_cia_aberta_{TABELA}_con_{year}.csv

    Modo 2 (fallback): ZIPs da CVM em base_folder/{year}/ ou download automático.

    Retorna DataFrame com colunas: year, category, value
    """
    if years is None:
        years = list(range(2019, 2026))

    all_records = []

    for year in years:
        year_df = pd.DataFrame()

        # ── Modo 1: CSVs pré-filtrados (CVMDownloader) ───────
        csv_folder = Path(base_folder) / empresa / str(year)
        if csv_folder.exists() and list(csv_folder.glob("dfp_cia_aberta_*_con_*.csv")):
            year_df = _read_prefiltered_csvs(csv_folder, year)

        # ── Modo 2: ZIP (legado ou download) ─────────────────
        if year_df.empty:
            candidates = [
                Path(base_folder) / empresa / str(year) / f"dfp_cia_aberta_{year}.zip",
                Path(base_folder) / str(year) / f"dfp_cia_aberta_{year}.zip",
                Path(base_folder) / empresa / f"dfp_cia_aberta_{year}.zip",
            ]
            zip_path = next((str(p) for p in candidates if p.exists()), None)

            if zip_path is None:
                zip_path = _download_zip(
                    year,
                    base_folder=str(Path(base_folder) / empresa / str(year)),
                )

            if zip_path:
                year_df = _extract_year_data(zip_path, cvm_code, year)

        if not year_df.empty:
            all_records.append(year_df)
        else:
            print(f"  [WARN] Sem dados para {empresa} {year}")

    if not all_records:
        return pd.DataFrame(columns=["year", "category", "value"])

    return pd.concat(all_records, ignore_index=True)