from data_layer.parsing.dfp_table_extractor import DFPTableExtractor
from normalization.financial_aggregator import consolidate_to_annual
from data_layer.normalization.account_normalizer import normalize_accounts
from data_layer.storage.financial_repository import FinancialRepository


def import_dfp_pdf(file_path, company_id):

    extractor = DFPTableExtractor(file_path)

    df_long = extractor.extract_tables()

    if df_long.empty:
        raise Exception("Nenhuma tabela válida encontrada no DFP")

    # Consolidar anual
    annual_df = consolidate_to_annual(df_long)

    # Normalizar contas
    annual_df = normalize_accounts(annual_df)

    repo = FinancialRepository()

    for year, row in annual_df.iterrows():

        repo.save_annual(
            company_id=company_id,
            ano=year,
            receita=row.get("REVENUE", 0),
            ebitda=row.get("EBITDA", 0),
            lucro_liquido=row.get("NET_INCOME", 0),
        )

        repo.save_annual_balance(
            company_id=company_id,
            ano=year,
            short_term_debt=row.get("SHORT_TERM_DEBT", 0),
            long_term_debt=row.get("LONG_TERM_DEBT", 0),
            cash=row.get("CASH", 0),
            total_assets=row.get("TOTAL_ASSETS", 0),
            total_equity=row.get("TOTAL_EQUITY", 0),
        )

    repo.close()

    print("DFP importado com sucesso.")