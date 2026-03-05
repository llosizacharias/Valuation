import pandas as pd
import re

from structure_detection.table_detector import UniversalTableExtractor
from semantic_layer.classifier import classify_label

from financial_model.capex_builder import build_capex_from_fixed_assets
from financial_model.dre_model import build_dre_projection
from financial_model.historical_cleaner import clean_historical_data

from valuation_engine.fcff_engine import build_fcff
from valuation_engine.wacc_model import build_wacc
from valuation_engine.dcf_engine import build_dcf
from valuation_engine.multiples import compute_multiples


# =====================================================
# FUNÇÃO EXTRAÇÃO ANO
# =====================================================

def extract_year(period):
    period = str(period).upper().strip()

    if re.match(r"^20\d{2}$", period):
        return int(period)

    if re.match(r"^[1-4][QT]\d{2}$", period):
        return 2000 + int(period[-2:])

    return None


# =====================================================
# RUNNER DETERMINÍSTICO COMPLETO (SEM PERDER NADA)
# =====================================================

def run_deterministic_valuation(
    file_path: str,
    forecast_years: int = 6,
    last_historical_year: int = 2024,
    tax_rate: float = 0.34,
    terminal_growth: float = 0.0188,
):

    print("Arquivo carregado:", file_path)

    # =====================================================
    # 1) EXTRAÇÃO
    # =====================================================

    extractor = UniversalTableExtractor(file_path)
    df_long = extractor.extract_long_format()

    print("\n=== DATA EXTRAÍDA ===")
    print(df_long.head())
    print("Total registros extraídos:", len(df_long))

    # =====================================================
    # 2) CLASSIFICAÇÃO
    # =====================================================

    df_long["category"] = df_long.apply(
        lambda row: classify_label(row["label_original"], row["sheet"]),
        axis=1
    )

    print("\n=== CLASSIFICAÇÃO IDENTIFICADA ===")
    print(df_long[df_long["category"].notna()].head(20))

    # =====================================================
    # 3) NORMALIZAÇÃO ANO
    # =====================================================

    df_long["year"] = df_long["period"].apply(extract_year)
    df_long = df_long[df_long["year"].notna()]
    df_long["year"] = df_long["year"].astype(int)
    df_long = df_long[df_long["year"] <= last_historical_year]

    has_annual = df_long["period"].str.match(r"^20\d{2}$", na=False).any()

    if has_annual:
        df_long = df_long[df_long["period"].str.match(r"^20\d{2}$", na=False)]
        print("Usando dados anuais consolidados do Excel.")
    else:
        print("Consolidando trimestres em anual.")
        df_long = df_long[df_long["period"].str.match(r"^[1-4][QT]\d{2}$", na=False)]

    # =====================================================
    # 4) CAPEX DERIVADO
    # =====================================================

    capex_series = build_capex_from_fixed_assets(df_long)

    if capex_series is not None and not capex_series.empty:
        capex_df = capex_series.reset_index()
        capex_df.columns = ["year", "value"]
        capex_df["category"] = "CAPEX"

        df_long = pd.concat([
            df_long,
            capex_df.assign(
                sheet="DERIVADO",
                label_original="CAPEX_DERIVADO",
                period=capex_df["year"].astype(str)
            )
        ])

    # =====================================================
    # 5) CONSOLIDAÇÃO ANUAL
    # =====================================================

    df_annual = (
        df_long[df_long["category"].notna()]
        .groupby(["year", "category"])["value"]
        .sum()
        .unstack()
        .sort_index()
    )

    print("\n=== DADOS ANUAIS CONSOLIDADOS ===")
    print(df_annual)

    print("\n=== AUDITORIA HISTÓRICA 2018–2024 ===")
    print(df_annual.loc[2018:2024])

    # =====================================================
    # 6) LIMPEZA HISTÓRICO
    # =====================================================

    historical_df = clean_historical_data(
        df_annual,
        last_historical_year=last_historical_year,
        min_years=3
    )

    print("\n=== HISTÓRICO LIMPO UTILIZADO ===")
    print(historical_df)

    # =====================================================
    # 7) PROJEÇÃO DRE
    # =====================================================

    dre_projection = build_dre_projection(
        historical_df,
        forecast_years=forecast_years
    )

    print("\n=== PROJEÇÃO DRE ===")
    print(dre_projection)

    # =====================================================
    # 8) FCFF
    # =====================================================

    combined_df = pd.concat([historical_df, dre_projection])

    fcff_series = build_fcff(combined_df, tax_rate=tax_rate)
    combined_df["FCFF"] = fcff_series

    print("\n=== FCFF CALCULADO ===")
    print(combined_df["FCFF"])

    # =====================================================
    # 9) WACC
    # =====================================================

    wacc_data = build_wacc()
    wacc = wacc_data["wacc"]

    print("\n=== WACC ===")
    print(wacc_data)

    # =====================================================
    # 10) DCF
    # =====================================================

    projected_fcff = combined_df.loc[
        combined_df.index > last_historical_year,
        "FCFF"
    ]

    dcf_results = build_dcf(
        projected_fcff,
        wacc=wacc,
        terminal_growth=terminal_growth
    )

    enterprise_value = dcf_results["enterprise_value"]

    print("\n=== DCF RESULTS ===")
    print(dcf_results)
    print("\nEnterprise Value:", enterprise_value)

    # =====================================================
    # 11) EQUITY VALUE
    # =====================================================

    net_debt = (
        historical_df["NET_DEBT"].iloc[-1]
        if "NET_DEBT" in historical_df.columns
        else 0
    )

    equity_value = enterprise_value - net_debt

    print("\nEquity Value:", equity_value)

    # =====================================================
    # 12) MÚLTIPLOS
    # =====================================================

    multiples = compute_multiples(
        enterprise_value,
        combined_df
    )

    print("\n=== MÚLTIPLOS ===")
    print(multiples)

    # =====================================================
    # 13) EXPORT
    # =====================================================

    with pd.ExcelWriter("valuation_output.xlsx") as writer:
        historical_df.to_excel(writer, sheet_name="historical")
        dre_projection.to_excel(writer, sheet_name="projection")
        combined_df.to_excel(writer, sheet_name="valuation")

    print("\nArquivo 'valuation_output.xlsx' gerado com sucesso.")

    return {
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "multiples": multiples,
        "historical_df": historical_df,
        "projection": dre_projection,
        "combined_df": combined_df,
    }