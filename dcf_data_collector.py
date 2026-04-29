"""
dcf_data_collector.py v2 — Shipyard | Vela Capital
Coleta DRE trimestral completa: Receita, COGS, SG&A, EBIT, Capex, DA, WC
Metodologia: CAGR trimestral vs % Receita — usa menor desvio padrão
"""
import numpy as np
import pandas as pd
import yfinance as yf
import json, time
from pathlib import Path

def _to_f(v):
    try: return float(v) if pd.notna(v) else None
    except: return None

def _get_row(df, labels):
    for lbl in labels:
        if lbl in df.index:
            row = df.loc[lbl]
            if row.notna().any(): return row
    return None

def _clean(series, n=8):
    if series is None: return []
    vals = [_to_f(v) for v in series.values[:n]]
    return [v for v in vals if v is not None]

def _cagr_quarterly(vals):
    """CAGR trimestral anualizado + std"""
    if len(vals) < 3: return None, 999
    rates = [(vals[i]/vals[i+1]-1) for i in range(len(vals)-1)
             if vals[i+1] and vals[i+1]>0 and vals[i] is not None]
    if len(rates) < 2: return None, 999
    cagr_q = np.mean(rates)
    cagr_aa = (1+cagr_q)**4 - 1
    return float(cagr_aa), float(np.std(rates))

def _pct_rev(num_vals, rev_vals):
    """Média e std de num/rev"""
    pairs = [(n/r) for n,r in zip(num_vals,rev_vals)
             if r and r>0 and n is not None]
    if len(pairs) < 2: return None, 999
    return float(np.mean(pairs)), float(np.std(pairs))

def _best(cagr, cagr_std, pct, pct_std):
    """Retorna (valor, método, std) com menor dispersão"""
    opts = []
    if cagr is not None: opts.append((cagr_std, cagr, "cagr"))
    if pct  is not None: opts.append((pct_std,  pct,  "pct_rev"))
    if not opts: return None, "none", 999
    opts.sort()
    return opts[0][1], opts[0][2], opts[0][0]

def collect(ticker_sa):
    out = {"ticker": ticker_sa, "ok": False}
    try:
        stk = yf.Ticker(ticker_sa)
        qf  = stk.quarterly_financials
        qcf = stk.quarterly_cashflow
        qbs = stk.quarterly_balance_sheet

        if qf is None or qf.empty: return out

        # ── RECEITA ──────────────────────────────────────────────
        rev_s = _get_row(qf, ["Total Revenue","Operating Revenue"])
        if rev_s is None: return out
        rev = _clean(rev_s)
        if len(rev) < 3: return out

        rev_now_aa = rev[0] * 4
        out["revenue_last"] = rev_now_aa

        rev_cagr, rev_cagr_std = _cagr_quarterly(rev)
        # Receita: só CAGR faz sentido (não tem % de referência)
        cagr_safe = rev_cagr if rev_cagr and rev_cagr > -0.20 else 0.03
        out["rev_cagr_hist"] = float(np.clip(cagr_safe, -0.20, 0.40))
        out["rev_cagr_std"]  = float(rev_cagr_std)
        out["rev_method"]    = "cagr"

        # ── COGS ─────────────────────────────────────────────────
        cogs_s = _get_row(qf, ["Cost Of Revenue","Reconciled Cost Of Revenue",
                                "Cost Of Goods And Services Sold"])
        if cogs_s is not None:
            cogs = [abs(v) for v in _clean(cogs_s)]
            if len(cogs) >= 3:
                cg_cagr, cg_cagr_std = _cagr_quarterly(cogs)
                cg_pct,  cg_pct_std  = _pct_rev(cogs, rev[:len(cogs)])
                val, meth, std = _best(cg_cagr, cg_cagr_std, cg_pct, cg_pct_std)
                out["cogs_method"]  = meth
                out["cogs_pct_rev"] = cg_pct
                out["cogs_cagr"]    = cg_cagr
                out["cogs_proj"]    = val   # valor a usar na projeção
                out["cogs_std"]     = std
                out["cogs_last"]    = cogs[0] * 4

        # ── GROSS PROFIT ─────────────────────────────────────────
        gp_s = _get_row(qf, ["Gross Profit"])
        if gp_s is not None:
            gp = _clean(gp_s)
            if len(gp) >= 3:
                gp_pct, gp_pct_std = _pct_rev(gp, rev[:len(gp)])
                gp_cagr, gp_cagr_std = _cagr_quarterly(gp)
                val, meth, std = _best(gp_cagr, gp_cagr_std, gp_pct, gp_pct_std)
                out["gp_method"]  = meth
                out["gp_pct_rev"] = gp_pct
                out["gp_proj"]    = val
                out["gp_std"]     = std

        # ── SG&A ─────────────────────────────────────────────────
        sga_s = _get_row(qf, ["Selling General And Administration",
                               "Operating Expense","Selling And Marketing Expense"])
        if sga_s is not None:
            sga = [abs(v) for v in _clean(sga_s)]
            if len(sga) >= 3:
                sg_cagr, sg_cagr_std = _cagr_quarterly(sga)
                sg_pct,  sg_pct_std  = _pct_rev(sga, rev[:len(sga)])
                val, meth, std = _best(sg_cagr, sg_cagr_std, sg_pct, sg_pct_std)
                out["sga_method"]  = meth
                out["sga_pct_rev"] = sg_pct
                out["sga_cagr"]    = sg_cagr
                out["sga_proj"]    = val
                out["sga_std"]     = std
                out["sga_last"]    = sga[0] * 4

        # ── EBIT (direto — para fallback) ─────────────────────────
        ebit_s = _get_row(qf, ["EBIT","Operating Income"])
        if ebit_s is not None:
            ebit = _clean(ebit_s)
            if len(ebit) >= 3:
                eb_cagr, eb_cagr_std = _cagr_quarterly(ebit)
                eb_pct,  eb_pct_std  = _pct_rev(ebit, rev[:len(ebit)])
                val, meth, std = _best(eb_cagr, eb_cagr_std, eb_pct, eb_pct_std)
                out["ebit_method"]      = meth
                out["ebit_margin_hist"] = eb_pct
                out["ebit_cagr"]        = eb_cagr
                out["ebit_proj"]        = val
                out["ebit_std"]         = std
                out["ebit_last"]        = ebit[0] * 4
                # Média ponderada 8 trimestres
                w = [0.25,0.20,0.15,0.12,0.10,0.08,0.06,0.04][:len(ebit)]
                out["ebit_3y_avg"] = float(sum(e*wi for e,wi in zip(ebit,w))/sum(w)*4)

        # ── CAPEX ────────────────────────────────────────────────
        capex_s = _get_row(qcf, ["Capital Expenditure","Purchase Of PPE",
                                  "Net PPE Purchase And Sale"]) if qcf is not None else None
        if capex_s is not None:
            capex = [abs(v) for v in _clean(capex_s)]
            if len(capex) >= 3:
                cx_cagr, cx_cagr_std = _cagr_quarterly(capex)
                cx_pct,  cx_pct_std  = _pct_rev(capex, rev[:len(capex)])
                val, meth, std = _best(cx_cagr, cx_cagr_std, cx_pct, cx_pct_std)
                out["capex_method"]  = meth
                out["capex_pct_rev"] = cx_pct
                out["capex_cagr"]    = cx_cagr
                out["capex_proj"]    = val
                out["capex_std"]     = std
                out["capex_last"]    = capex[0] * 4

        # ── D&A ──────────────────────────────────────────────────
        da_s = _get_row(qcf, ["Depreciation And Amortization",
                               "Reconciled Depreciation","Depreciation"]) if qcf is not None else None
        ppe_s = _get_row(qbs, ["Gross PPE"]) if qbs is not None else None

        if da_s is not None:
            da = [abs(v) for v in _clean(da_s)]
            if len(da) >= 3:
                out["da_last"] = da[0] * 4
                # 3 métodos: da/capex, da/ppe, da/rev
                methods_da = []
                if capex_s is not None and len(capex) >= 3:
                    r1,s1 = _pct_rev(da[:len(capex)], capex[:len(da)])
                    if r1: methods_da.append((s1, r1, "da_pct_capex"))
                if ppe_s is not None:
                    ppe = [abs(v) for v in _clean(ppe_s)]
                    if len(ppe) >= 3:
                        r2,s2 = _pct_rev(da[:len(ppe)], ppe[:len(da)])
                        if r2: methods_da.append((s2, r2, "da_pct_ppe"))
                r3,s3 = _pct_rev(da, rev[:len(da)])
                if r3: methods_da.append((s3, r3, "da_pct_rev"))

                if methods_da:
                    methods_da.sort()
                    out["da_method"]    = methods_da[0][2]
                    out["da_ratio"]     = float(methods_da[0][1])
                    out["da_pct_rev"]   = float(r3) if r3 else None
                    out["da_pct_capex"] = float(methods_da[0][1]) if methods_da[0][2]=="da_pct_capex" else None

        # ── CAPITAL DE GIRO ───────────────────────────────────────
        if qbs is not None and not qbs.empty:
            wc_op_series = []
            for col in qbs.columns[:8]:
                bs = qbs[col]
                ar  = abs(_to_f(bs.get("Accounts Receivable")) or 0)
                inv = abs(_to_f(bs.get("Inventory")) or 0)
                tax_r = abs(_to_f(bs.get("Taxes Receivable")) or 0)
                ap  = abs(_to_f(bs.get("Accounts Payable")) or 0)
                ttp = abs(_to_f(bs.get("Total Tax Payable")) or 0)
                ocl = abs(_to_f(bs.get("Other Current Liabilities")) or 0)
                wc_op_series.append((ar+inv+tax_r) - (ap+ttp+ocl))

            if len(wc_op_series) >= 4:
                # Dias via COGS/Receita
                cogs_q2 = [abs(v) for v in _clean(_get_row(qf, ["Cost Of Revenue","Reconciled Cost Of Revenue"]) if _get_row(qf, ["Cost Of Revenue","Reconciled Cost Of Revenue"]) is not None else pd.Series([]))]
                ar_q = [abs(_to_f(qbs[col].get("Accounts Receivable")) or 0) for col in qbs.columns[:8]]
                ap_q = [abs(_to_f(qbs[col].get("Accounts Payable")) or 0) for col in qbs.columns[:8]]
                inv_q= [abs(_to_f(qbs[col].get("Inventory")) or 0) for col in qbs.columns[:8]]

                dias_ar  = [ar/r*90 for ar,r in zip(ar_q,rev[:len(ar_q)]) if r>0]
                dias_ap  = [ap/c*90 for ap,c in zip(ap_q,cogs_q2[:len(ap_q)]) if c>0] if cogs_q2 else []
                dias_inv = [iv/c*90 for iv,c in zip(inv_q,cogs_q2[:len(inv_q)]) if c>0] if cogs_q2 else []

                if dias_ar and dias_ap:
                    out["dias_ar_mean"]  = float(np.mean(dias_ar))
                    out["dias_ar_std"]   = float(np.std(dias_ar))
                    out["dias_ap_mean"]  = float(np.mean(dias_ap))
                    out["dias_ap_std"]   = float(np.std(dias_ap))
                    out["dias_inv_mean"] = float(np.mean(dias_inv)) if dias_inv else 0.0
                    out["wc_method"]     = "dias"

                # Plano B: múltiplos ratios
                wc_ratios = {}
                wc_rev = [w/r for w,r in zip(wc_op_series,rev[:len(wc_op_series)]) if r>0]
                if len(wc_rev)>=3: wc_ratios["wc_pct_rev"] = (np.mean(wc_rev), np.std(wc_rev))
                at_q = _clean(_get_row(qbs,["Total Assets"]))
                if at_q:
                    wc_at = [w/a for w,a in zip(wc_op_series,at_q[:len(wc_op_series)]) if a>0]
                    if len(wc_at)>=3: wc_ratios["wc_pct_ativo"] = (np.mean(wc_at), np.std(wc_at))

                if wc_ratios:
                    best = min(wc_ratios.items(), key=lambda x: x[1][1])
                    out["wc_best_method"] = best[0]
                    out["wc_best_ratio"]  = float(best[1][0])
                    out["wc_best_std"]    = float(best[1][1])
                    out["wc_last"]        = float(wc_op_series[0])
                    out["wc_pct_rev"]     = float(wc_ratios.get("wc_pct_rev",(None,))[0]) if "wc_pct_rev" in wc_ratios else None

        # ── NET DEBT & SHARES ────────────────────────────────────
        if qbs is not None and not qbs.empty:
            bs0 = qbs[qbs.columns[0]]
            debt = abs(_to_f(bs0.get("Total Debt")) or 0)
            cash = abs(_to_f(bs0.get("Cash And Cash Equivalents")) or 0)
            sti  = abs(_to_f(bs0.get("Other Short Term Investments")) or 0)
            out["net_debt"] = float(debt - cash - sti)
            out["div_liq"]  = out["net_debt"]

        sh_s = _get_row(qf, ["Diluted Average Shares","Basic Average Shares"])
        if sh_s is not None:
            s = _to_f(sh_s.iloc[0])
            if s: out["shares_out"] = float(s)

        out["ok"] = True
        return out
    except Exception as e:
        out["error"] = str(e)
        return out

def run_all():
    results = json.load(open("/opt/shipyard/valuation_results_combined.json"))
    updated = errors = 0
    total = len(results)
    for i,(emp,v) in enumerate(results.items()):
        tk = v.get("ticker","")
        if not tk: continue
        data = collect(tk)
        time.sleep(0.12)
        if data.get("ok"):
            for k,val in data.items():
                if k not in ["ticker","ok","error"] and val is not None:
                    results[emp][k] = val
            updated += 1
        else:
            errors += 1
        if (i+1)%30==0:
            print(f"  {i+1}/{total}...")
            json.dump(results,open("/opt/shipyard/valuation_results_combined.json","w"),
                      ensure_ascii=False,indent=2)
    json.dump(results,open("/opt/shipyard/valuation_results_combined.json","w"),
              ensure_ascii=False,indent=2)
    print(f"Atualizadas: {updated} | Erros: {errors}")

if __name__=="__main__":
    # Teste WEGE3
    d = collect("WEGE3.SA")
    print("=== WEGE3 ===")
    for k,v in sorted(d.items()):
        if k not in ["ok","error","ticker"]: print(f"  {k}: {v}")
    resp = input("\nRodar todas? (s/n): ")
    if resp.lower()=="s": run_all()
