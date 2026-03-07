from data_layer.parsing.dfp_table_extractor import DFPTableExtractor
from data_layer.normalization.account_normalizer import normalize_accounts
from data_layer.storage.financial_repository import FinancialRepository

# ✅ CORREÇÃO BUG CRÍTICO: import errado
# Era: from normalization.financial_aggregator import consolidate_to_annual
# Esse módulo não existe no projeto — causava ImportError imediato
# A consolidação anual é feita agrupando por period diretamente aqui


def _consolidate_to_annual(df_long):
    """
    Agrupa df no formato long (period, category, value)
    em um DataFrame anual (index=ano, columns=categories).
    """
    if df_long.empty:
        return df_long

    df = df_long.copy()
    df["period"] = df["period"].astype(str)

    # Mantém apenas anos completos (ex: 2022, não 1T22)
    df = df[df["period"].str.match(r"^20\d{2}$", na=False)]
    df["period"] = df["period"].astype(int)

    annual = (
        df.groupby(["period", "category"])["value"]
        .sum()
        .unstack()
        .sort_index()
    )

    annual.index.name = "ano"
    return annual


def import_dfp_pdf(file_path, company_id):

    extractor = DFPTableExtractor(file_path)
    df_long = extractor.extract_tables()

    if df_long.empty:
        # ✅ CORREÇÃO: raise ValueError em vez de Exception genérico
        raise ValueError(
            f"Nenhuma tabela válida encontrada no DFP: {file_path}"
        )

    annual_df = _consolidate_to_annual(df_long)

    if annual_df.empty:
        raise ValueError(
            "Nenhum dado anual consolidado após extração. "
            "Verifique se o PDF contém períodos no formato YYYY."
        )

    annual_df = normalize_accounts(annual_df)

    repo = FinancialRepository()

    try:
        for year, row in annual_df.iterrows():

            repo.save_annual(
                company_id=company_id,
                ano=year,
                receita=row.get("REVENUE") or 0,
                ebitda=row.get("EBITDA") or 0,
                lucro_liquido=row.get("NET_INCOME") or 0,
            )

            repo.save_annual_balance(
                company_id=company_id,
                ano=year,
                short_term_debt=row.get("SHORT_TERM_DEBT") or 0,
                long_term_debt=row.get("LONG_TERM_DEBT") or 0,
                cash=row.get("CASH") or 0,
                total_assets=row.get("TOTAL_ASSETS") or 0,
                total_equity=row.get("TOTAL_EQUITY") or 0,
            )

        print(f"[OK] DFP importado: {len(annual_df)} anos para company_id={company_id}")

    finally:
        # ✅ CORREÇÃO: repo sempre fechado mesmo se der erro no loop
        repo.close()
