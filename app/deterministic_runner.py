import pandas as pd
import re
from pathlib import Path
from glob import glob

from structure_detection.table_detector import UniversalTableExtractor
from semantic_layer.classifier import classify_label

from financial_model.capex_builder import build_capex_from_fixed_assets
from financial_model.dre_model import build_dre_projection
from financial_model.historical_cleaner import clean_historical_data

from valuation_engine.fcff_engine import build_fcff
from valuation_engine.wacc_model import build_wacc_structural_brazil
from valuation_engine.dcf_engine import build_dcf
from valuation_engine.multiples import compute_multiples

# ──────────────────────────────────────────────────────────────
# MAPA: categoria CVM → categoria interna do pipeline
# ──────────────────────────────────────────────────────────────

CVM_TO_PIPELINE = {
    "REVENUE":          "REVENUE",
    "COGS":             "COGS",
    "GROSS_PROFIT":     "GROSS_PROFIT",
    "SELLING_EXPENSES": "SELLING_EXPENSES",
    "GA_EXPENSES":      "GA_EXPENSES",
    "EBIT":             "EBIT",
    "FIN_INCOME":       "FIN_INCOME",
    "FIN_EXPENSE":      "FIN_EXPENSE",
    "EBT":              "EBT",
    "TAXES":            "TAXES",
    "NET_INCOME":       "NET_INCOME",
    "NET_INCOME_CONT":  "NET_INCOME",
    "DEPRECIATION":     "DEPRECIATION",
    "CAPEX_FIXED":      "CAPEX",          # ← soma com CAPEX_INTANGIBLE abaixo
    "CAPEX_INTANGIBLE": "CAPEX",
    "OPER_CF":          "OPER_CF",
    "INVEST_CF":        "INVEST_CF",
    "FIN_CF":           "FIN_CF",
    "CASH":             "CASH",
    "FIN_INVESTMENTS":  "FIN_INVESTMENTS",
    "DEBT_SHORT":       "DEBT_SHORT",
    "DEBT_LONG":        "DEBT_LONG",
    "EQUITY":           "EQUITY",
    "TOTAL_ASSETS":     "TOTAL_ASSETS",
    "TOTAL_LIABILITIES":"TOTAL_LIABILITIES",
}


def extract_year(period):
    period = str(period).upper().strip()
    if re.match(r"^20\d{2}$", period):
        return int(period)
    if re.match(r"^[1-4][QT]\d{2}$", period):
        return 2000 + int(period[-2:])
    return None


# ──────────────────────────────────────────────────────────────
# EXTRAÇÃO DE PDF — VIA CVM DFP PARSER (fonte primária)
# ──────────────────────────────────────────────────────────────

def extract_from_cvm_dfp(pdf_path: str) -> pd.DataFrame:
    """
    Usa o CVMDFPParser para extrair dados estruturados do DFP CVM.
    Retorna df_long com colunas: year, category, value (em Reais).
    """
    from data_layer.parsing.cvm_dfp_parser import CVMDFPParser

    parser = CVMDFPParser(pdf_path)
    df = parser.parse()   # valores em Reais Mil

    if df.empty:
        return pd.DataFrame()

    # Converte para Reais
    df["value"] = df["value"] * 1000

    # Mapeia categoria CVM → categoria pipeline
    df["category"] = df["category"].map(CVM_TO_PIPELINE)
    df = df[df["category"].notna()].copy()

    # CAPEX: agrupa CAPEX_FIXED + CAPEX_INTANGIBLE em valor absoluto
    capex_mask = df["category"] == "CAPEX"
    df.loc[capex_mask, "value"] = df.loc[capex_mask, "value"].abs()

    # Agrega por (year, category) — soma componentes como CAPEX
    df = (
        df.groupby(["year", "category"])["value"]
        .sum()
        .reset_index()
    )

    return df


def extract_from_multiple_dfps(dfp_folder: str, empresa: str,
                               cvm_code: str = None) -> pd.DataFrame:
    """
    Busca dados DFP da empresa: primeiro tenta PDFs, depois CSVs da CVM.

    Estrutura PDF: data/raw/{empresa}/{ano}/4T_DFP.pdf
    Estrutura CSV: data/raw/{empresa}/{ano}/dfp_cia_aberta_*.csv
    """
    # ── Tenta PDFs primeiro ──────────────────────────────────
    patterns = [
        f"{dfp_folder}/**/*DFP*.pdf",
        f"{dfp_folder}/**/*dfp*.pdf",
        f"{dfp_folder}/**/*4T_DFP*.pdf",
    ]

    found_pdfs = []
    for pattern in patterns:
        found_pdfs.extend(glob(pattern, recursive=True))
    found_pdfs = sorted(set(found_pdfs))

    if found_pdfs:
        try:
            from data_layer.parsing.cvm_dfp_parser import parse_multiple_dfps
        except ImportError:
            found_pdfs = []

    if found_pdfs:
        print(f"  DFPs (PDF) encontrados: {len(found_pdfs)}")
        for f in found_pdfs:
            print(f"    {f}")

        combined = parse_multiple_dfps(found_pdfs)

        if not combined.empty:
            combined["value"] = combined["value"] * 1000   # Reais Mil → Reais
            combined["category"] = combined["category"].map(CVM_TO_PIPELINE)
            combined = combined[combined["category"].notna()].copy()

            capex_mask = combined["category"] == "CAPEX"
            combined.loc[capex_mask, "value"] = combined.loc[capex_mask, "value"].abs()

            df = (
                combined.groupby(["year", "category"])["value"]
                .sum()
                .reset_index()
            )

            print(f"\n  Anos disponíveis: {sorted(df['year'].unique())}")
            return df

    # ── Fallback: CSVs da CVM (dados abertos) ───────────────
    found_csvs = glob(f"{dfp_folder}/**/*.csv", recursive=True)

    if found_csvs and cvm_code:
        print(f"  PDFs não encontrados — usando CSVs da CVM (código {cvm_code})")
        from data_layer.parsing.cvm_csv_parser import parse_multiple_years

        combined = parse_multiple_years(
            base_folder=str(Path(dfp_folder).parent),
            empresa=empresa,
            cvm_code=cvm_code,
        )

        if not combined.empty:
            # CSVs já vêm em Reais (não em Mil)
            combined["category"] = combined["category"].map(CVM_TO_PIPELINE)
            combined = combined[combined["category"].notna()].copy()

            capex_mask = combined["category"] == "CAPEX"
            combined.loc[capex_mask, "value"] = combined.loc[capex_mask, "value"].abs()

            df = (
                combined.groupby(["year", "category"])["value"]
                .sum()
                .reset_index()
            )

            print(f"\n  Anos disponíveis: {sorted(df['year'].unique())}")
            return df

    print(f"  [WARN] Nenhum dado encontrado em {dfp_folder}")
    return pd.DataFrame()

    # CAPEX: valor absoluto
    capex_mask = combined["category"] == "CAPEX"
    combined.loc[capex_mask, "value"] = combined.loc[capex_mask, "value"].abs()

    # Agrega
    df = (
        combined.groupby(["year", "category"])["value"]
        .sum()
        .reset_index()
    )

    print(f"\n  Anos disponíveis: {sorted(df['year'].unique())}")
    return df


# ──────────────────────────────────────────────────────────────
# EXTRAÇÃO DE EXCEL — fallback para arquivos de modelo financeiro
# ──────────────────────────────────────────────────────────────

def extract_from_excel(file_path: str) -> pd.DataFrame:
    """
    Extrai dados de Excel usando UniversalTableExtractor.
    Retorna df_long no formato (year, category, value).
    """
    extractor = UniversalTableExtractor(file_path)
    df_long = extractor.extract_long_format()

    if df_long.empty:
        return pd.DataFrame()

    # Classifica labels
    df_long["category"] = df_long.apply(
        lambda row: classify_label(row["label_original"], row["sheet"]),
        axis=1
    )

    df_long["period"] = df_long["period"].astype(str).str.strip()
    df_long["year"] = df_long["period"].apply(extract_year)
    df_long = df_long[df_long["year"].notna()]
    df_long["year"] = df_long["year"].astype(int)

    # Consolida trimestres se necessário
    has_annual = df_long["period"].str.match(r"^20\d{2}$", na=False).any()
    if has_annual:
        df_long = df_long[df_long["period"].str.match(r"^20\d{2}$", na=False)]
    else:
        df_long = df_long[df_long["period"].str.match(r"^[1-4][QT]\d{2}$", na=False)]

    df = (
        df_long[df_long["category"].notna()]
        .groupby(["year", "category"])["value"]
        .sum()
        .reset_index()
    )

    return df


# ──────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ──────────────────────────────────────────────────────────────

def run_deterministic_valuation(
    file_path: str = None,
    dfp_folder: str = None,
    empresa: str = None,
    cvm_code: str = None,
    ticker: str = None,
    cost_of_debt: float = 0.12,
    forecast_years: int = 6,
    last_historical_year: int = 2024,
    tax_rate: float = 0.34,
    terminal_growth: float = 0.0188,
):
    # =====================================================
    # 1) EXTRAÇÃO — escolhe a fonte
    # =====================================================

    if dfp_folder and empresa:
        print(f"Modo: múltiplos DFPs ({empresa})")
        df_data = extract_from_multiple_dfps(dfp_folder, empresa, cvm_code=cvm_code)

    elif file_path:
        ext = Path(file_path).suffix.lower()
        print(f"Arquivo: {file_path}")

        if ext == ".pdf":
            print("Modo: DFP PDF (CVM)")
            df_data = extract_from_cvm_dfp(file_path)
        elif ext in (".xlsx", ".xls"):
            print("Modo: Excel")
            df_data = extract_from_excel(file_path)
        else:
            raise ValueError(f"Formato não suportado: {ext}")
    else:
        raise ValueError("Informe file_path ou dfp_folder+empresa.")

    if df_data.empty:
        raise ValueError("Nenhum dado extraído.")

    # Filtra até o último ano histórico
    df_data = df_data[df_data["year"] <= last_historical_year]

    print(f"\n=== DADOS EXTRAÍDOS ===")
    print(f"  Anos: {sorted(df_data['year'].unique())}")
    print(f"  Categorias: {sorted(df_data['category'].unique())}")
    print(f"  Total registros: {len(df_data)}")

    # =====================================================
    # 2) PIVOT → df_annual (year × category)
    # =====================================================

    df_annual = (
        df_data
        .groupby(["year", "category"])["value"]
        .sum()
        .unstack()
        .sort_index()
    )

    # CAPEX derivado de ativos fixos (complementa se CAPEX não veio direto)
    if "CAPEX" not in df_annual.columns:
        df_long_compat = df_data.rename(columns={"year": "period"})
        df_long_compat["period"] = df_long_compat["period"].astype(str)
        capex_series = build_capex_from_fixed_assets(df_long_compat)
        if capex_series is not None and not capex_series.empty:
            df_annual["CAPEX"] = capex_series
            print("  CAPEX derivado de ativo imobilizado.")

    print("\n=== DADOS ANUAIS CONSOLIDADOS ===")
    print(df_annual)

    # =====================================================
    # 3) LIMPEZA HISTÓRICO
    # =====================================================

    historical_df = clean_historical_data(
        df_annual,
        last_historical_year=last_historical_year,
        min_years=3,
    )

    print("\n=== HISTÓRICO LIMPO ===")
    print(historical_df)

    # =====================================================
    # 4) PROJEÇÃO DRE
    # =====================================================

    dre_projection = build_dre_projection(
        historical_df,
        forecast_years=forecast_years,
        tax_rate=tax_rate,
    )

    print("\n=== PROJEÇÃO DRE ===")
    print(dre_projection)

    # =====================================================
    # 5) FCFF
    # =====================================================

    combined_df = pd.concat([historical_df, dre_projection])
    fcff_series = build_fcff(combined_df, tax_rate=tax_rate)
    combined_df["FCFF"] = fcff_series

    print("\n=== FCFF ===")
    print(combined_df["FCFF"])

    # =====================================================
    # 6) WACC
    # =====================================================

    # Passa balanço mais recente para WACC calcular pesos reais de mercado
    _debt_s = float(historical_df["DEBT_SHORT"].iloc[-1]) if "DEBT_SHORT" in historical_df.columns else 0.0
    _debt_l = float(historical_df["DEBT_LONG"].iloc[-1])  if "DEBT_LONG"  in historical_df.columns else 0.0
    _cash   = float(historical_df["CASH"].iloc[-1])       if "CASH"       in historical_df.columns else 0.0

    wacc_data = build_wacc_structural_brazil(
        ticker_symbol=ticker or "^BVSP",
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        debt_short=_debt_s,
        debt_long=_debt_l,
        cash=_cash,
    )

    wacc = wacc_data["wacc"]
    print("\n=== WACC ===")
    print(wacc_data)

    # =====================================================
    # 7) DCF
    # =====================================================

    projected_fcff = combined_df.loc[
        combined_df.index > last_historical_year, "FCFF"
    ]

    if projected_fcff.empty:
        raise ValueError("Nenhum FCFF projetado encontrado.")

    dcf_results = build_dcf(
        projected_fcff,
        wacc=wacc,
        terminal_growth=terminal_growth,
    )

    enterprise_value = dcf_results["enterprise_value"]
    print("\n=== DCF ===")
    print(dcf_results)

    # =====================================================
    # 8) EQUITY VALUE
    # =====================================================

    net_debt = 0
    if "NET_DEBT" in historical_df.columns:
        net_debt = historical_df["NET_DEBT"].iloc[-1]
    elif "DEBT_SHORT" in historical_df.columns and "DEBT_LONG" in historical_df.columns:
        debt = historical_df["DEBT_SHORT"].iloc[-1] + historical_df["DEBT_LONG"].iloc[-1]
        cash = historical_df.get("CASH", pd.Series([0])).iloc[-1]
        net_debt = debt - cash

    equity_value = enterprise_value - net_debt

    # =====================================================
    # 9) MÚLTIPLOS
    # =====================================================

    multiples = compute_multiples(enterprise_value, combined_df)

    # =====================================================
    # 10) EXPORT
    # =====================================================

    with pd.ExcelWriter("valuation_output.xlsx") as writer:
        historical_df.to_excel(writer, sheet_name="historical")
        dre_projection.to_excel(writer, sheet_name="projection")
        combined_df.to_excel(writer, sheet_name="valuation")

    print("\nArquivo 'valuation_output.xlsx' gerado.")

    return {
        "enterprise_value": enterprise_value,
        "equity_value":     equity_value,
        "net_debt":         net_debt,
        "multiples":        multiples,
        "wacc_data":        wacc_data,
        "dcf_results":      dcf_results,
        "historical_df":    historical_df,
        "projection":       dre_projection,
        "combined_df":      combined_df,
    }