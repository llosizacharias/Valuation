import json
import pandas as pd
import yfinance as yf
from companies_config import COMPANIES
from app.deterministic_runner import run_deterministic_valuation

OUTPUT_JSON = "valuation_results.json"

def serialize(obj):
    import numpy as np
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    raise TypeError(f"Not serializable: {type(obj)}")

def clean(d):
    if isinstance(d, dict):
        return {k: clean(v) for k, v in d.items()
                if not isinstance(v, (pd.DataFrame, pd.Series))}
    return d

def get_price(ticker):
    try:
        t = yf.Ticker(ticker)
        p = t.fast_info.get("lastPrice") or t.fast_info.get("last_price")
        if p: return float(p)
        h = t.history(period="1d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except:
        return None

def run_all():
    results = {}
    for nome, cfg in COMPANIES.items():
        print(f"\n{'='*55}\n  {nome} ({cfg['ticker']})\n{'='*55}")
        try:
            result = run_deterministic_valuation(
                dfp_folder=f"data/raw/{nome}",
                empresa=nome,
                cvm_code=cfg["cvm_code"],
                ticker=cfg["ticker"],
                terminal_growth=cfg.get("terminal_growth", 0.04),
                cost_of_debt=cfg.get("cost_of_debt", 0.12),
                ifrs16_lease_total=cfg.get("ifrs16_lease_total"),
                revenue_growth_override=cfg.get("revenue_growth_override"),
                ebit_margin_override=cfg.get("ebit_margin_override"),
            )
            if not result:
                print(f"  ❌ resultado vazio"); continue

            # Calcula price_fair e upside
            shares    = cfg.get("shares_out", 0)
            eq_value  = result.get("equity_value", 0)
            ev        = result.get("enterprise_value", 0)
            net_debt  = result.get("net_debt", 0)
            price_now = get_price(cfg["ticker"])
            price_fair = (eq_value / shares) if shares and eq_value else 0
            upside     = ((price_fair - price_now) / price_now) if price_now and price_fair else 0

            if upside > 0.15:   rec = "COMPRA FORTE"
            elif upside > 0.05: rec = "COMPRA"
            elif upside > -0.15:rec = "NEUTRO"
            elif upside > -0.30:rec = "VENDA"
            else:               rec = "VENDA FORTE"

            wacc_data  = result.get("wacc_data", {})
            multiples  = result.get("multiples", {})
            dcf        = result.get("dcf_results", {})
            combined   = result.get("combined_df")

            # FCFF série
            fcff_series = {}
            if combined is not None and isinstance(combined, pd.DataFrame) and "FCFF" in combined.columns:
                fcff_series = {str(int(k)): float(v) for k, v in combined["FCFF"].items()}

            # Métricas operacionais
            hist = result.get("historical_df")
            roic = roe = ebit_margin = net_margin = 0.0
            cagr_revenue = cagr_ebit = 0.0
            if hist is not None and isinstance(hist, pd.DataFrame):
                try:
                    last = hist.iloc[-1]
                    rev  = abs(last.get("REVENUE", 1)) or 1
                    ebit = last.get("EBIT", 0)
                    ni   = last.get("NET_INCOME", 0)
                    eq   = last.get("EQUITY", 1) or 1
                    debt = last.get("DEBT_SHORT", 0) + last.get("DEBT_LONG", 0)
                    inv_cap = debt + eq or 1
                    ebit_margin = float(ebit / rev)
                    net_margin  = float(ni / rev)
                    roic = float(ebit * 0.66 / inv_cap)
                    roe  = float(ni / eq)
                    if len(hist) >= 2:
                        r0 = abs(hist.iloc[0].get("REVENUE", 0))
                        rn = abs(hist.iloc[-1].get("REVENUE", 0))
                        n  = len(hist) - 1
                        cagr_revenue = float((rn/r0)**(1/n) - 1) if r0 > 0 else 0
                except: pass

            record = {
                "empresa":           nome,
                "ticker":            cfg["ticker"],
                "price_now":         price_now or 0,
                "price_fair":        price_fair,
                "upside":            upside,
                "recomendacao":      rec,
                "enterprise_value":  ev,
                "equity_value":      eq_value,
                "net_debt":          net_debt,
                "wacc":              wacc_data.get("wacc", 0),
                "beta":              wacc_data.get("beta", 0),
                "wacc_data":         wacc_data,
                "roic":              roic,
                "roe":               roe,
                "ebit_margin":       ebit_margin,
                "net_margin":        net_margin,
                "cagr_revenue":      cagr_revenue,
                "ev_ebitda":         multiples.get("ev_ebitda", 0),
                "ev_ebit":           multiples.get("ev_ebit", 0),
                "pe":                multiples.get("pe", 0),
                "dcf_pv_fcf":        dcf.get("pv_fcf", 0),
                "dcf_pv_terminal":   dcf.get("pv_terminal", 0),
                "terminal_growth":   cfg.get("terminal_growth", 0.04),
                "cost_of_debt":      cfg.get("cost_of_debt", 0.12),
                "shares_out":        shares,
                "fcff_series":       fcff_series,
            }

            results[nome] = record
            print(f"  ✅ tela R${price_now:.2f} | justo R${price_fair:.2f} | upside {upside*100:.1f}% | {rec}")

        except Exception as e:
            print(f"  ❌ erro: {e}")
            import traceback; traceback.print_exc()

    with open(OUTPUT_JSON, "w") as f:
        json.dump(clean(results), f, default=serialize, indent=2)
    print(f"\n✅ {OUTPUT_JSON} salvo com: {list(results.keys())}")

if __name__ == "__main__":
    run_all()
