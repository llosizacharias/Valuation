"""
main.py
────────
Pipeline de valuation multi-empresa.

Uso:
  python main.py              → roda todas as empresas em COMPANIES
  python main.py WEG          → roda só WEG
  python main.py WEG COGNA    → roda WEG e COGNA

Os resultados são salvos em:
  valuation_output_{EMPRESA}.xlsx
  valuation_results.json        ← todos os resultados consolidados (para o dashboard)
"""

import sys
import os
import json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from companies_config import get_company, list_companies
from data_layer.providers.mz_api_provider import MZAPIProvider
from data_layer.download.pdf_downloader import PDFDownloader
from data_layer.storage.document_repository import DocumentRepository
from app.deterministic_runner import run_deterministic_valuation

import yfinance as yf

IPCA_LONG_TERM = 0.04


# ─────────────────────────────────────────────────────────────
# KPI HELPERS
# ─────────────────────────────────────────────────────────────

def calc_roic(historical_df, tax_rate):
    try:
        ebit   = historical_df["EBIT"].iloc[-1]
        nopat  = ebit * (1 - tax_rate)
        equity = historical_df.get("EQUITY",     pd.Series([0])).iloc[-1]
        debt   = (historical_df.get("DEBT_SHORT", pd.Series([0])).iloc[-1] +
                  historical_df.get("DEBT_LONG",  pd.Series([0])).iloc[-1])
        cash   = historical_df.get("CASH",        pd.Series([0])).iloc[-1]
        ic     = equity + debt - cash
        return nopat / ic if ic > 0 else None
    except Exception:
        return None


def calc_roe(historical_df):
    try:
        ni  = historical_df.get("NET_INCOME", pd.Series([0])).iloc[-1]
        eq  = historical_df.get("EQUITY",     pd.Series([0])).iloc[-1]
        return ni / eq if eq > 0 else None
    except Exception:
        return None


def calc_ev_ebitda(ev, historical_df):
    try:
        ebit = historical_df["EBIT"].iloc[-1]
        dep  = historical_df.get("DEPRECIATION", pd.Series([0])).iloc[-1]
        return ev / (ebit + dep) if (ebit + dep) > 0 else None
    except Exception:
        return None


def calc_ev_ebit(ev, historical_df):
    try:
        ebit = historical_df["EBIT"].iloc[-1]
        return ev / ebit if ebit > 0 else None
    except Exception:
        return None


def calc_pe(eq_value, historical_df):
    try:
        ni = historical_df.get("NET_INCOME", pd.Series([0])).iloc[-1]
        return eq_value / ni if ni > 0 else None
    except Exception:
        return None


def calc_cagr(series):
    try:
        s = series.dropna()
        if len(s) < 2:
            return None
        years = s.index[-1] - s.index[0]
        return (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1
    except Exception:
        return None


def _calc_irr(cash_flows):
    """TIR via Newton-Raphson puro (sem scipy)."""
    if not cash_flows or len(cash_flows) < 2:
        return None
    cf   = [float(c) for c in cash_flows]
    rate = 0.10
    for _ in range(1000):
        npv  = sum(c / (1 + rate) ** t for t, c in enumerate(cf))
        dnpv = sum(-t * c / (1 + rate) ** (t + 1) for t, c in enumerate(cf))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-8:
            rate = new_rate
            break
        rate = new_rate
    npv_check = sum(c / (1 + rate) ** t for t, c in enumerate(cf))
    if abs(npv_check) > abs(cf[0]) * 0.01 or rate < -0.99 or rate > 100:
        return None
    return rate


def recommendation(upside_pct):
    if upside_pct >= 0.20:  return "🟢 COMPRA FORTE"
    if upside_pct >= 0.05:  return "🟡 COMPRA"
    if upside_pct >= -0.05: return "⚪ NEUTRO"
    if upside_pct >= -0.20: return "🟠 VENDA"
    return "🔴 VENDA FORTE"


# ─────────────────────────────────────────────────────────────
# PIPELINE POR EMPRESA
# ─────────────────────────────────────────────────────────────

def run_company(empresa_key: str) -> dict:
    cfg = get_company(empresa_key)

    CVM_CODE      = cfg.get("cvm_code")
    TICKER        = cfg["ticker"]
    NOME          = cfg["nome"]
    COMPANY_ID_MZ = cfg["company_id_mz"]
    RI_URL        = cfg["ri_url"]
    SHARES_OUT    = cfg["shares_out"]
    COST_OF_DEBT  = cfg["cost_of_debt"]
    TERM_GROWTH   = cfg["terminal_growth"]
    FORECAST_YRS  = cfg["forecast_years"]
    TAX_RATE      = cfg["tax_rate"]
    MIN_YEAR      = cfg["min_year"]
    DFP_FOLDER    = f"data/raw/{empresa_key}"

    sep  = "=" * 60
    sep2 = "─" * 60

    print(f"\n{sep}")
    print(f"  🏢 {NOME} ({TICKER})")
    print(sep)

    # ── 1) Documentos MZ ────────────────────────────────────
    print("\n[1/4] Buscando documentos MZ...")
    provider   = MZAPIProvider(empresa=empresa_key, company_id=COMPANY_ID_MZ, referer_url=RI_URL)
    documentos = provider.get_all_available_documents(min_year=MIN_YEAR)

    # ── 2) Banco ─────────────────────────────────────────────
    repo = DocumentRepository()
    company_db_id = repo.get_or_create_company(
        ticker=TICKER, nome=NOME, ri_url=RI_URL,
        provider="mz_api", company_id_mz=COMPANY_ID_MZ,
    )
    if documentos:
        print(f"  {len(documentos)} documentos encontrados.")
        repo.save_documents(company_db_id, documentos)
    repo.close()

    # ── 3) Download ──────────────────────────────────────────
    arquivos = []

    if documentos:
        print("[3/4] Baixando arquivos via MZ...")
        downloader = PDFDownloader(base_folder="data/raw")
        arquivos   = downloader.download_batch(documentos)

    # Fallback: CVM Dados Abertos (público, sem autenticação)
    if not arquivos:
        print("[3/4] MZ indisponível — baixando DFPs direto da CVM...")
        from data_layer.download.cvm_downloader import CVMDownloader
        cvm_dl   = CVMDownloader(base_folder="data/raw")
        arquivos = cvm_dl.download_dfps_empresa(
            ticker=TICKER,
            empresa=empresa_key,
            min_year=MIN_YEAR,
            cvm_code=CVM_CODE,
        )

    if not arquivos:
        # Último recurso: verifica se já existem DFPs baixados anteriormente
        from glob import glob
        existing = glob(f"{DFP_FOLDER}/**/*.pdf", recursive=True)
        if existing:
            print(f"  Usando {len(existing)} DFPs já existentes em {DFP_FOLDER}")
            arquivos = existing
        else:
            raise RuntimeError(
                f"Nenhum arquivo disponível para {empresa_key}.\n"
                f"Opções manuais:\n"
                f"  1. Baixe os DFPs em {DFP_FOLDER}/{{ano}}/4T_DFP.pdf\n"
                f"  2. Acesse: https://www.rad.cvm.gov.br"
            )

    # ── 4) Valuation ─────────────────────────────────────────
    print("[4/4] Calculando valuation...")
    resultado = run_deterministic_valuation(
        dfp_folder=DFP_FOLDER,
        empresa=empresa_key,
        cvm_code=CVM_CODE,
        ticker=TICKER,
        cost_of_debt=COST_OF_DEBT,
        terminal_growth=TERM_GROWTH,
        forecast_years=FORECAST_YRS,
        tax_rate=TAX_RATE,
    )

    # ── Extração ─────────────────────────────────────────────
    wacc_data  = resultado["wacc_data"]
    historical = resultado["historical_df"]
    combined   = resultado["combined_df"]
    dcf        = resultado["dcf_results"]
    ev         = resultado["enterprise_value"]
    net_debt   = resultado["net_debt"]
    eq_value   = resultado["equity_value"]
    fcff_s     = combined["FCFF"]
    wacc       = wacc_data["wacc"]
    market_cap = wacc_data.get("market_cap")

    # ── Preço atual ───────────────────────────────────────────
    try:
        info          = yf.Ticker(TICKER).info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        current_price = None

    price_dcf = eq_value / SHARES_OUT if SHARES_OUT else None
    upside    = (price_dcf / current_price - 1) if (price_dcf and current_price) else None

    # ── KPIs ──────────────────────────────────────────────────
    roic      = calc_roic(historical, TAX_RATE)
    roe       = calc_roe(historical)
    ev_ebitda = calc_ev_ebitda(ev, historical)
    ev_ebit   = calc_ev_ebit(ev, historical)
    pe        = calc_pe(eq_value, historical)
    rev_cagr  = calc_cagr(historical["REVENUE"])
    ebit_cagr = calc_cagr(historical["EBIT"])
    rev_last  = historical["REVENUE"].iloc[-1]
    ebit_last = historical["EBIT"].iloc[-1]
    ni_last   = historical.get("NET_INCOME", pd.Series([0])).iloc[-1]
    fcff_last = fcff_s[fcff_s.index <= 2024].iloc[-1] if not fcff_s.empty else None
    fcff_yld  = fcff_last / market_cap if (fcff_last and market_cap) else None
    real_ret  = (1 + wacc) / (1 + IPCA_LONG_TERM) - 1

    # TIR
    proj_fcff = fcff_s[fcff_s.index > 2024]
    irr = None
    if market_cap and len(proj_fcff) >= 3:
        irr = _calc_irr([-market_cap] + list(proj_fcff.values))

    rec = recommendation(upside or 0)

    # ── Salva Excel ───────────────────────────────────────────
    output_file = f"valuation_output_{empresa_key}.xlsx"
    with pd.ExcelWriter(output_file) as writer:
        historical.to_excel(writer, sheet_name="historical")
        resultado["projection"].to_excel(writer, sheet_name="projection")
        combined.to_excel(writer, sheet_name="valuation")
    print(f"  Salvo: {output_file}")

    # ── Dashboard Terminal ────────────────────────────────────
    print(f"\n{sep}")
    print(f"  📊 VALUATION — {NOME} ({TICKER})")
    print(sep)

    print(f"\n  💰 PREÇO & UPSIDE")
    print(sep2)
    if current_price: print(f"  Preço de Tela        : R$ {current_price:>10.2f} / ação")
    if price_dcf:     print(f"  Preço Justo (DCF)    : R$ {price_dcf:>10.2f} / ação")
    if upside is not None:
        arrow = "▲" if upside > 0 else "▼"
        label = "(subavaliada)" if upside > 0 else "(sobreavaliada)"
        print(f"  Upside / Downside    :  {arrow} {abs(upside):.1%}  {label}")
    if market_cap: print(f"  Market Cap (mercado) : R$ {market_cap/1e9:>8.1f} bi")
    print(      f"  Equity Value (DCF)   : R$ {eq_value/1e9:>8.1f} bi")

    print(f"\n  💡 RECOMENDAÇÃO")
    print(sep2)
    print(f"  {rec}")
    if irr:
        spread = irr - wacc
        print(f"  TIR implícita : {irr:.1%}  |  Spread TIR−WACC: {spread:+.1%}")
        print(f"  Equivalente   : IPCA + {(irr - IPCA_LONG_TERM)*100:.1f}% a.a.")

    print(f"\n  📈 VALUATION DCF")
    print(sep2)
    print(f"  PV FCFs Explícitos   : R$ {dcf['pv_fcf']/1e9:>8.1f} bi")
    print(f"  Valor Terminal (PV)  : R$ {dcf['pv_terminal']/1e9:>8.1f} bi")
    print(f"  Enterprise Value     : R$ {ev/1e9:>8.1f} bi")
    print(f"  (−) Dívida Líquida   : R$ {net_debt/1e9:>8.1f} bi")
    print(f"  Equity Value         : R$ {eq_value/1e9:>8.1f} bi")
    print(f"  % Valor Terminal/EV  :    {dcf['pv_terminal']/ev:.0%}")

    print(f"\n  ⚙️  WACC")
    print(sep2)
    print(f"  Beta                 : {wacc_data['beta']:.2f}")
    print(f"  Rf (nominal)         : {wacc_data['risk_free_nominal']*100:.2f}%")
    print(f"  ERP (Damodaran)      : {wacc_data['equity_risk_premium']*100:.2f}%")
    print(f"  Ke (custo equity)    : {wacc_data['cost_of_equity']*100:.2f}%")
    print(f"  Kd líq. IR           : {wacc_data['after_tax_cost_of_debt']*100:.2f}%")
    print(f"  Peso Equity          : {wacc_data.get('equity_weight',0)*100:.1f}%")
    print(f"  Peso Dívida          : {wacc_data.get('debt_weight',0)*100:.1f}%")
    print(f"  WACC                 : {wacc*100:.2f}%")
    print(f"  Retorno Real         : IPCA + {real_ret*100:.1f}% a.a.")

    print(f"\n  📉 MÚLTIPLOS")
    print(sep2)
    if ev_ebitda:  print(f"  EV/EBITDA            : {ev_ebitda:.1f}x")
    if ev_ebit:    print(f"  EV/EBIT              : {ev_ebit:.1f}x")
    if pe:         print(f"  P/E                  : {pe:.1f}x")
    rev_mult = ev / rev_last if rev_last else None
    if rev_mult:   print(f"  EV/Receita           : {rev_mult:.2f}x")
    if fcff_yld:   print(f"  FCF Yield            : {fcff_yld:.2%}")

    print(f"\n  🏭 OPERACIONAL — HISTÓRICO 2024")
    print(sep2)
    print(f"  Receita              : R$ {rev_last/1e9:.1f} bi")
    ebit_mg = ebit_last / rev_last if rev_last else None
    ni_mg   = ni_last   / rev_last if rev_last else None
    if ebit_mg:    print(f"  Margem EBIT          : {ebit_mg:.1%}")
    if ni_mg:      print(f"  Margem Líquida       : {ni_mg:.1%}")
    if roic:       print(f"  ROIC                 : {roic:.1%}")
    if roe:        print(f"  ROE                  : {roe:.1%}")
    if rev_cagr:   print(f"  CAGR Receita (7a)    : {rev_cagr:.1%} a.a.")
    if ebit_cagr:  print(f"  CAGR EBIT (7a)       : {ebit_cagr:.1%} a.a.")

    print(f"\n  🔮 FCFF PROJETADO")
    print(sep2)
    for year, val in fcff_s.items():
        flag = "  [hist]" if year <= 2024 else "  [proj]"
        print(f"  {year}: R$ {val/1e9:>6.2f} bi{flag}")

    print(f"\n  🔮 PREMISSAS")
    print(sep2)
    print(f"  Terminal Growth  : {TERM_GROWTH*100:.1f}%")
    print(f"  Forecast Years   : {FORECAST_YRS}")
    print(f"  Tax Rate         : {TAX_RATE*100:.0f}%")
    print(f"  Kd bruto         : {COST_OF_DEBT*100:.1f}%")
    print(f"  Shares Out       : {SHARES_OUT/1e6:.0f} mi")
    print(sep)
    print(f"  {rec}")
    print(sep)

    # ── Retorna dict para consolidação ────────────────────────
    return {
        "empresa":        empresa_key,
        "ticker":         TICKER,
        "setor":          cfg.get("setor", ""),
        "current_price":  current_price,
        "price_dcf":      price_dcf,
        "upside":         upside,
        "rec":            rec,
        "ev":             ev,
        "eq_value":       eq_value,
        "net_debt":       net_debt,
        "market_cap":     market_cap,
        "wacc":           wacc,
        "irr":            irr,
        "roic":           roic,
        "roe":            roe,
        "ev_ebitda":      ev_ebitda,
        "pe":             pe,
        "rev_cagr":       rev_cagr,
        "revenue":        rev_last,
        "ebit_margin":    ebit_mg,
    }


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Quais empresas rodar? Args da linha de comando ou todas
    args = sys.argv[1:]
    targets = args if args else list_companies()

    print(f"\n🚀 Rodando valuation para: {targets}")

    all_results = {}
    errors      = {}

    for empresa in targets:
        try:
            result = run_company(empresa)
            all_results[empresa] = result
        except Exception as e:
            print(f"\n❌ Erro em {empresa}: {e}")
            errors[empresa] = str(e)

    # ── Sumário Comparativo ───────────────────────────────────
    if len(all_results) > 1:
        sep = "=" * 60
        print(f"\n\n{sep}")
        print(f"  📊 SUMÁRIO COMPARATIVO — {len(all_results)} EMPRESAS")
        print(sep)
        header = f"  {'Empresa':<10} {'Preço':>8} {'Justo':>8} {'Upside':>8} {'WACC':>7} {'ROIC':>7}  Rec"
        print(header)
        print("─" * 65)
        for emp, r in all_results.items():
            price_s  = f"R${r['current_price']:.2f}" if r['current_price'] else "  N/A  "
            justo_s  = f"R${r['price_dcf']:.2f}"     if r['price_dcf']     else "  N/A  "
            upside_s = f"{r['upside']:+.1%}"          if r['upside'] is not None else "  N/A "
            wacc_s   = f"{r['wacc']:.1%}"
            roic_s   = f"{r['roic']:.1%}"             if r['roic'] else "  N/A "
            print(f"  {emp:<10} {price_s:>8} {justo_s:>8} {upside_s:>8} {wacc_s:>7} {roic_s:>7}  {r['rec']}")
        print(sep)

    # ── Salva JSON para o dashboard futuro ───────────────────
    def to_serializable(obj):
        if isinstance(obj, (np.floating, float)):
            return None if (obj != obj) else float(obj)  # NaN → None
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        return obj

    json_results = {
        k: {kk: to_serializable(vv) for kk, vv in v.items()}
        for k, v in all_results.items()
    }

    with open("valuation_results.json", "w", encoding="utf-8") as f:
        json.dump(json_results, f, ensure_ascii=False, indent=2)

    print("\n📁 valuation_results.json salvo (pronto para o dashboard)")

    if errors:
        print(f"\n⚠️  Erros: {errors}")