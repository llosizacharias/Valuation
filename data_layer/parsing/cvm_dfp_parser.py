"""
cvm_csv_parser.py
──────────────────
Parseia CSVs de dados abertos da CVM salvos pelo CVMDownloader.

Formato real dos arquivos:
  CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;
  ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA

Notas:
  - CD_CVM vem com zeros à esquerda (ex: "017973")
  - VL_CONTA em Mil Reais
  - ORDEM_EXERC: "ÚLTIMO" = ano corrente, "PENÚLTIMO" = ano anterior
  - Usar apenas ÚLTIMO para evitar duplicar dados
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Mapeamento de CD_CONTA → categoria interna do pipeline
ACCOUNT_MAP = {
    # DRE
    "3.01":       "REVENUE",
    "3.02":       "COGS",
    "3.03":       "GROSS_PROFIT",
    "3.04":       "OPER_EXPENSES",
    "3.05":       "EBIT",
    "3.06":       "FIN_RESULT",
    "3.06.01":    "FIN_INCOME",
    "3.06.02":    "FIN_EXPENSE",
    "3.07":       "EBT",
    "3.08":       "TAXES",
    "3.09":       "NET_INCOME_CONT",
    "3.11":       "NET_INCOME",
    # DFC_MD / DFC_MI
    "6.01":       "OPER_CF",
    "6.02":       "INVEST_CF",
    "6.03":       "FIN_CF",
    "6.01.01.02": "DEPRECIATION",
    "6.02.02":    "CAPEX_FIXED",
    "6.02.03":    "CAPEX_INTANGIBLE",
    # BPA (Ativo)
    "1":          "TOTAL_ASSETS",
    "1.01":       "CURRENT_ASSETS",
    "1.01.01":    "CASH",
    "1.01.02":    "FIN_INVESTMENTS",
    "1.02":       "NON_CURRENT_ASSETS",
    # BPP (Passivo)
    "2":          "TOTAL_LIABILITIES",
    "2.01":       "CURRENT_LIABILITIES",
    "2.01.04":    "DEBT_SHORT",
    "2.02":       "NON_CURRENT_LIABILITIES",
    "2.02.01":    "DEBT_LONG",
    "2.03":       "EQUITY",
}


def parse_company_csvs(folder: str, cvm_code: str) -> pd.DataFrame:
    """
    Lê todos os CSVs de uma pasta (um ano) e retorna DataFrame:
    year | category | value (em Reais)
    """
    folder_path = Path(folder)
    csv_files   = list(folder_path.glob("dfp_cia_aberta_*_con_*.csv"))

    if not csv_files:
        return pd.DataFrame()

    # CD_CVM pode ter zeros à esquerda — normaliza para comparar
    cvm_target = str(int(cvm_code))   # "017973" → "17973"

    all_rows = []

    for csv_path in csv_files:
        try:
            df = pd.read_csv(
                csv_path,
                sep=";",
                encoding="latin-1",
                dtype=str,
                low_memory=False,
            )
            df.columns = [c.strip().upper() for c in df.columns]

            # Filtra pela empresa (CD_CVM sem zeros à esquerda)
            if "CD_CVM" not in df.columns:
                continue

            df["CD_CVM_NORM"] = df["CD_CVM"].str.strip().str.lstrip("0")
            df = df[df["CD_CVM_NORM"] == cvm_target].copy()

            if df.empty:
                continue

            # Usa apenas ÚLTIMO exercício (evita duplicar com PENÚLTIMO)
            if "ORDEM_EXERC" in df.columns:
                ultimos = df[df["ORDEM_EXERC"].str.contains("LTIMO", na=False) &
                            ~df["ORDEM_EXERC"].str.contains("PEN", na=False)]
                if not ultimos.empty:
                    df = ultimos

            # Extrai ano da DT_REFER
            if "DT_REFER" in df.columns:
                df["year"] = pd.to_datetime(
                    df["DT_REFER"], errors="coerce"
                ).dt.year
            elif "DT_FIM_EXERC" in df.columns:
                df["year"] = pd.to_datetime(
                    df["DT_FIM_EXERC"], errors="coerce"
                ).dt.year
            else:
                continue

            # Converte valor
            if "VL_CONTA" not in df.columns:
                continue

            df["value"] = pd.to_numeric(
                df["VL_CONTA"].str.replace(",", "."),
                errors="coerce"
            ).fillna(0.0)

            # Multiplica por 1000 (CSV em Mil Reais → Reais)
            df["value"] = df["value"] * 1000.0

            for _, row in df.iterrows():
                code = str(row.get("CD_CONTA", "")).strip()
                if not code or pd.isna(row["year"]):
                    continue
                all_rows.append({
                    "year":         int(row["year"]),
                    "account_code": code,
                    "description":  str(row.get("DS_CONTA", "")).strip(),
                    "value":        float(row["value"]),
                })

        except Exception as e:
            print(f"  [WARN] parse {csv_path.name}: {e}")

    if not all_rows:
        return pd.DataFrame()

    df_all = pd.DataFrame(all_rows)

    # Mapeia para categorias do pipeline
    df_all["category"] = df_all["account_code"].map(ACCOUNT_MAP)
    df_all = df_all[df_all["category"].notna()].copy()

    # Agrega por (year, category)
    result = (
        df_all.groupby(["year", "category"])["value"]
        .sum()
        .reset_index()
    )

    return result


def parse_multiple_years(base_folder: str, empresa: str,
                          cvm_code: str, min_year: int = 2019) -> pd.DataFrame:
    """
    Lê CSVs de múltiplos anos e consolida em um único DataFrame.
    """
    current_year = datetime.now().year
    all_dfs      = []

    for year in range(current_year, min_year - 1, -1):
        folder = Path(base_folder) / empresa / str(year)
        if not folder.exists():
            continue

        df = parse_company_csvs(str(folder), cvm_code)
        if not df.empty:
            print(f"  {year}: {len(df)} categorias extraídas")
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    # Deduplica: mantém o valor mais recente para cada (year, category)
    combined = (
        combined
        .sort_values("year")
        .drop_duplicates(subset=["year", "category"], keep="last")
        .reset_index(drop=True)
    )

    return combined