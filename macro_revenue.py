"""macro_revenue.py — Projeta receita via correlação com IPCA e PIB"""
import requests, numpy as np, pandas as pd
import yfinance as yf
from functools import lru_cache

IPCA_FWD = 0.055; PIB_FWD = 0.020
IPCA_LP  = 0.045; PIB_LP  = 0.023

@lru_cache(maxsize=1)
def get_macro_historico():
    # Inclui 2025 com estimativa Focus/BCB
    ipca_fb = {
        2010:0.0591,2011:0.0650,2012:0.0584,2013:0.0591,2014:0.0640,
        2015:0.1067,2016:0.0689,2017:0.0295,2018:0.0375,2019:0.0421,
        2020:0.0452,2021:0.1006,2022:0.0562,2023:0.0462,2024:0.0483,
        2025:0.0510  # estimativa Focus
    }
    pib_fb = {
        2010:0.0754,2011:0.0400,2012:0.0192,2013:0.0303,2014:0.0050,
        2015:-0.0354,2016:-0.0328,2017:0.0115,2018:0.0132,2019:0.0119,
        2020:-0.0396,2021:0.0499,2022:0.0290,2023:0.0293,2024:0.0338,
        2025:0.0220  # estimativa Focus
    }
    try:
        url = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados"
               "?formato=json&dataInicial=01/12/2010&dataFinal=01/12/2024")
        for d in requests.get(url, timeout=8).json():
            ipca_fb[int(d['data'].split('/')[-1])] = float(d['valor'].replace(',','.'))/100
    except: pass
    try:
        url2 = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.7326/dados"
                "?formato=json&dataInicial=01/01/2010&dataFinal=01/01/2024")
        for d in requests.get(url2, timeout=8).json():
            pib_fb[int(d['data'].split('/')[-1])] = float(d['valor'].replace(',','.'))/100
    except: pass
    return ipca_fb, pib_fb


def get_receita_anual(ticker):
    """Reconstrói receita anual a partir de trimestrais (soma 4Q por ano)."""
    try:
        stock = yf.Ticker(ticker)
        qf = stock.quarterly_financials
        if qf is not None and not qf.empty and 'Total Revenue' in qf.index:
            rev_q = qf.loc['Total Revenue'].dropna()
            rev_q.index = pd.to_datetime(rev_q.index)
            rev_q = rev_q.sort_index()
            rev_anual = {}
            for ano in rev_q.index.year.unique():
                mask = rev_q.index.year == ano
                if mask.sum() >= 4:
                    rev_anual[int(ano)] = float(rev_q[mask].sum())
                elif mask.sum() >= 2:
                    # Anualiza se tiver pelo menos 2 trimestres
                    rev_anual[int(ano)] = float(rev_q[mask].sum() * 4 / mask.sum())
            if len(rev_anual) >= 3:
                return rev_anual
        # Fallback anual
        fin = stock.financials
        if fin is not None and not fin.empty and 'Total Revenue' in fin.index:
            rev = fin.loc['Total Revenue'].dropna()
            return {int(pd.Timestamp(c).year): float(v) for c,v in rev.items() if v > 0}
    except: pass
    return {}


def calc_macro_correlation(ticker):
    ipca_h, pib_h = get_macro_historico()
    rev_h = get_receita_anual(ticker)
    if len(rev_h) < 3: return None

    anos = sorted(rev_h.keys())
    rg, ip, pb, av = [], [], [], []
    for i in range(1, len(anos)):
        a0, a1 = anos[i-1], anos[i]
        if a1 not in ipca_h or a1 not in pib_h: continue
        if rev_h[a0] <= 0: continue
        g = rev_h[a1]/rev_h[a0] - 1
        if abs(g) > 1.5: continue
        av.append(a1); rg.append(g)
        ip.append(ipca_h[a1]); pb.append(pib_h[a1])

    # Mínimo 2 observações válidas
    if len(rg) < 2: return None

    rg=np.array(rg); ip=np.array(ip); pb=np.array(pb); ms=ip+pb

    def corr(x,y):
        if len(x)<2 or np.std(x)==0 or np.std(y)==0: return 0.0
        return float(np.corrcoef(x,y)[0,1])

    ci=corr(rg,ip); cp=corr(rg,pb); cm=corr(rg,ms)

    candidatos=[]
    thr = 0.30 if len(rg) >= 4 else 0.50  # threshold maior com menos dados
    if abs(ci)>=thr: candidatos.append(('ipca',  float(np.std(rg-ip)),  ci, float(np.median(rg-ip))))
    if abs(cp)>=thr: candidatos.append(('pib',   float(np.std(rg-pb)),  cp, float(np.median(rg-pb))))
    if abs(cm)>=thr: candidatos.append(('macro', float(np.std(rg-ms)),  cm, float(np.median(rg-ms))))

    if candidatos:
        metodo,std_b,corr_b,spread = min(candidatos,key=lambda x:x[1])
    else:
        metodo='hist_median'; std_b=float(np.std(rg))
        corr_b=0.0; spread=float(np.median(rg))

    sc = float(np.clip(spread,-0.04,0.12))

    if metodo=='ipca':   cp_=IPCA_FWD+sc; cl_=IPCA_LP+sc*0.6
    elif metodo=='pib':  cp_=PIB_FWD+sc;  cl_=PIB_LP+sc*0.6
    elif metodo=='macro':cp_=IPCA_FWD+PIB_FWD+sc; cl_=IPCA_LP+PIB_LP+sc*0.6
    else: cp_=np.clip(spread,0.02,0.12); cl_=np.clip(spread*0.6,0.02,0.08)

    return {
        'metodo':      metodo,
        'corr_ipca':   round(ci,3),
        'corr_pib':    round(cp,3),
        'corr_macro':  round(cm,3),
        'std_spread':  round(std_b,4),
        'spread_hist': round(spread,4),
        'cagr_proj':   round(float(np.clip(cp_,0.02,0.18)),4),
        'cagr_lp':     round(float(np.clip(cl_,0.02,0.10)),4),
        'n_obs':       len(rg),
    }


def update_macro_rev(ticker, v_dict):
    res = calc_macro_correlation(ticker)
    if not res: return False
    v_dict['rev_macro_metodo']  = res['metodo']
    v_dict['rev_macro_corr_ip'] = res['corr_ipca']
    v_dict['rev_macro_corr_pb'] = res['corr_pib']
    v_dict['rev_cagr_proj']     = res['cagr_proj']
    v_dict['rev_cagr_lp']       = res['cagr_lp']
    v_dict['rev_spread_hist']   = res['spread_hist']
    v_dict['rev_n_obs']         = res['n_obs']
    return True


if __name__ == '__main__':
    ipca_h,pib_h = get_macro_historico()
    print(f"Macro OK: IPCA_2024={ipca_h.get(2024,0)*100:.1f}% IPCA_2025={ipca_h.get(2025,0)*100:.1f}%\n")
    testes=['WEGE3.SA','PETR4.SA','VALE3.SA','EQTL3.SA','KLBN11.SA','SUZB3.SA','ALOS3.SA','ITUB4.SA','HAPV3.SA']
    print(f"{'Ticker':<12}{'Método':<13}{'r_IP':>6}{'r_PB':>6}{'Spread':>7}{'CAGR_p':>7}{'CAGR_lp':>8}{'n':>3}")
    print("-"*64)
    for tk in testes:
        r = calc_macro_correlation(tk)
        rv = get_receita_anual(tk)
        if r:
            print(f"{tk:<12}{r['metodo']:<13}{r['corr_ipca']:>+5.2f}{r['corr_pib']:>+6.2f}"
                  f"{r['spread_hist']:>+6.1%}{r['cagr_proj']:>6.1%}{r['cagr_lp']:>7.1%}{r['n_obs']:>3}")
        else:
            print(f"{tk:<12}SEM DADOS  (anos={sorted(rv.keys())})")
