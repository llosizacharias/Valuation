"""
expand_coverage.py — Adiciona 139 empresas Tier 1 ao Shipyard
Fonte: Lista B3 (NM/N1/N2) + ComDinheiro API + brapi preços
"""
import json, sys, time, requests
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, "/opt/shipyard")
import brapi_client as brapi

CD_USER = "vela.capital"
CD_PASS = "Vela.capital1!"
API_URL = "https://api.comdinheiro.com.br/v1/ep1/import-data"

# ── Tier 1 faltando — base B3 + sufixo correto ────────────────────
TIER1 = {
    # NM
    "AALR3":"AALR","AERI3":"AERI","AGRO3":"AGRO","AGXY3":"AGXY",
    "ALLD3":"ALLD","ALOS3":"ALOS","ALPK3":"ALPK","AMAR3":"AMAR",
    "AMER3":"AMER","ANIM3":"ANIM","ARML3":"ARML","ASAI3":"ASAI",
    "AUAU3":"AUAU","AVLL3":"AVLL","AZZA3":"AZZA","B3SA3":"B3SA",
    "BBAS3":"BBAS","BBSE3":"BBSE","BEEF3":"BEEF","BHIA3":"BHIA",
    "BLAU3":"BLAU","BMOB3":"BMOB","BRAV3":"BRAV","BRST3":"BRST",
    "CAML3":"CAML","CASH3":"CASH","CCTY3":"CCTY","CEAB3":"CEAB",
    "CURY3":"CURY","CVCB3":"CVCB","CXSE3":"CXSE","DESK3":"DESK",
    "DMVF3":"DMVF","DOTZ3":"DOTZ","EMBJ3":"EMBJ","ENEV3":"ENEV",
    "ESPA3":"ESPA","ETER3":"ETER","FIQE3":"FIQE","FRIO3":"FRIO",
    "GFSA3":"GFSA","GGPS3":"GGPS","GMAT3":"GMAT","GRND3":"GRND",
    "HAPV3":"HAPV","HBOR3":"HBOR","HBRE3":"HBRE","HYPE3":"HYPE",
    "IRBR3":"IRBR","JALL3":"JALL","JSLG3":"JSLG","KEPL3":"KEPL",
    "KLAS3":"KLAS","LAVV3":"LAVV","LEVE3":"LEVE","LJQQ3":"LJQQ",
    "LOGG3":"LOGG","LPSB3":"LPSB","LWSA3":"LWSA","MATD3":"MATD",
    "MBRF3":"MBRF","MDNE3":"MDNE","MEAL3":"MEAL","MELK3":"MELK",
    "MLAS3":"MLAS","MOTV3":"MOTV","MTRE3":"MTRE","MYPK3":"MYPK",
    "NATU3":"NATU","NEOE3":"NEOE","ONCO3":"ONCO","ORVR3":"ORVR",
    "PCAR3":"PCAR","PLPL3":"PLPL","PMAM3":"PMAM","PRNR3":"PRNR",
    "PSSA3":"PSSA","PTBL3":"PTBL","QUAL3":"QUAL","RANI3":"RANI",
    "RDOR3":"RDOR","RECV3":"RECV","RENT3":"RENT","RIAA3":"RIAA",
    "RSID3":"RSID","SANB11":"SANB","SBFG3":"SBFG","SBSP3":"SBSP",
    "SCAR3":"SCAR","SEER3":"SEER","SIMH3":"SIMH","SMFT3":"SMFT",
    "SMTO3":"SMTO","SOJA3":"SOJA","SYNE3":"SYNE","TCSA3":"TCSA",
    "TECN3":"TECN","TGMA3":"TGMA","TIMS3":"TIMS","TOTS3":"TOTS",
    "TRAD3":"TRAD","TRIS3":"TRIS","TTEN3":"TTEN","UGPA3":"UGPA",
    "VAMO3":"VAMO","VITT3":"VITT","VIVA3":"VIVA","VIVT3":"VIVT",
    "VLID3":"VLID","VSTE3":"VSTE","VTRU3":"VTRU","VULC3":"VULC",
    "VVEO3":"VVEO","WIZC3":"WIZC","B1003":"B100",
    # N1
    "ALPA4":"ALPA","BBDC4":"BBDC","BMEB4":"BMEB","BRAP4":"BRAP",
    "BRSR6":"BRSR","EUCA4":"EUCA","FESA4":"FESA","FRAS3":"FRAS",
    "GOAU4":"GOAU","ITSA4":"ITSA","ITUB4":"ITUB","UNIP3":"UNIP",
    # N2
    "ABCB4":"ABCB","BPAC11":"BPAC","BRBI3":"BRBI","CLSC6":"CLSC",
    "CMIN3":"CMIN","PINE4":"PINE","POMO4":"POMO","RAIZ4":"RAIZ",
    "SALT3":"SALT","SAPR4":"SAPR","TASA4":"TASA","TFCO4":"TFCO",
}

SEGMENTO = {
    "AALR3":"NM","AERI3":"NM","AGRO3":"NM","AGXY3":"NM","ALLD3":"NM",
    "ALOS3":"NM","ALPK3":"NM","AMAR3":"NM","AMER3":"NM","ANIM3":"NM",
    "ARML3":"NM","ASAI3":"NM","AUAU3":"NM","AVLL3":"NM","AZZA3":"NM",
    "B3SA3":"NM","BBAS3":"NM","BBSE3":"NM","BEEF3":"NM","BHIA3":"NM",
    "BLAU3":"NM","BMOB3":"NM","BRAV3":"NM","BRST3":"NM","CAML3":"NM",
    "CASH3":"NM","CCTY3":"NM","CEAB3":"NM","CURY3":"NM","CVCB3":"NM",
    "CXSE3":"NM","DESK3":"NM","DMVF3":"NM","DOTZ3":"NM","EMBJ3":"NM",
    "ENEV3":"NM","ESPA3":"NM","ETER3":"NM","FIQE3":"NM","FRIO3":"NM",
    "GFSA3":"NM","GGPS3":"NM","GMAT3":"NM","GRND3":"NM","HAPV3":"NM",
    "HBOR3":"NM","HBRE3":"NM","HYPE3":"NM","IRBR3":"NM","JALL3":"NM",
    "JSLG3":"NM","KEPL3":"NM","KLAS3":"NM","LAVV3":"NM","LEVE3":"NM",
    "LJQQ3":"NM","LOGG3":"NM","LPSB3":"NM","LWSA3":"NM","MATD3":"NM",
    "MBRF3":"NM","MDNE3":"NM","MEAL3":"NM","MELK3":"NM","MLAS3":"NM",
    "MOTV3":"NM","MTRE3":"NM","MYPK3":"NM","NATU3":"NM","NEOE3":"NM",
    "ONCO3":"NM","ORVR3":"NM","PCAR3":"NM","PLPL3":"NM","PMAM3":"NM",
    "PRNR3":"NM","PSSA3":"NM","PTBL3":"NM","QUAL3":"NM","RANI3":"NM",
    "RDOR3":"NM","RECV3":"NM","RENT3":"NM","RIAA3":"NM","RSID3":"NM",
    "SANB11":"NM","SBFG3":"NM","SBSP3":"NM","SCAR3":"NM","SEER3":"NM",
    "SIMH3":"NM","SMFT3":"NM","SMTO3":"NM","SOJA3":"NM","SYNE3":"NM",
    "TCSA3":"NM","TECN3":"NM","TGMA3":"NM","TIMS3":"NM","TOTS3":"NM",
    "TRAD3":"NM","TRIS3":"NM","TTEN3":"NM","UGPA3":"NM","VAMO3":"NM",
    "VITT3":"NM","VIVA3":"NM","VIVT3":"NM","VLID3":"NM","VSTE3":"NM",
    "VTRU3":"NM","VULC3":"NM","VVEO3":"NM","WIZC3":"NM","B1003":"NM",
    "ALPA4":"N1","BBDC4":"N1","BMEB4":"N1","BRAP4":"N1","BRSR6":"N1",
    "EUCA4":"N1","FESA4":"N1","FRAS3":"N1","GOAU4":"N1","ITSA4":"N1",
    "ITUB4":"N1","UNIP3":"N1",
    "ABCB4":"N2","BPAC11":"N2","BRBI3":"N2","CLSC6":"N2","CMIN3":"N2",
    "PINE4":"N2","POMO4":"N2","RAIZ4":"N2","SALT3":"N2","SAPR4":"N2",
    "TASA4":"N2","TFCO4":"N2",
}

def cd_request(url_consulta, timeout=30):
    url_enc = quote(url_consulta + "&format=json3", safe="=&?/+")
    payload = f"username={CD_USER}&password={CD_PASS}&URL={url_enc}"
    r = requests.post(API_URL, data=payload,
                      headers={"Content-Type":"application/x-www-form-urlencoded"},
                      timeout=timeout)
    r.raise_for_status()
    return r.json()

def parse_cd(data):
    try:
        tab  = list(data.get("tables",{}).values())[0]
        lin0 = tab.get("lin0",{})
        cols = [lin0[k] for k in sorted(lin0, key=lambda x: int(x.replace("col","")))]
        rows, i = [], 1
        while f"lin{i}" in tab:
            lin = tab[f"lin{i}"]
            rows.append({cols[j]: lin.get(f"col{j}") for j in range(len(cols))})
            i += 1
        import pandas as pd
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except:
        return None

def to_f(v):
    if not v: return None
    try: return float(str(v).replace(",",".").strip())
    except: return None

def get_financials(ticker_sa):
    """Busca BP+DRE via ComDinheiro BalancosSinteticos001"""
    tk = ticker_sa.replace(".SA","")
    try:
        url = (f"BalancosSinteticos001.php?&an_inicio=2022&an_fim=2024"
               f"&IT_CODIGO={tk}&FORMATO=SIMPLES")
        data = cd_request(url)
        df = parse_cd(data)
        if df is None or df.empty:
            return {}
        
        col0 = df.columns[0]
        def row_val(label):
            mask = df[col0].astype(str).str.strip() == label
            if not mask.any(): return None
            row = df[mask].iloc[0]
            for c in df.columns[1:]:
                v = to_f(row.get(c))
                if v is not None and v != 0: return v
            return None
        
        receita  = row_val("Receita Líquida")
        ebit     = row_val("EBIT")
        ebitda   = row_val("EBITDA")
        ll       = row_val("Lucro Líquido")
        div_liq  = row_val("Dívida Líquida")
        pl       = row_val("Patrimônio Líquido")
        at       = row_val("Ativo Total")
        
        return {
            "revenue_last": receita,
            "ebit_last":    ebit,
            "ebitda_last":  ebitda,
            "net_income":   ll,
            "net_debt":     div_liq,
            "equity":       pl,
            "total_assets": at,
            "ebit_margin":  (ebit/receita*100) if ebit and receita else None,
            "roe":          (ll/pl*100) if ll and pl else None,
        }
    except Exception as e:
        return {"cd_error": str(e)}

# ── MAIN ──────────────────────────────────────────────────────────
results = json.load(open("/opt/shipyard/valuation_results_combined.json"))
existing = set(v.get("ticker","") for v in results.values())

print(f"Empresas existentes: {len(results)}")
print(f"Para adicionar: {len(TIER1)}")
print(f"Já existem: {sum(1 for tk in TIER1 if tk+'.SA' in existing)}")

added = 0
errors = 0

for ticker, base in TIER1.items():
    tk_sa = ticker + ".SA"
    if tk_sa in existing:
        continue
    
    print(f"  Processando {ticker}...", end=" ", flush=True)
    
    # Preço via brapi
    price = None
    try:
        bp = brapi.get_quote([ticker])
        price = bp.get(ticker, {}).get("price")
        if not price:
            # tenta yfinance
            import yfinance as yf
            hist = yf.download(tk_sa, period="5d", auto_adjust=True, progress=False)
            if not hist.empty:
                price = float(hist["Close"].dropna().iloc[-1])
    except: pass
    
    # Financials via ComDinheiro
    fins = get_financials(tk_sa)
    time.sleep(0.3)  # rate limit
    
    # Monta entrada no results
    entry = {
        "ticker":          tk_sa,
        "name":            base,
        "sector":          "",
        "price_now":       price or 0,
        "price_fair":      0,
        "upside":          0,
        "recomendacao":    "NEUTRO",
        "segmento_b3":     SEGMENTO.get(ticker, ""),
        "wacc":            0.12,
        "tg":              0.04,
        "beta":            1.0,
        "revenue_last":    fins.get("revenue_last"),
        "ebit_last":       fins.get("ebit_last"),
        "ebitda_last":     fins.get("ebitda_last"),
        "net_income":      fins.get("net_income"),
        "net_debt":        fins.get("net_debt"),
        "equity":          fins.get("equity"),
        "ebit_margin":     fins.get("ebit_margin"),
        "roe":             fins.get("roe"),
        "tier":            1,
        "fonte":           "B3+ComDinheiro",
    }
    
    # Nome real via brapi se disponível
    try:
        bp2 = brapi.get_quote([ticker])
        if bp2.get(ticker,{}).get("name"):
            entry["name"] = bp2[ticker]["name"]
    except: pass
    
    key = entry["name"] or ticker
    results[key] = entry
    added += 1
    
    status = f"R${price:.2f}" if price else "sem preco"
    fins_ok = "fins OK" if fins.get("revenue_last") else "sem fins"
    print(f"{status} | {fins_ok}")

print(f"\nTotal adicionadas: {added}")
print(f"Total final: {len(results)}")

json.dump(results, open("/opt/shipyard/valuation_results_combined.json","w"),
          ensure_ascii=False, indent=2)
print("JSON salvo!")
