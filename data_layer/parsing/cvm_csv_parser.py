"""
cvm_csv_parser.py
──────────────────
Parseia os CSVs de dados abertos da CVM (dados.cvm.gov.br).

Formato: dfp_cia_aberta_{TABELA}_con_{YEAR}.csv
Colunas: CD_CVM;CNPJ_CIA;DENOM_CIA;DT_REFER;VERSAO;GRUPO_DFP;
         CD_CONTA;DS_CONTA;ST_CONTA_FIXA;COLUNA_DF;VL_CONTA;DT_FIM_EXERC

Usa os mesmos códigos de conta que o CVMDFPParser (PDF).
"""

import pandas as pd
from pathlib import Path

# Mesmo mapa do cvm_dfp_parser.py
ACCOUNT_MAP = {
    "3.01":       "REVENUE",
    "3.02":       "COGS",
    "3.03":       "GROSS_PROFIT",
    "3.04.01":    "SELLING_EXPENSES",
    "3.04.02":    "GA_EXPENSES",
    "3.05":       "EBIT",
    "3.06.01":    "FIN_INCOME",
    "3.06.02":    "FIN_EXPENSE",
    "3.07":       "EBT",
    "3.08":       "TAXES",
    "3.09":       "NET_INCOME_CONT",
    "3.11":       "NET_INCOME",
    "6.01":       "OPER_CF",
    "6.02":       "INVEST_CF",
    "6.03":       "FIN_CF",
    "6.01.01.02": "DEPRECIATION",
    "6.02.02":    "CAPEX_FIXED",
    "6.02.03":    "CAPEX_INTANGIBLE",
    "1.01.01":    "CASH",
    "1.01.02":    "FIN_INVESTMENTS",
    "1":          "TOTAL_ASSETS",
    "2.01.04":    "DEBT_SHORT",
    "2.02.01":    "DEBT_LONG",
    "2.03":       "EQUITY",
    "2":          "TOTAL_LIABILITIES",
}


class CVMCSVParser:

    def __init__(self, folder: str, cvm_code: str):
        """
        folder:   pasta com os CSVs (ex: data/raw/COGNA/2024)
        cvm_code: código CVM da empresa (ex: "19615")
        """
        self.folder   = Path(folder)
        self.cvm_code = str(int(cvm_code))   # remove zeros à esquerda

    def parse(self) -> pd.DataFrame:
        """
        Lê todos os CSVs da pasta e retorna DataFrame:
        (year, account_code, description, category, value)
        Valores em Reais (os CSVs já vêm em Reais, não em Mil).
        """
        all_rows = []

        csv_files = list(self.folder.glob("dfp_cia_aberta_*.csv"))
        if not csv_files:
            return pd.DataFrame()

        for csv_path in csv_files:
            rows = self._parse_csv(csv_path)
            all_rows.extend(rows)

        if not all_rows:
            return pd.DataFrame()

        df = pd.DataFrame(all_rows)

        # Mapeia código → categoria
        df["category"] = df["account_code"].map(ACCOUNT_MAP)

        # Agrega por (year, category) somando componentes
        df_agg = (
            df[df["category"].notna()]
            .groupby(["year", "account_code", "description", "category"])["value"]
            .sum()
            .reset_index()
        )

        return df_agg

    def _parse_csv(self, csv_path: Path) -> list:
        rows = []
        try:
            df = pd.read_csv(
                csv_path,
                sep=";",
                encoding="latin-1",
                dtype=str,
                low_memory=False,
            )

            # Normaliza nomes de colunas
            df.columns = [c.strip().upper() for c in df.columns]

            # Filtra pela empresa
            if "CD_CVM" in df.columns:
                df = df[df["CD_CVM"].astype(str).str.strip() == self.cvm_code]

            if df.empty:
                return []

            # Seleciona colunas consolidadas (COLUNA_DF = "DF Consolidado")
            if "COLUNA_DF" in df.columns:
                consolidado = df[df["COLUNA_DF"].str.contains("Consolidado", na=False)]
                if not consolidado.empty:
                    df = consolidado

            for _, row in df.iterrows():
                try:
                    code  = str(row.get("CD_CONTA", "")).strip()
                    desc  = str(row.get("DS_CONTA", "")).strip()
                    value = str(row.get("VL_CONTA", "0")).strip().replace(",", ".")
                    # Data de referência → ano
                    dt_refer = str(row.get("DT_REFER", "")).strip()
                    year = int(dt_refer[:4]) if dt_refer and len(dt_refer) >= 4 else None

                    if not code or not year:
                        continue

                    value_f = float(value) if value and value != "nan" else 0.0

                    rows.append({
                        "year":         year,
                        "account_code": code,
                        "description":  desc,
                        "value":        value_f,
                    })
                except Exception:
                    continue

        except Exception as e:
            print(f"  [WARN] parse_csv {csv_path.name}: {e}")

        return rows


def parse_multiple_years(base_folder: str, empresa: str,
                          cvm_code: str, min_year: int = 2019) -> pd.DataFrame:
    """
    Lê CSVs de múltiplos anos e consolida.
    """
    import os
    from datetime import datetime

    all_dfs = []
    current_year = datetime.now().year

    for year in range(current_year, min_year - 1, -1):
        folder = Path(base_folder) / empresa / str(year)
        if not folder.exists():
            continue

        parser = CVMCSVParser(str(folder), cvm_code)
        df = parser.parse()

        if not df.empty:
            print(f"  {year}: {len(df)} registros CSV")
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    # Deduplica: mantém valor mais recente para cada (year, account_code)
    combined = (
        combined
        .sort_values("year")
        .drop_duplicates(subset=["year", "account_code"], keep="last")
        .reset_index(drop=True)
    )

    return combined