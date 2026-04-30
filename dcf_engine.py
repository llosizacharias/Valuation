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

# ── D-006: TV com ROIC explícito (Damodaran cap. 12) ──────────────
# g perpétuo por setor (nominal, ≤ PIB nominal Brasil ~7%)
G_SETOR_PERP = {
    "energia":0.045,"saneamento":0.040,"financeiro":0.055,"banco":0.055,
    "tecnologia":0.070,"saude":0.060,"construc":0.050,"consumo":0.060,
    "petroleo":0.035,"minerac":0.035,"agro":0.050,"telecom":0.045,
    "varejo":0.060,"DEFAULT":0.050,
}
# Spread perpétuo ROIC* sobre WACC* (decay para WACC + spread)
SPREAD_SETOR_PERP = {
    "energia":0.010,"saneamento":0.010,"financeiro":0.020,"banco":0.020,
    "tecnologia":0.030,"saude":0.030,"construc":0.020,"consumo":0.020,
    "petroleo":0.000,"minerac":0.000,"agro":0.010,"telecom":0.010,
    "varejo":0.020,"DEFAULT":0.020,
}
# Estrutura de capital perpétua (D/V) por setor — para WACC perpétuo
DV_SETOR_PERP = {
    "energia":0.40,"saneamento":0.45,"financeiro":0.20,"banco":0.10,
    "tecnologia":0.10,"saude":0.20,"construc":0.40,"consumo":0.25,
    "petroleo":0.30,"minerac":0.25,"agro":0.30,"telecom":0.40,
    "varejo":0.30,"DEFAULT":0.25,
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

# Tickers reconhecidos como banco/financeira independente do campo sector
BANK_TICKERS = {
    "ITUB4", "ITUB3", "ITSA4", "ITSA3",
    "BBDC4", "BBDC3", "BBAS3", "SANB11", "SANB3", "SANB4",
    "BPAC11", "BPAC3", "BPAC5",
    "BRSR6", "BRSR3", "BRSR5",
    "ABCB4", "BMGB4", "BIDI4", "BIDI11",
    "BBSE3", "PSSA3", "IRBR3", "BMOB3", "WIZS3",
    "B3SA3",
}

def _is_banco_ticker(ticker_raw):
    """Verifica se ticker (com ou sem .SA) bate com lista conhecida."""
    if not ticker_raw:
        return False
    tk = ticker_raw.replace(".SA", "").upper()
    return tk in BANK_TICKERS


def _is_banco(sector_or_v):
    """
    Aceita string (sector) OU dict (v completo).
    Se receber dict, checa sector + ticker.
    """
    if isinstance(sector_or_v, dict):
        sector = (sector_or_v.get("sector") or sector_or_v.get("setor") or "").lower()
        if any(b in sector for b in BANCOS):
            return True
        return _is_banco_ticker(sector_or_v.get("ticker"))
    return any(b in (sector_or_v or "").lower() for b in BANCOS)

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
    Reinvestimento líquido em capital fixo (Damodaran cap. 10/12):
        CapEx_liquido = CapEx - D&A_total

    Damodaran usa D&A TOTAL (não incremental). A definição de FCFF é:
        FCFF = NOPAT - (CapEx - D&A) - ΔWC
    onde (CapEx - D&A) é o reinvestimento líquido em ativos fixos.

    Empresas em fase de colheita (D&A > CapEx) têm reinvestimento
    NEGATIVO — soma de volta ao FCFF. Isso é correto e desejado.
    """
    setor = _sk(v.get("sector") or v.get("setor", ""))

    # CapEx como % receita
    capex_pct = v.get("capex_pct_rev") or _get_default(CAPEX_DEFAULT, setor)
    capex_pct = max(0.01, min(float(capex_pct), 0.35))
    capex = receita_proj * capex_pct

    # D&A TOTAL como % receita (Damodaran-style)
    da_pct = v.get("da_pct_rev")
    if da_pct is not None:
        da_pct = max(0.0, min(float(da_pct), 0.30))
        da_total = receita_proj * da_pct
    else:
        # Fallback: estima D&A em 70% do CapEx (média histórica empresas BR maduras)
        da_total = capex * 0.70

    # Reinvestimento líquido = CapEx - D&A (pode ser negativo!)
    return capex - da_total


# ── DELTA CAPITAL DE GIRO ─────────────────────────────────────────
def proj_dcg(v, receita_proj, receita_ant):
    """
    Variação de capital de giro (ΔWC).
    ΔWC = ΔRev × dcg_pct_drev, com CAP de ±15% (Damodaran sanity).

    Empresas normais têm WC marginal entre 0% e 15% da receita.
    Valores fora disso (>15% ou <-15%) são lixo de coleta —
    geralmente histórico curto com outlier amplificado.
    """
    if not receita_ant or receita_ant <= 0:
        return 0
    delta_rev = receita_proj - receita_ant
    dcg_pct = v.get("dcg_pct_drev")
    if dcg_pct is None:
        return 0
    dcg_pct = float(dcg_pct)
    # Cap em ±15% — sanity Damodaran
    dcg_pct = max(-0.15, min(dcg_pct, 0.15))
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
    if not lpa: return None, {"erro": "lpa ausente para banco — preciso de LPA do yfinance"}
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

# ── D-006: WACC perpétuo (β=1, estrutura setorial, RF_BASE) ───────
def calc_wacc_perpetuo(setor, rf=None, erp=None, tax=None):
    """
    WACC na perpetuidade: β=1.0, estrutura de capital setorial,
    Kd com spread reduzido (empresa madura), RF=RF_BASE (8.5%, equilíbrio LP).
    Damodaran (Investment Valuation, cap. 12):
    'beta should be close to one — between 0.8 and 1.2'
    """
    rf = RF_BASE if rf is None else rf
    erp = ERP if erp is None else erp
    tax = TAX if tax is None else tax

    beta_perp = 1.0
    ke_perp = rf + beta_perp * erp

    dv = DV_SETOR_PERP.get(setor, DV_SETOR_PERP["DEFAULT"])
    ev = 1.0 - dv

    # Kd perpétuo: spread setorial reduzido (empresa madura)
    kd_spread_perp = {
        "banco":0.015,"financeiro":0.015,
        "energia":0.020,"saneamento":0.020,"telecom":0.020,
        "DEFAULT":0.025,
    }
    kd_perp = rf + kd_spread_perp.get(setor, kd_spread_perp["DEFAULT"])

    wacc_p = ev * ke_perp + dv * kd_perp * (1 - tax)
    return wacc_p, ke_perp, kd_perp


# ── D-006: Terminal Value com ROIC explícito (Damodaran cap. 12) ──
def calc_tv_v2(v, ebit_n, wacc_e, anos):
    """
    Terminal Value com fórmula:
        TV_N = NOPAT_{N+1} × (1 - g/ROIC*) / (WACC* - g)

    Decisões (D-006):
    1. NOPAT_{N+1} = EBIT_N × (1+g) × (1-t)  — não FCFF_N × (1+g)
       (FCFF do ano N carrega reinvestimento do ano N, inadequado p/ perpetuidade)
    2. WACC* via calc_wacc_perpetuo (β=1, estrutura setorial, RF_BASE)
    3. g setorial, limitado por RF_BASE
    4. ROIC* = min(ROIC_atual, WACC* + spread_setor); spreads 0-3pp
    5. Se ROIC_atual < WACC*: ROIC* = WACC* (sem excess return),
       reinv_rate = g/WACC*

    Retorna: (tv_pv, details_dict)
    """
    setor = _sk(v.get("sector") or v.get("setor", ""))

    # 1. WACC perpétuo
    wacc_p, ke_p, kd_p = calc_wacc_perpetuo(setor)

    # 2. g perpétuo (limitado por RF_BASE)
    g = min(G_SETOR_PERP.get(setor, G_SETOR_PERP["DEFAULT"]), RF_BASE * 0.95)

    # 3. ROIC perpétuo (com fade)
    roic_atual = v.get("roic")
    try:
        roic_atual = float(roic_atual) if roic_atual is not None else None
    except (TypeError, ValueError):
        roic_atual = None

    spread = SPREAD_SETOR_PERP.get(setor, SPREAD_SETOR_PERP["DEFAULT"])

    # Fix #3: empresas em distress (ROIC < 0) — não aplicar TV padrão
    if roic_atual is not None and roic_atual < 0:
        return None, {
            "erro": f"distress: ROIC={roic_atual:.2%} < 0 — requer tratamento especial (Damodaran cap. 22)",
            "tv_case": "distress_roic_negativo",
        }

    if roic_atual is None or roic_atual < wacc_p:
        # ROIC* = WACC*: TV = NOPAT/(WACC-g) puro (sem excess return)
        roic_p = wacc_p
        reinv_rate = g / wacc_p
        case = "no_excess" if roic_atual is not None else "no_roic_data"
    else:
        roic_p = min(roic_atual, wacc_p + spread)
        reinv_rate = g / roic_p
        case = "fade"

    # 4. NOPAT_{N+1}
    nopat_n_plus_1 = ebit_n * (1 + g) * (1 - TAX)

    # 5. TV em t=N
    if wacc_p <= g:
        return None, {"erro": f"wacc_p ({wacc_p:.2%}) <= g ({g:.2%})"}
    tv_n = nopat_n_plus_1 * (1 - reinv_rate) / (wacc_p - g)

    # 6. PV em t=0 (descontado a wacc_explicito)
    if wacc_e <= -1.0:
        return None, {"erro": "wacc_e invalido"}
    tv_pv = tv_n / (1 + wacc_e) ** anos

    return tv_pv, {
        "tv_method":     "damodaran_roic_v2",
        "wacc_perpetuo": round(wacc_p * 100, 2),
        "ke_perpetuo":   round(ke_p * 100, 2),
        "kd_perpetuo":   round(kd_p * 100, 2),
        "g_perpetuo":    round(g * 100, 2),
        "roic_atual":    round(roic_atual * 100, 2) if roic_atual is not None else None,
        "roic_perpetuo": round(roic_p * 100, 2),
        "reinv_rate":    round(reinv_rate * 100, 2),
        "ebit_n":        round(ebit_n, 0),
        "nopat_n1":      round(nopat_n_plus_1, 0),
        "tv_in_year_n":  round(tv_n, 0),
        "tv_pv":         round(tv_pv, 0),
        "case":          case,
        "tv_case":       case,
    }


def calc_dcf_full(v):
    price  = float(v.get("price_now") or 0)
    mktcap = v.get("mkt_cap")
    nd     = float(v.get("div_liq") or v.get("net_debt") or 0)
    sector = v.get("sector") or v.get("setor","") or ""
    setor  = _sk(sector)
    
    if not price or not mktcap: return None, {"erro": "price ou mktcap zerado"}
    shares = mktcap / price
    if shares <= 0: return None, {"erro": "shares <= 0"}
    
    if _is_banco(v):
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
    if not rev_base: return None, {"erro": "revenue_last zerado"}
    
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
    
    # ── D-006: Terminal value via Damodaran ROIC explícito ──
    # EBIT do ano N: re-projeção (mesma metodologia de proj_ebit) ou
    # extrapolação a partir do FCFF/margem — preferimos recalcular EBIT_N puro
    receita_n = receita_ant  # após o loop, receita_ant = receita do ano N
    ebit_n = proj_ebit(v, receita_n)
    if ebit_n is None or ebit_n <= 0:
        # Fallback: estima EBIT_N pela margem média × receita_N
        margin = float(v.get("ebit_margin_hist") or 0.15)
        ebit_n = receita_n * margin

    tv, tv_details = calc_tv_v2(v, ebit_n, wacc_e, ANOS)
    if tv is None:
        return None, {"erro_tv": tv_details.get("erro", "tv None")}

    # Compatibilidade backward: mantém wacc_i e fcff_last como referência
    wacc_i = tv_details["wacc_perpetuo"] / 100
    fcff_last = fcff_series[-1] if fcff_series else 0
    
    eq_val = pv + tv - nd
    if eq_val <= 0: return None, {"erro": f"eq_val negativo: pv={pv:.0f} tv={tv:.0f} nd={nd:.0f}"}
    
    pf = round(eq_val / shares, 2)
    
    details = {
        "wacc_expl":    round(wacc_e*100, 2),
        "wacc_impl":    round(wacc_i*100, 2),
        "ke_expl":      round(ke_e*100, 2),
        "ke_impl":      round(tv_details["ke_perpetuo"], 2),
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
        # D-006: detalhes do TV v2
        "tv_v2":        tv_details,
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
