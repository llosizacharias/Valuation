"""
main.py — ponto de entrada do sistema de valuation.

Uso:
  python main.py                    # roda todas as empresas
  python main.py COGNA              # roda só COGNA
  python main.py WEG COGNA          # roda lista específica
"""

import sys
import json
import pandas as pd
from pathlib import Path

from companies_config import COMPANIES, get_company
from app.deterministic_runner import run_deterministic_valuation


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _fmt_bi(v):
    try:
        return f"R$ {float(v)/1e9:.1f} bi"
    except Exception:
        return str(v)

def _fmt_pct(v):
    try:
        return f"{float(v)*100:.1f}%"
    except Exception:
        return str(v)

def _fmt_price(v):
    try:
        return f"R$ {float(v):.2f} / ação"
    except Exception:
        return str(v)


# ─────────────────────────────────────────────────────────────
# RUNNER POR EMPRESA
# ─────────────────────────────────────────────────────────────

def run_company(nome: str) -> dict | None:
    cfg = get_company(nome)

    ticker        = cfg["ticker"]
    cvm_code      = cfg["cvm_code"]
    shares_out    = cfg["shares_out"]
    term_growth   = cfg.get("terminal_growth", 0.035)
    cost_of_debt  = cfg.get("cost_of_debt",    0.12)

    # ── Overrides forward-looking (opcionais) ──────────────
    rev_override   = cfg.get("revenue_growth_override")
    ebit_override  = cfg.get("ebit_margin_override")

    dfp_folder = str(Path("data/raw") / nome)

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  🏢 {ticker}")
    print(sep)

    # ── MZ API (tenta mas não bloqueia) ───────────────────
    try:
        from data_layer.download.mz_downloader import MZDownloader
        company_id = cfg.get("company_id_mz")
        if company_id:
            print(f"\n[1/4] Buscando documentos MZ...")
            dl = MZDownloader(company_id, nome)
            dl.download_all(base_folder="data/raw")
    except Exception as e:
        print(f"[1/4] MZ indisponível — {e}")

    # ── CVM Downloader ────────────────────────────────────
    print(f"\n[3/4] MZ indisponível — baixando DFPs direto da CVM...")
    print(f"  Código CVM: {cvm_code} | Fonte: dados.cvm.gov.br")
    try:
        from data_layer.download.cvm_downloader import CVMDownloader
        dl_cvm = CVMDownloader(cvm_code=cvm_code, empresa=nome)
        dl_cvm.download_all(years=list(range(2019, 2026)))
    except Exception as e:
        print(f"  [WARN] CVM Downloader: {e}")

    # ── Valuation ─────────────────────────────────────────
    print(f"\n[4/4] Calculando valuation...")
    try:
        result = run_deterministic_valuation(
            dfp_folder=dfp_folder,
            empresa=nome,
            cvm_code=cvm_code,
            ticker=ticker,
            cost_of_debt=cost_of_debt,
            terminal_growth=term_growth,
            revenue_growth_override=rev_override,
            ebit_margin_override=ebit_override,
        )
    except Exception as e:
        print(f"❌ Erro em {nome}: {e}")
        import traceback; traceback.print_exc()
        return None

    ev           = result["enterprise_value"]
    equity_value = result["equity_value"]
    net_debt     = result["net_debt"]
    wacc_data    = result["wacc_data"]
    multiples    = result["multiples"]
    hist         = result["historical_df"]
    proj         = result["projection"]
    combined     = result["combined_df"]

    # ── Preço justo ───────────────────────────────────────
    try:
        import yfinance as yf
        price_now = yf.Ticker(ticker).info.get("currentPrice") or \
                    yf.Ticker(ticker).info.get("regularMarketPrice", 0)
    except Exception:
        price_now = 0

    market_cap    = wacc_data.get("market_cap") or 0
    price_fair    = equity_value / shares_out if shares_out else 0
    upside        = (price_fair / price_now - 1) if price_now else None

    if upside is not None:
        if upside > 0.15:
            rec = "🟢 COMPRA"
        elif upside > -0.15:
            rec = "🟡 NEUTRO"
        elif upside > -0.30:
            rec = "🟠 VENDA"
        else:
            rec = "🔴 VENDA FORTE"
    else:
        rec = "⚪ S/D"

    # ── ROIC / ROE ────────────────────────────────────────
    try:
        last = hist.iloc[-1]
        ebit_last = float(last.get("EBIT", 0))
        equity    = float(last.get("EQUITY", 1)) or 1
        inv_cap   = (float(last.get("DEBT_SHORT", 0)) + float(last.get("DEBT_LONG", 0)) + float(last.get("EQUITY", 1))) or 1
        roic      = ebit_last * (1 - 0.34) / (inv_cap or 1)
        roe       = (float(hist["NET_INCOME"].iloc[-1]) / equity) if "NET_INCOME" in hist.columns else None
        rev_last  = float(hist["REVENUE"].iloc[-1])
        margin_ebit = ebit_last / rev_last if rev_last else None
        net_inc   = float(hist["NET_INCOME"].iloc[-1]) if "NET_INCOME" in hist.columns else 0
        margin_net  = net_inc / rev_last if rev_last else None
    except Exception:
        roic = roe = margin_ebit = margin_net = None

    # ── CAGR Receita / EBIT ───────────────────────────────
    try:
        rev_series  = hist["REVENUE"].dropna()
        ebit_series = hist["EBIT"].dropna()
        n = len(rev_series) - 1
        cagr_rev  = (rev_series.iloc[-1]  / rev_series.iloc[0])  ** (1/n) - 1 if n > 0 else None
        cagr_ebit = (ebit_series.iloc[-1] / ebit_series.iloc[0]) ** (1/n) - 1 \
                    if n > 0 and ebit_series.iloc[0] > 0 else None
    except Exception:
        cagr_rev = cagr_ebit = None

    # ── WACC ──────────────────────────────────────────────
    beta   = wacc_data.get("beta", 0)
    rf_nom = wacc_data.get("risk_free_nominal", 0)
    erp    = wacc_data.get("equity_risk_premium", 0)
    ke     = wacc_data.get("cost_of_equity", 0)
    kd     = wacc_data.get("after_tax_cost_of_debt", 0)
    eq_w   = wacc_data.get("equity_weight", 0)
    dbt_w  = wacc_data.get("debt_weight", 0)
    wacc   = wacc_data.get("wacc", 0)
    rr     = wacc_data.get("real_return") or (1 + wacc) / 1.04 - 1

    # ── FCF Yield ─────────────────────────────────────────
    try:
        fcff_last  = float(combined.loc[combined.index == combined.index.max(), "FCFF"].iloc[0])
        fcf_yield  = fcff_last / market_cap if market_cap else None
    except Exception:
        fcf_yield = None

    # ── Múltiplos EV ─────────────────────────────────────
    ev_ebitda = multiples.get("EV/EBITDA")
    ev_ebit   = multiples.get("EV/EBIT")
    pe        = multiples.get("P/E")
    ev_rev    = multiples.get("EV/Revenue")

    # ── Output ───────────────────────────────────────────
    last_year = hist.index.max()
    nome_completo = {
        "WEG":   "WEG S.A.",
        "COGNA": "Cogna Educação S.A.",
    }.get(nome, nome)

    print(f"""
{sep}
  📊 VALUATION — {nome_completo} ({ticker})
{sep}

  💰 PREÇO & UPSIDE
{'─'*60}
  Preço de Tela        : {_fmt_price(price_now)}
  Preço Justo (DCF)    : {_fmt_price(price_fair)}
  Upside / Downside    :  {'▲' if (upside or 0)>0 else '▼'} {abs(upside*100):.1f}%  ({'subavaliada' if (upside or 0)>0 else 'sobreavaliada'})
  Market Cap (mercado) : {_fmt_bi(market_cap)}
  Equity Value (DCF)   : {_fmt_bi(equity_value)}

  💡 RECOMENDAÇÃO
{'─'*60}
  {rec}""")

    if rev_override or ebit_override:
        print(f"""
  ⚠️  OVERRIDES ATIVOS
{'─'*60}""")
        if rev_override:
            print(f"  Crescimento receita  : {_fmt_pct(rev_override)} (forward override)")
        if ebit_override:
            print(f"  Margem EBIT          : {_fmt_pct(ebit_override)} (forward override)")

    print(f"""
  📈 VALUATION DCF
{'─'*60}
  PV FCFs Explícitos   : {_fmt_bi(result['dcf_results'].get('pv_fcf'))}
  Valor Terminal (PV)  : {_fmt_bi(result['dcf_results'].get('pv_terminal'))}
  Enterprise Value     : {_fmt_bi(ev)}
  (−) Dívida Líquida   : {_fmt_bi(net_debt)}
  Equity Value         : {_fmt_bi(equity_value)}
  % Valor Terminal/EV  :    {result['dcf_results'].get('pv_terminal',0)/ev*100:.0f}%

  ⚙️  WACC
{'─'*60}
  Beta                 : {beta:.2f}
  Rf (nominal)         : {_fmt_pct(rf_nom)}
  ERP (Damodaran)      : {_fmt_pct(erp)}
  Ke (custo equity)    : {_fmt_pct(ke)}
  Kd líq. IR           : {_fmt_pct(kd)}
  Peso Equity          : {_fmt_pct(eq_w)}
  Peso Dívida          : {_fmt_pct(dbt_w)}
  WACC                 : {_fmt_pct(wacc)}
  Retorno Real         : IPCA + {_fmt_pct(rr)}

  📉 MÚLTIPLOS
{'─'*60}
  EV/EBITDA            : {f'{ev_ebitda:.1f}x' if ev_ebitda else 'n/d'}
  EV/EBIT              : {f'{ev_ebit:.1f}x' if ev_ebit else 'n/d'}
  P/E                  : {f'{pe:.1f}x' if pe else 'n/d'}
  EV/Receita           : {f'{ev_rev:.2f}x' if ev_rev else 'n/d'}
  FCF Yield            : {_fmt_pct(fcf_yield) if fcf_yield else 'n/d'}

  🏭 OPERACIONAL — HISTÓRICO {last_year}
{'─'*60}
  Receita              : {_fmt_bi(hist['REVENUE'].iloc[-1])}
  Margem EBIT          : {_fmt_pct(margin_ebit) if margin_ebit is not None else 'n/d'}
  Margem Líquida       : {_fmt_pct(margin_net) if margin_net is not None else 'n/d'}
  ROIC                 : {_fmt_pct(roic) if roic is not None else 'n/d'}
  ROE                  : {_fmt_pct(roe) if roe is not None else 'n/d'}
  CAGR Receita ({len(hist)-1}a)    : {_fmt_pct(cagr_rev) if cagr_rev else 'n/d'} a.a.
  CAGR EBIT ({len(hist)-1}a)       : {_fmt_pct(cagr_ebit) if cagr_ebit else 'n/d'} a.a.

  🔮 FCFF PROJETADO
{'─'*60}""")

    for yr, row in combined.iterrows():
        fcff_val = row.get("FCFF", float("nan"))
        tag = "[hist]" if yr <= last_year else "[proj]"
        print(f"  {yr}: R$ {fcff_val/1e9:6.2f} bi  {tag}")

    print(f"""
  🔮 PREMISSAS
{'─'*60}
  Terminal Growth  : {_fmt_pct(term_growth)}
  Forecast Years   : 6
  Tax Rate         : 34%
  Kd bruto         : {_fmt_pct(cost_of_debt)}
  Shares Out       : {shares_out//1_000_000} mi
{sep}
  {rec}
{sep}""")

    # ── Salva output individual ───────────────────────────
    try:
        out_path = f"valuation_output_{nome}.xlsx"
        with pd.ExcelWriter(out_path) as writer:
            hist.to_excel(writer,     sheet_name="historical")
            proj.to_excel(writer,     sheet_name="projection")
            combined.to_excel(writer, sheet_name="valuation")
        print(f"  Salvo: {out_path}")
    except Exception as e:
        print(f"  [WARN] Excel: {e}")

    return {
        "empresa":          nome,
        "ticker":           ticker,
        "price_now":        price_now,
        "price_fair":       price_fair,
        "upside":           upside,
        "recomendacao":     rec,
        "enterprise_value": ev,
        "equity_value":     equity_value,
        "net_debt":         net_debt,
        "wacc":             wacc,
        "beta":             beta,
        "overrides": {
            "revenue_growth": rev_override,
            "ebit_margin":    ebit_override,
        },
    }


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:]] if len(sys.argv) > 1 else list(COMPANIES.keys())

    print(f"🚀 Rodando valuation para: {args}")

    results = {}
    for nome in args:
        try:
            r = run_company(nome)
            if r:
                results[nome] = r
        except Exception as e:
            print(f"❌ Erro fatal em {nome}: {e}")
            import traceback; traceback.print_exc()

    # ── Salva JSON consolidado ────────────────────────────
    out = {}
    for nome, r in results.items():
        out[nome] = {k: (float(v) if hasattr(v, "__float__") else v)
                     for k, v in r.items() if not callable(v)}

    with open("valuation_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    print("\n📁 valuation_results.json salvo (pronto para o dashboard)")