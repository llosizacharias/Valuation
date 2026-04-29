"""
update_valuations.py — busca dados da ComDinheiro com 1 sessão só
"""
import asyncio, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, "/opt/shipyard")

from config import required_env
CD_USER = required_env("COMDINHEIRO_USER")
CD_PASS = required_env("COMDINHEIRO_PASS")
RF=0.065; ERP=0.055; TAX=0.34; ANOS=10

SETOR_PARAMS = {
    "energia":   {"tg":0.03,"kd":0.095,"beta":0.65},
    "saneamento":{"tg":0.03,"kd":0.095,"beta":0.60},
    "financeiro":{"tg":0.05,"kd":0.13, "beta":0.90},
    "banco":     {"tg":0.05,"kd":0.13, "beta":0.85},
    "tecnologia":{"tg":0.06,"kd":0.14, "beta":1.10},
    "saude":     {"tg":0.05,"kd":0.13, "beta":0.80},
    "construc":  {"tg":0.04,"kd":0.14, "beta":1.10},
    "consumo":   {"tg":0.04,"kd":0.12, "beta":0.90},
    "petroleo":  {"tg":0.03,"kd":0.11, "beta":0.85},
    "minerac":   {"tg":0.03,"kd":0.11, "beta":1.00},
    "agro":      {"tg":0.04,"kd":0.12, "beta":0.85},
    "telecom":   {"tg":0.03,"kd":0.10, "beta":0.70},
    "DEFAULT":   {"tg":0.04,"kd":0.12, "beta":1.00},
}

def get_params(sector):
    s = (sector or "").lower()
    for k,v in SETOR_PARAMS.items():
        if k in s: return v
    return SETOR_PARAMS["DEFAULT"]

def parse_bi(v):
    if not v: return None
    try:
        s = str(v).strip().replace("\xa0"," ").replace("\u00a0"," ")
        if " bi"  in s: return float(s.replace(" bi","").replace(",",".").strip())*1e9
        if " mi"  in s: return float(s.replace(" mi","").replace(",",".").strip())*1e6
        if " tri" in s: return float(s.replace(" tri","").replace(",",".").strip())*1e12
        return float(s.replace(",",".").strip())
    except: return None

def calc_wacc(beta,kd,equity,net_debt):
    ke=RF+beta*ERP; eq=abs(equity or 1e9); nd=abs(net_debt or 0); t=eq+nd
    return ke*(eq/t)+kd*(1-TAX)*(nd/t)

def calc_dcf(ebit,tg,wacc,net_debt,shares):
    if not ebit or not shares or wacc<=tg or shares<=0: return None
    fcf=ebit*(1-TAX)*0.65
    pv=sum(fcf*(1+tg)**i/(1+wacc)**i for i in range(1,ANOS+1))
    tv=fcf*(1+tg)**ANOS*(1+tg)/(wacc-tg)/(1+wacc)**ANOS
    eq=pv+tv-(net_debt or 0)
    return round(eq/shares,2) if eq>0 else None

async def scrape_one(page, ticker):
    """Busca dados de uma empresa na sessão já aberta"""
    try:
        url = f"https://www.comdinheiro.com.br/Fundamentalista2-02553-20251231-01-{ticker}-consolidado-IFRS-comdinheiro-12"
        await page.goto(url, timeout=25000)
        await page.wait_for_load_state('networkidle', timeout=15000)
        await page.wait_for_timeout(1000)

        data = await page.evaluate('''() => {
            const r = {};
            document.querySelectorAll("table tr").forEach(row => {
                const cells = row.querySelectorAll("td,th");
                if (cells.length >= 2) {
                    const k = cells[0].innerText.trim();
                    const v = cells[1].innerText.trim();
                    if (k && v && k.length < 80) r[k] = v;
                }
            });
            return r;
        }''')

        def pf(k): return parse_bi(data.get(k))

        mkt_cap = pf("Valor de Mercado")
        ev      = pf("Enterprise Value (EV)")
        ebitda  = pf("EBITDA")
        ebit    = pf("EBIT")
        div_liq = pf("Dívida Líquida")

        def tof(v):
            try: return float(str(v).replace(",",".").strip()) if v else None
            except: return None

        return {
            "mkt_cap":   mkt_cap,
            "ev":        ev,
            "ebitda":    ebitda,
            "ebit":      ebit,
            "div_liq":   div_liq,
            "ev_ebitda": tof(data.get("EV/EBITDA")),
            "lpa":       tof(data.get("Lucro por Ação (R$)")),
            "beta":      tof(data.get("Beta")),
            "kd":        tof(data.get("Kd (% ao ano)")),
            "roe":       tof(data.get("(LL/RL)x(RL/AT)x(AT/PL)%:")),
            "sector":    data.get("Indústria","") or data.get("Setor",""),
            "margem_liq":tof(data.get("Margem Líquida (LL/RL) em %:")),
            "ok": True
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def main():
    results = json.load(open("/opt/shipyard/valuation_results_combined.json"))
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Login único
        await page.goto("https://www.comdinheiro.com.br/login", timeout=30000)
        await page.wait_for_load_state('networkidle')
        await page.fill('#textUser', CD_USER)
        await page.fill('#textSenha', CD_PASS)
        await page.check('input[name="aceito"]')
        await page.click('button[type="button"]:has-text("LOGIN")')
        await page.wait_for_load_state('networkidle', timeout=15000)
        await page.wait_for_timeout(1000)
        print("Login OK")

        updated = errors = 0
        total = len(results)

        for i, (emp, r) in enumerate(results.items()):
            tk = r.get("ticker","").replace(".SA","")
            if not tk: continue

            print(f"[{i+1}/{total}] {tk}...", end=" ", flush=True)

            f = await scrape_one(page, tk)

            if not f.get("ok"):
                print(f"ERRO: {f.get('error','')[:50]}")
                errors += 1
                continue

            # Atualiza dados de mercado
            results[emp].update({k:v for k,v in f.items() if v is not None and k != "ok"})

            # Calcula valuation
            price  = float(r.get("price_now") or 0)
            ebit   = f.get("ebit")
            mktcap = f.get("mkt_cap")
            divliq = f.get("div_liq") or 0
            equity = r.get("equity") or (mktcap*0.8 if mktcap else None)
            shares = mktcap/price if (mktcap and price>0) else None
            sector = f.get("sector") or r.get("sector","")
            beta   = float(f.get("beta") or r.get("beta") or 1.0)

            if ebit and shares and price>0 and equity:
                params = get_params(sector)
                kd     = params["kd"]
                tg     = params["tg"]
                wacc   = calc_wacc(beta, kd, equity, divliq)
                pf_val = calc_dcf(ebit, tg, wacc, divliq, shares)

                if pf_val and pf_val>0:
                    upside = round((pf_val/price-1)*100,2)
                    if abs(upside) <= 800:
                        results[emp].update({
                            "price_fair":   pf_val,
                            "upside":       upside,
                            "wacc":         round(wacc*100,2),
                            "tg":           round(tg*100,2),
                            "beta":         round(beta,2),
                            "recomendacao": (
                                "COMPRA FORTE" if upside>30  else
                                "COMPRA"       if upside>10  else
                                "NEUTRO"       if upside>-10 else
                                "VENDA"        if upside>-30 else
                                "VENDA FORTE")
                        })
                        updated += 1
                        print(f"pf=R${pf_val:.2f} up={upside:.1f}%")
                    else:
                        print(f"distorcao({upside:.0f}%)")
                else:
                    print("dcf=None")
            else:
                print(f"sem dados(ebit={ebit is not None} sh={shares is not None})")

            # Salva a cada 20 empresas
            if (i+1) % 20 == 0:
                json.dump(results, open("/opt/shipyard/valuation_results_combined.json","w"),
                          ensure_ascii=False, indent=2)
                print(f"  >>> Checkpoint salvo ({i+1} processadas)")

        await browser.close()

    # Salva final
    json.dump(results, open("/opt/shipyard/valuation_results_combined.json","w"),
              ensure_ascii=False, indent=2)
    com_val = sum(1 for v in results.values() if float(v.get("price_fair") or 0)>0)
    print(f"\nFinalizado! Atualizados: {updated} | Erros: {errors}")
    print(f"Total com valuation: {com_val}/{len(results)}")

asyncio.run(main())
