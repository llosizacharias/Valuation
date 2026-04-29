"""
dcf_engine.py — Shipyard | Vela Capital v2
DCF com dois WACCs, Kd real, estrutura de capital real,
beta desalavancado/reavelado, FCFF real com:
- Receita projetada por CAGR histórico
- EBIT projetado pelo método mais estável (CAGR vs % Receita)
- Capex - D&A incremental (investimento líquido de expansão)
- ΔCapital de Giro = ΔCG/ΔRev × ΔRev
- D&A incremental (não cumulativo)
"""
import json
import numpy as np
from pathlib import Path

# ── PARÂMETROS MACROECONÔMICOS BRASIL 2026 ────────────────────────
DI_AA     = 0.1466   # DI Over aa — RF stress (cenário atual)
RF_BASE   = 0.085    # RF base = equilíbrio longo prazo (NTN-B convergência)
NTNB_NOM  = 0.1402   # NTN-B 2035 nominal
IPCA_LP   = 0.050    # IPCA longo prazo
NTNB_REAL = (1 + NTNB_NOM) / (1 + IPCA_LP) - 1
RF_EXPL   = RF_BASE   # base = equilíbrio; use DI_AA para stress
RF_IMPL   = NTNB_REAL + IPCA_LP
RF_STRESS = DI_AA    # cenário stress = DI atual
ERP       = 0.0747   # Damodaran 2026
TAX       = 0.34
ANOS      = 7
TG_PIB    = 0.023

# Beta desalavancado setorial (Damodaran 2026 EM)
BETA_U = {
    "energia":0.45,"saneamento":0.40,"financeiro":0.50,"banco":0.45,
    "tecnologia":0.90,"saude":0.65,"construc":0.80,"consumo":0.70,
    "petroleo":0.65,"minerac":0.75,"agro":0.65,"telecom":0.55,
    "varejo":0.80,"DEFAULT":0.70,
}

TG_SETOR = {
    "energia":0.035,"saneamento":0.040,"financeiro":0.060,"banco":0.060,
    "tecnologia":0.080,"saude":0.060,"construc":0.050,"consumo":0.050,
    "petroleo":0.025,"minerac":0.025,"agro":0.050,"telecom":0.030,
    "varejo":0.055,"DEFAULT":0.045,
}

CAPEX_DEFAULT = {
    "energia":0.18,"saneamento":0.20,"telecom":0.12,"petroleo":0.15,
    "minerac":0.14,"construc":0.08,"consumo":0.05,"varejo":0.04,
    "tecnologia":0.06,"saude":0.07,"agro":0.10,"DEFAULT":0.08,
}
DA_DEFAULT = {
    "energia":0.08,"saneamento":0.09,"telecom":0.10,"petroleo":0.09,
    "minerac":0.08,"construc":0.05,"consumo":0.04,"varejo":0.03,
    "tecnologia":0.07,"saude":0.05,"agro":0.06,"DEFAULT":0.06,
}
DCG_DEFAULT = {
    "banco":0.0,"financeiro":0.0,"seguro":0.0,
    "varejo":0.15,"consumo":0.12,"construc":0.18,"DEFAULT":0.10,
}

BANCOS = ["banco","financeiro","seguro","previdencia","credito"]

def _sk(sector):
    s = (sector or "").lower()
    for k in list(BETA_U.keys())[:-1]:
        if k in s: return k
    return "DEFAULT"

def _is_banco(sector):
    return any(b in (sector or "").lower() for b in BANCOS)

def _get_default(dct, setor):
    for k,v in dct.items():
        if k in setor: return v
    return dct.get("DEFAULT", list(dct.values())[-1])

# ── BETA ─────────────────────────────────────────────────────────
def unlever(bl, d_e): return bl / (1 + (1-TAX)*d_e)
def relever(bu, d_e): return bu * (1 + (1-TAX)*d_e)

# ── WACC ─────────────────────────────────────────────────────────
def calc_wacc(beta_l, kd, eq_mkt, nd, rf, erp):
    ke  = rf + beta_l * erp
    eq  = abs(eq_mkt or 1e9)
    nd  = max(0, nd or 0)
    t   = eq + nd
    return ke*(eq/t) + kd*(1-TAX)*(nd/t), ke

# ── PROJEÇÃO DE RECEITA ───────────────────────────────────────────
def proj_receita(v, ano):
    """Receita projetada usando CAGR histórico blended com setor"""
    setor = _sk(v.get("sector") or v.get("setor",""))
    tg_setor = TG_SETOR.get(setor, TG_SETOR["DEFAULT"])
    
    rev_base = float(v.get("revenue_last") or 0)
    if not rev_base: return None
    
    cagr_hist = v.get("rev_cagr_hist")
    if cagr_hist:
        # Blended 60% histórico + 40% setor — mean reversion
        cagr = 0.60*float(cagr_hist) + 0.40*tg_setor
    else:
        cagr = tg_setor
    
    # Cap: 2% a 10%
    cagr = max(0.02, min(cagr, 0.10))
    return rev_base * (1 + cagr)**ano

# ── PROJEÇÃO DE EBIT ──────────────────────────────────────────────
def proj_ebit(v, receita_proj):
    """
    Usa o método mais estável historicamente:
    - pct_rev: EBIT = margem_hist × Receita
    - cagr: EBIT cresce pelo CAGR histórico
    """
    metodo = v.get("ebit_method", "pct_rev")
    
    if metodo == "pct_rev" and v.get("ebit_margin_hist"):
        margin = float(v["ebit_margin_hist"])
        # Cap por setor — seguradoras/holdings podem ter margem > 100%
        # mas para DCF usamos margem operacional real
        setor = _sk(v.get("sector") or v.get("setor",""))
        max_margin = {
            "banco":0.40,"financeiro":0.40,"seguro":0.35,
            "energia":0.55,"saneamento":0.50,
            "DEFAULT":0.55
        }
        margin_cap = max_margin.get(setor, max_margin["DEFAULT"])
        margin = max(0.02, min(margin, margin_cap))
        return receita_proj * margin
    else:
        # CAGR — usa ebit base e CAGR setorial
        ebit_base = float(v.get("ebit_3y_avg") or v.get("ebit_last") or v.get("ebit") or 0)
        if not ebit_base: return None
        setor = _sk(v.get("sector") or v.get("setor",""))
        tg = TG_SETOR.get(setor, TG_SETOR["DEFAULT"])
        return ebit_base  # será multiplicado pelo crescimento no loop

# ── CAPEX LÍQUIDO ─────────────────────────────────────────────────
def proj_capex_liq(v, receita_proj, receita_ant):
    """
    Capex líquido = Capex - D&A incremental
    D&A incremental = variação média histórica da D&A (não cumulativa)
    """
    setor = _sk(v.get("sector") or v.get("setor",""))
    
    # Capex como % receita
    capex_pct = v.get("capex_pct_rev") or _get_default(CAPEX_DEFAULT, setor)
    capex_pct = max(0.01, min(float(capex_pct), 0.35))
    capex = receita_proj * capex_pct
    
    # D&A incremental (variação média histórica — não cumulativo)
    da_inc = v.get("da_incremental_avg")
    if da_inc is not None:
        # D&A incremental proporcional ao crescimento da receita
        if receita_ant and receita_ant > 0:
            delta_rev_pct = (receita_proj - receita_ant) / receita_ant
            da_inc_proj = float(da_inc) * (1 + delta_rev_pct)
        else:
            da_inc_proj = float(da_inc)
    else:
        # Fallback: % da receita
        da_pct = v.get("da_pct_rev") or _get_default(DA_DEFAULT, setor)
        da_base = float(v.get("da_last") or 0)
        if da_base and receita_ant:
            da_inc_proj = da_base * (receita_proj/receita_ant - 1)
        else:
            da_inc_proj = receita_proj * float(da_pct) * 0.15  # 15% do D&A total
    
    # Capex líquido = Capex - D&A incremental (mínimo zero)
    return max(0, capex - max(0, da_inc_proj))

# ── DELTA CAPITAL DE GIRO ─────────────────────────────────────────
def proj_dcg(v, receita_proj, receita_ant):
    """ΔCG = ΔCG/ΔRev × ΔRev"""
    if not receita_ant or receita_ant <= 0: return 0
    delta_rev = receita_proj - receita_ant
    
    setor = _sk(v.get("sector") or v.get("setor",""))
    dcg_pct = v.get("dcg_pct_drev")
    if dcg_pct is None:
        dcg_pct = _get_default(DCG_DEFAULT, setor)
    
    dcg_pct = max(-0.20, min(float(dcg_pct), 0.40))
    return delta_rev * dcg_pct

# ── FCFF POR ANO ──────────────────────────────────────────────────
def calc_fcff_ano(v, ano, receita_ant):
    """FCFF_t = EBIT_t×(1-t) - CapexLiq_t - ΔCG_t"""
    receita_t = proj_receita(v, ano)
    if not receita_t: return None, receita_t
    
    ebit_t = proj_ebit(v, receita_t)
    if not ebit_t: return None, receita_t
    
    nopat_t   = ebit_t * (1 - TAX)
    capex_liq = proj_capex_liq(v, receita_t, receita_ant)
    dcg_t     = proj_dcg(v, receita_t, receita_ant)
    
    fcff_t = nopat_t - capex_liq - dcg_t
    return fcff_t, receita_t

# ── DDM PARA BANCOS ───────────────────────────────────────────────
def calc_ddm(v, shares, price):
    lpa    = v.get("lpa")
    if not lpa: return None, {}
    lpa    = float(lpa)
    payout = v.get("payout") or 0.40
    if isinstance(payout, (int,float)) and payout > 1: payout /= 100
    payout = max(0.20, min(float(payout), 0.90))
    
    dps = lpa * payout
    beta_l = float(v.get("beta") or 1.0)
    ke = RF_EXPL + beta_l * ERP
    g  = 0.055
    if ke <= g: ke = g + 0.04
    
    pf = round(dps / (ke - g), 2)
    return pf, {"modelo":"DDM","lpa":lpa,"dps":round(dps,4),
                "ke_ddm":round(ke*100,2),"g_ddm":round(g*100,2),
                "wacc_expl":round(ke*100,2),"wacc_impl":round(ke*100,2)}

# ── DCF COMPLETO ──────────────────────────────────────────────────
def calc_dcf_full(v):
    price  = float(v.get("price_now") or 0)
    mktcap = v.get("mkt_cap")
    nd     = float(v.get("div_liq") or v.get("net_debt") or 0)
    sector = v.get("sector") or v.get("setor","") or ""
    setor  = _sk(sector)
    
    if not price or not mktcap: return None, {}
    shares = mktcap / price
    if shares <= 0: return None, {}
    
    if _is_banco(sector):
        return calc_ddm(v, shares, price)
    
    # Beta
    beta_u   = BETA_U[setor]
    nd_pos   = max(0, nd)
    d_e      = nd_pos / mktcap if mktcap > 0 else 0
    beta_l   = min(relever(beta_u, d_e), 2.5)
    
    # Kd via spread sobre RF
    spreads = {"banco":0.020,"energia":0.025,"saneamento":0.025,
               "telecom":0.030,"consumo":0.035,"varejo":0.040,
               "construc":0.045,"tecnologia":0.040,"saude":0.035,
               "petroleo":0.030,"minerac":0.030,"agro":0.035,"DEFAULT":0.035}
    kd = RF_EXPL + spreads.get(setor, spreads["DEFAULT"])
    if nd_pos < mktcap * 0.05: kd = RF_EXPL + 0.020
    
    # WACC explícito
    wacc_e, ke_e = calc_wacc(beta_l, kd, mktcap, nd_pos, RF_EXPL, ERP)
    
    # Receita base
    rev_base = float(v.get("revenue_last") or 0)
    if not rev_base: return None, {}
    
    # PV período explícito — FCFF projetado ano a ano
    pv = 0.0
    receita_ant = rev_base
    fcff_series = []
    
    for i in range(1, ANOS+1):
        fcff_i, receita_i = calc_fcff_ano(v, i, receita_ant)
        if not fcff_i:
            return None, {}
        pv += fcff_i / (1 + wacc_e)**i
        fcff_series.append(round(fcff_i, 0))
        receita_ant = receita_i
    
    # Estrutura terminal
    nd_term  = nd_pos * 0.70
    eq_term  = mktcap
    d_e_term = nd_term / eq_term if eq_term > 0 else 0
    beta_l_t = min(relever(beta_u, d_e_term), 2.5)
    kd_term  = RF_IMPL * 0.90
    wacc_i, ke_i = calc_wacc(beta_l_t, kd_term,
                              eq_term, nd_term, RF_IMPL, ERP)
    wacc_i = min(wacc_i, 0.18)
    
    if wacc_i <= TG_PIB: wacc_i = TG_PIB + 0.03
    
    # Valor terminal
    fcff_last = fcff_series[-1]
    tv = fcff_last * (1 + TG_PIB) / (wacc_i - TG_PIB) / (1 + wacc_e)**ANOS
    
    eq_val = pv + tv - nd
    if eq_val <= 0: return None, {}
    
    pf = round(eq_val / shares, 2)
    
    details = {
        "wacc_expl":    round(wacc_e*100, 2),
        "wacc_impl":    round(wacc_i*100, 2),
        "ke_expl":      round(ke_e*100, 2),
        "ke_impl":      round(ke_i*100, 2),
        "kd_real":      round(kd*100, 2),
        "beta_levered": round(beta_l, 3),
        "beta_unlevered":round(beta_u, 3),
        "ev_weight":    round(mktcap/(mktcap+nd_pos)*100, 1),
        "dv_weight":    round(nd_pos/(mktcap+nd_pos)*100, 1) if nd_pos else 0,
        "tg_expl":      round(float(v.get("rev_cagr_hist") or TG_SETOR.get(setor,0.045))*100, 2),
        "tg_impl":      round(TG_PIB*100, 2),
        "pv_explicit":  round(pv, 0),
        "pv_terminal":  round(tv, 0),
        "fcff_series":  fcff_series,
        "ebit_method":  v.get("ebit_method","pct_rev"),
        "rev_base":     round(rev_base, 0),
    }
    
    return pf, details

# ── MAIN ─────────────────────────────────────────────────────────
def run():
    results = json.load(open("/opt/shipyard/valuation_results_combined.json"))
    updated = skipped = invalid = bancos = 0
    
    for emp, v in results.items():
        if v.get("deslistado"): continue
        price = float(v.get("price_now") or 0)
        if not price: skipped += 1; continue
        
        pf, details = calc_dcf_full(v)
        if details.get("modelo") == "DDM": bancos += 1
        
        if not pf or pf <= 0: skipped += 1; continue
        
        upside = round((pf/price-1)*100, 2)
        if abs(upside) > 500: invalid += 1; continue
        
        results[emp].update({
            "price_fair":    pf,
            "upside":        upside,
            "wacc":          details.get("wacc_expl", 0),
            "wacc_expl":     details.get("wacc_expl", 0),
            "wacc_impl":     details.get("wacc_impl", 0),
            "tg":            details.get("tg_expl", 4.5),
            "tg_impl":       round(TG_PIB*100, 2),
            "beta":          details.get("beta_levered", v.get("beta",1.0)),
            "beta_unlevered":details.get("beta_unlevered"),
            "wacc_details":  details,
            "recomendacao":  (
                "COMPRA FORTE" if upside > 30  else
                "COMPRA"       if upside > 10  else
                "NEUTRO"       if upside > -10 else
                "VENDA"        if upside > -30 else
                "VENDA FORTE")
        })
        updated += 1
    
    from collections import Counter
    recs = Counter(v.get("recomendacao","—") for v in results.values()
                   if float(v.get("price_fair") or 0) > 0 and not v.get("deslistado"))
    
    print(f"Recalculados: {updated} | DDM: {bancos} | Sem dados: {skipped} | Inválidos: {invalid}")
    print(f"Com valuation: {sum(1 for v in results.values() if float(v.get('price_fair') or 0)>0)}")
    print("\nDistribuição:")
    for k,n in recs.most_common(): print(f"  {k}: {n}")
    
    vals = [(float(v.get("upside") or 0), v.get("ticker","").replace(".SA",""))
            for v in results.values()
            if float(v.get("price_fair") or 0)>0 and not v.get("deslistado")
            and abs(float(v.get("upside") or 0)) <= 300]
    vals.sort(reverse=True)
    print("\nTop 10 COMPRA:")
    for up,tk in vals[:10]: print(f"  {tk:8s} {up:+.1f}%")
    print("\nTop 10 VENDA:")
    for up,tk in vals[-10:]: print(f"  {tk:8s} {up:+.1f}%")
    
    json.dump(results, open("/opt/shipyard/valuation_results_combined.json","w"),
              ensure_ascii=False, indent=2)
    print("\nSalvo!")

if __name__ == "__main__":
    run()
