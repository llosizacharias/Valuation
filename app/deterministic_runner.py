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

# ─────────────────────────────────────────────────────────────
# MAPA: categoria CVM → categoria interna do pipeline
# ─────────────────────────────────────────────────────────────

CVM_TO_PIPELINE = {
    "REVENUE":            "REVENUE",
    "COGS":               "COGS",
    "GROSS_PROFIT":       "GROSS_PROFIT",
    "SELLING_EXPENSES":   "SELLING_EXPENSES",
    "GA_EXPENSES":        "GA_EXPENSES",
    "EBIT":               "EBIT",
    "FIN_INCOME":         "FIN_INCOME",
    "FIN_EXPENSE":        "FIN_EXPENSE",
    "EBT":                "EBT",
    "TAXES":              "TAXES",
    "NET_INCOME":         "NET_INCOME",
    "NET_INCOME_CONT":    "NET_INCOME",
    "DEPRECIATION":       "DEPRECIATION",
    "CAPEX_FIXED":        "CAPEX",
    "CAPEX_INTANGIBLE":   "CAPEX",
    "OPER_CF":            "OPER_CF",
    "INVEST_CF":          "INVEST_CF",
    "FIN_CF":             "FIN_CF",
    "CASH":               "CASH",
    "FIN_INVESTMENTS":    "FIN_INVESTMENTS",
    "FIN_INVESTMENTS_LT": "FIN_INVESTMENTS_LT",
    "DEBT_SHORT":         "DEBT_SHORT",
    "DEBT_LONG":          "DEBT_LONG",
    "DEBT_SHORT_FIN":     "DEBT_SHORT_FIN",   # dívida financeira CP (ex-IFRS 16)
    "DEBT_LONG_FIN":      "DEBT_LONG_FIN",    # dívida financeira LP (ex-IFRS 16)
    "LEASE_SHORT":        "LEASE_SHORT",      # arrendamento CP (IFRS 16)
    "LEASE_LONG":         "LEASE_LONG",       # arrendamento LP (IFRS 16)
    "EQUITY":             "EQUITY",
    "TOTAL_ASSETS":       "TOTAL_ASSETS",
    "TOTAL_LIABILITIES":  "TOTAL_LIABILITIES",
}


def extract_year(period):
    period = str(period).upper().strip()
    if re.match(r"^20\d{2}$", period):
        return int(period)
    if re.match(r"^[1-4][QT]\d{2}$", period):
        return 2000 + int(period[-2:])
    return None


def _cash_total(df: pd.DataFrame) -> float:
    """
    Caixa total = CASH (1.01.01) + FIN_INVESTMENTS (1.01.02) + FIN_INVESTMENTS_LT (1.02.01)
    """
    cash   = float(df["CASH"].iloc[-1])               if "CASH"               in df.columns else 0.0
    fin_cp = float(df["FIN_INVESTMENTS"].iloc[-1])    if "FIN_INVESTMENTS"    in df.columns else 0.0
    fin_lp = float(df["FIN_INVESTMENTS_LT"].iloc[-1]) if "FIN_INVESTMENTS_LT" in df.columns else 0.0
    total  = cash + fin_cp + fin_lp

    print(f"[CASH] Caixa restrito     (1.01.01): R$ {cash/1e9:.3f} bi")
    print(f"[CASH] Aplic. financeiras (1.01.02): R$ {fin_cp/1e9:.3f} bi")
    print(f"[CASH] Invest. financ. LP (1.02.01): R$ {fin_lp/1e9:.3f} bi")
    print(f"[CASH] Caixa total                 : R$ {total/1e9:.3f} bi")
    return total


# ─────────────────────────────────────────────────────────────
# EXTRAÇÃO DE PDF
# ─────────────────────────────────────────────────────────────

def extract_from_cvm_dfp(pdf_path: str) -> pd.DataFrame:
    from data_layer.parsing.cvm_dfp_parser import CVMDFPParser

    parser = CVMDFPParser(pdf_path)
    df     = parser.parse()

    if df.empty:
        return pd.DataFrame()

    df["value"]    = df["value"] * 1000
    df["category"] = df["category"].map(CVM_TO_PIPELINE)
    df             = df[df["category"].notna()].copy()
    df.loc[df["category"] == "CAPEX", "value"] = df.loc[df["category"] == "CAPEX", "value"].abs()

    return df.groupby(["year", "category"])["value"].sum().reset_index()


def extract_from_multiple_dfps(dfp_folder: str, empresa: str,
                                cvm_code: str = None) -> pd.DataFrame:
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
            combined["value"]    = combined["value"] * 1000
            combined["category"] = combined["category"].map(CVM_TO_PIPELINE)
            combined             = combined[combined["category"].notna()].copy()
            combined.loc[combined["category"] == "CAPEX", "value"] = \
                combined.loc[combined["category"] == "CAPEX", "value"].abs()

            df = combined.groupby(["year", "category"])["value"].sum().reset_index()
            print(f"\n  Anos disponiveis: {sorted(df['year'].unique())}")
            return df

    # ── Fallback: CSVs da CVM ────────────────────────────────
    found_csvs = glob(f"{dfp_folder}/**/*.csv", recursive=True)

    if found_csvs and cvm_code:
        print(f"  PDFs nao encontrados — usando CSVs da CVM (codigo {cvm_code})")
        from data_layer.parsing.cvm_csv_parser import parse_multiple_years

        combined = parse_multiple_years(
            base_folder=str(Path(dfp_folder).parent),
            empresa=empresa,
            cvm_code=cvm_code,
        )

        if not combined.empty:
            combined["category"] = combined["category"].map(CVM_TO_PIPELINE)
            combined             = combined[combined["category"].notna()].copy()
            combined.loc[combined["category"] == "CAPEX", "value"] = \
                combined.loc[combined["category"] == "CAPEX", "value"].abs()

            df = combined.groupby(["year", "category"])["value"].sum().reset_index()
            print(f"\n  Anos disponiveis: {sorted(df['year'].unique())}")
            return df

    print(f"  [WARN] Nenhum dado encontrado em {dfp_folder}")
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────
# EXTRAÇÃO DE EXCEL
# ─────────────────────────────────────────────────────────────

def extract_from_excel(file_path: str) -> pd.DataFrame:
    extractor = UniversalTableExtractor(file_path)
    df_long   = extractor.extract_long_format()

    if df_long.empty:
        return pd.DataFrame()

    df_long["category"] = df_long.apply(
        lambda row: classify_label(row["label_original"], row["sheet"]), axis=1
    )
    df_long["period"] = df_long["period"].astype(str).str.strip()
    df_long["year"]   = df_long["period"].apply(extract_year)
    df_long           = df_long[df_long["year"].notna()]
    df_long["year"]   = df_long["year"].astype(int)

    has_annual = df_long["period"].str.match(r"^20\d{2}$", na=False).any()
    if has_annual:
        df_long = df_long[df_long["period"].str.match(r"^20\d{2}$", na=False)]
    else:
        df_long = df_long[df_long["period"].str.match(r"^[1-4][QT]\d{2}$", na=False)]

    return (
        df_long[df_long["category"].notna()]
        .groupby(["year", "category"])["value"]
        .sum()
        .reset_index()
    )


# ─────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────

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
    # ── Overrides forward-looking (lidos de companies_config) ─
    revenue_growth_override: float = None,
    ebit_margin_override: float = None,
    # ── Override IFRS 16 ──────────────────────────────────────
    # Quando a empresa usa estrutura de 3 subcontas para dívida
    # (empréstimos / debêntures / arrendamentos), DEBT_SHORT_FIN
    # captura apenas empréstimos. Informe o total de arrendamentos
    # para excluir da dívida bruta total manualmente.
    ifrs16_lease_total: float = None,
):
    # ===================================================
    # 1) EXTRAÇÃO
    # ===================================================

    if dfp_folder and empresa:
        print(f"Modo: multiplos DFPs ({empresa})")
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
            raise ValueError(f"Formato nao suportado: {ext}")
    else:
        raise ValueError("Informe file_path ou dfp_folder+empresa.")

    if df_data.empty:
        raise ValueError("Nenhum dado extraido.")

    df_data = df_data[df_data["year"] <= last_historical_year]

    print(f"\n=== DADOS EXTRAIDOS ===")
    print(f"  Anos: {sorted(df_data['year'].unique())}")
    print(f"  Categorias: {sorted(df_data['category'].unique())}")
    print(f"  Total registros: {len(df_data)}")

    # ===================================================
    # 2) PIVOT → df_annual (year x category)
    # ===================================================

    df_annual = (
        df_data
        .groupby(["year", "category"])["value"]
        .sum()
        .unstack()
        .sort_index()
    )

    if "CAPEX" not in df_annual.columns:
        df_long_compat = df_data.rename(columns={"year": "period"})
        df_long_compat["period"] = df_long_compat["period"].astype(str)
        capex_series = build_capex_from_fixed_assets(df_long_compat)
        if capex_series is not None and not capex_series.empty:
            df_annual["CAPEX"] = capex_series
            print("  CAPEX derivado de ativo imobilizado.")

    print("\n=== DADOS ANUAIS CONSOLIDADOS ===")
    print(df_annual)

    # ===================================================
    # 3) LIMPEZA HISTORICO
    # ===================================================

    historical_df = clean_historical_data(
        df_annual,
        last_historical_year=last_historical_year,
        min_years=3,
    )

    print("\n=== HISTORICO LIMPO ===")
    print(historical_df)

    # ===================================================
    # 4) PROJECAO DRE  (com overrides se configurados)
    # ===================================================

    if revenue_growth_override is not None or ebit_margin_override is not None:
        print("\n[DRE] ⚠️  Overrides forward-looking ativos para esta empresa.")
        print("[DRE]    Para desativar, remova os campos em companies_config.py.\n")

    dre_projection = build_dre_projection(
        historical_df,
        forecast_years=forecast_years,
        tax_rate=tax_rate,
        terminal_growth=terminal_growth,
        revenue_growth_override=revenue_growth_override,
        ebit_margin_override=ebit_margin_override,
    )

    print("\n=== PROJECAO DRE ===")
    print(dre_projection)

    # ===================================================
    # 5) FCFF
    # ===================================================

    combined_df         = pd.concat([historical_df, dre_projection])
    fcff_series         = build_fcff(combined_df, tax_rate=tax_rate)
    combined_df["FCFF"] = fcff_series

    print("\n=== FCFF ===")
    print(combined_df["FCFF"])

    # ===================================================
    # 6) WACC
    # ===================================================

    _debt_s = float(historical_df["DEBT_SHORT"].iloc[-1]) if "DEBT_SHORT" in historical_df.columns else 0.0
    _debt_l = float(historical_df["DEBT_LONG"].iloc[-1])  if "DEBT_LONG"  in historical_df.columns else 0.0
    _cash   = _cash_total(historical_df)

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

    # ===================================================
    # 7) DCF
    # ===================================================

    projected_fcff = combined_df.loc[combined_df.index > last_historical_year, "FCFF"]

    if projected_fcff.empty:
        raise ValueError("Nenhum FCFF projetado encontrado.")

    dcf_results      = build_dcf(projected_fcff, wacc=wacc, terminal_growth=terminal_growth)
    enterprise_value = dcf_results["enterprise_value"]

    print("\n=== DCF ===")
    print(dcf_results)

    # ===================================================
    # 8) EQUITY VALUE — dívida financeira líquida (ex-IFRS 16)
    # ===================================================

    if "NET_DEBT" in historical_df.columns:
        net_debt = float(historical_df["NET_DEBT"].iloc[-1])
    else:
        # Tenta usar dívida financeira pura (subcategorias .01 do CVM)
        has_fin_debt = (
            "DEBT_SHORT_FIN" in historical_df.columns and
            "DEBT_LONG_FIN"  in historical_df.columns
        )
        has_lease = (
            "LEASE_SHORT" in historical_df.columns or
            "LEASE_LONG"  in historical_df.columns
        )

        if ifrs16_lease_total is not None:
            # Override manual: usa dívida total menos arrendamentos informados
            debt_total = (
                historical_df["DEBT_SHORT"].iloc[-1] +
                historical_df["DEBT_LONG"].iloc[-1]
            ) if "DEBT_SHORT" in historical_df.columns else 0.0
            debt = float(debt_total) - ifrs16_lease_total
            print(f"[DEBT] Dívida total           : R$ {float(debt_total)/1e9:.3f} bi")
            print(f"[DEBT] (−) IFRS 16 override   : R$ {ifrs16_lease_total/1e9:.3f} bi")
            print(f"[DEBT] Dívida financeira líq. : R$ {debt/1e9:.3f} bi")
        elif has_fin_debt:
            # Empresa segrega corretamente: usa dívida financeira pura
            debt_fin = (
                historical_df["DEBT_SHORT_FIN"].iloc[-1] +
                historical_df["DEBT_LONG_FIN"].iloc[-1]
            )
            debt_total = (
                historical_df["DEBT_SHORT"].iloc[-1] +
                historical_df["DEBT_LONG"].iloc[-1]
            ) if "DEBT_SHORT" in historical_df.columns else 0.0
            # Sanity check: se FIN < 15% do total, provavelmente estrutura de 3 subcontas
            ratio = float(debt_fin) / float(debt_total) if float(debt_total) > 0 else 1.0
            if ratio < 0.15:
                print(f"[DEBT] ⚠️  DEBT_SHORT/LONG_FIN = {ratio:.1%} da dívida total")
                print(f"[DEBT]    Possível estrutura 3-subcontas (empréstimos/debêntures/arrendamento)")
                print(f"[DEBT]    Usando dívida total. Adicione 'ifrs16_lease_total' em companies_config para excluir arrendamentos.")
                debt = float(debt_total)
            else:
                debt = float(debt_fin)
                print(f"[DEBT] Dívida financeira pura (ex-IFRS 16): R$ {debt/1e9:.3f} bi")
        elif has_lease:
            # Empresa não segrega, mas temos as contas de arrendamento separadas
            lease_s = float(historical_df["LEASE_SHORT"].iloc[-1]) if "LEASE_SHORT" in historical_df.columns else 0.0
            lease_l = float(historical_df["LEASE_LONG"].iloc[-1])  if "LEASE_LONG"  in historical_df.columns else 0.0
            lease   = lease_s + lease_l
            debt_total = (
                historical_df["DEBT_SHORT"].iloc[-1] +
                historical_df["DEBT_LONG"].iloc[-1]
            ) if "DEBT_SHORT" in historical_df.columns else 0.0
            debt = debt_total - lease
            print(f"[DEBT] Dívida total           : R$ {debt_total/1e9:.3f} bi")
            print(f"[DEBT] (−) Arrendamentos IFRS 16: R$ {lease/1e9:.3f} bi")
            print(f"[DEBT] Dívida financeira líq. : R$ {debt/1e9:.3f} bi")
        else:
            # Sem segregação — usa dívida total (inclui IFRS 16)
            debt = (
                historical_df["DEBT_SHORT"].iloc[-1] +
                historical_df["DEBT_LONG"].iloc[-1]
            ) if "DEBT_SHORT" in historical_df.columns else 0.0
            print(f"[DEBT] ⚠️  Dívida total (inclui IFRS 16 estimado): R$ {debt/1e9:.3f} bi")
            print(f"[DEBT]    Para excluir IFRS 16, adicione contas 2.01.04.02/2.02.01.02 ao BPP.")

        net_debt = float(debt) - _cash

    equity_value = enterprise_value - net_debt

    # ===================================================
    # 9) MULTIPLOS
    # ===================================================

    _market_cap = wacc_data.get("market_cap")
    multiples = compute_multiples(
        enterprise_value,
        combined_df,
        market_cap=_market_cap,
        last_historical_year=last_historical_year,
    )

    # ===================================================
    # 10) EXPORT
    # ===================================================

    with pd.ExcelWriter("valuation_output.xlsx") as writer:
        historical_df.to_excel(writer,  sheet_name="historical")
        dre_projection.to_excel(writer, sheet_name="projection")
        combined_df.to_excel(writer,    sheet_name="valuation")

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