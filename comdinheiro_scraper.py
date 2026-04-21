"""
comdinheiro_scraper.py — Shipyard | Vela Capital
Scraping autenticado da ComDinheiro via Playwright
Dados: Fundamentalista, Acionistas, Balanços, Proventos
"""
import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright

CD_USER = os.getenv("COMDINHEIRO_USER", "vela.capital")
CD_PASS = os.getenv("COMDINHEIRO_PASS", "Vela.capital1!")
CACHE_DIR = Path("/opt/shipyard/data/cd_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Login singleton ────────────────────────────────────────────────
_browser = None
_page    = None

async def _get_page():
    global _browser, _page
    p = await async_playwright().start()
    _browser = await p.chromium.launch(headless=True)
    _page = await _browser.new_page()
    await _page.goto("https://www.comdinheiro.com.br/login", timeout=30000)
    await _page.wait_for_load_state('networkidle')
    await _page.fill('#textUser', CD_USER)
    await _page.fill('#textSenha', CD_PASS)
    await _page.check('input[name="aceito"]')
    await _page.click('button[type="button"]:has-text("LOGIN")')
    await _page.wait_for_load_state('networkidle', timeout=15000)
    await _page.wait_for_timeout(1500)
    return _page

async def _fetch(url, wait=2000):
    page = await _get_page()
    await page.goto(url, timeout=30000)
    await page.wait_for_load_state('networkidle', timeout=20000)
    await page.wait_for_timeout(wait)
    return page

# ── 1. ACIONISTAS ─────────────────────────────────────────────────
async def get_acionistas(ticker: str) -> dict:
    cache_file = CACHE_DIR / f"acionistas_{ticker}.json"
    if cache_file.exists():
        import time
        if time.time() - cache_file.stat().st_mtime < 86400:  # cache 24h
            return json.loads(cache_file.read_text())
    
    try:
        url = f"https://www.comdinheiro.com.br/PrincipaisAcionistas001-{ticker}-0-comdinheiro-89990101-0"
        page = await _fetch(url)
        
        data = await page.evaluate('''() => {
            const tables = [];
            document.querySelectorAll('table').forEach(t => {
                const rows = [];
                t.querySelectorAll('tr').forEach(row => {
                    const cells = Array.from(row.querySelectorAll('td,th'))
                        .map(c => c.innerText.trim());
                    if (cells.some(c => c)) rows.push(cells);
                });
                if (rows.length > 1) tables.push(rows);
            });
            return tables;
        }''')
        
        result = {"ticker": ticker, "acionistas": [], "data_posicao": "", "raw_tables": data}
        
        if data and len(data) > 0:
            rows = data[0]
            header = rows[0] if rows else []
            for row in rows[1:]:
                if len(row) >= 6 and row[0].isdigit():
                    result["acionistas"].append({
                        "rank":      row[0],
                        "nome":      row[1],
                        "pessoa":    row[3] if len(row) > 3 else "",
                        "pais":      row[4] if len(row) > 4 else "",
                        "controle":  row[5] if len(row) > 5 else "",
                        "quant_on":  row[6] if len(row) > 6 else "",
                        "pct_on":    row[7] if len(row) > 7 else "",
                        "quant_pn":  row[8] if len(row) > 8 else "",
                        "pct_pn":    row[9] if len(row) > 9 else "",
                        "pct_total": row[10] if len(row) > 10 else "",
                    })
            # Data da posição
            for row in rows:
                if row and "Posição acionária em" in str(row[0]):
                    result["data_posicao"] = row[0]
        
        cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception as e:
        return {"ticker": ticker, "acionistas": [], "error": str(e)}

# ── 2. FUNDAMENTALISTA ────────────────────────────────────────────
async def get_fundamentalista(ticker: str) -> dict:
    cache_file = CACHE_DIR / f"fund_{ticker}.json"
    if cache_file.exists():
        import time
        if time.time() - cache_file.stat().st_mtime < 3600:  # cache 1h
            return json.loads(cache_file.read_text())
    
    try:
        url = f"https://www.comdinheiro.com.br/Fundamentalista2-02553-20251231-01-{ticker}-consolidado-IFRS-comdinheiro-12"
        page = await _fetch(url)
        
        data = await page.evaluate('''() => {
            const result = {};
            document.querySelectorAll('table tr').forEach(row => {
                const cells = row.querySelectorAll('td, th');
                if (cells.length >= 2) {
                    const key = cells[0].innerText.trim();
                    const val = cells[1].innerText.trim();
                    if (key && val && key.length < 80) result[key] = val;
                }
            });
            return result;
        }''')
        
        # Normaliza valores
        def parse_val(v):
            if not v: return None
            v = v.replace(' bi','e9').replace(' mi','e6').replace(' tri','e12')
            v = v.replace('.','').replace(',','.').replace('%','').strip()
            try: return float(v)
            except: return v
        
        result = {
            "ticker": ticker,
            "raw": data,
            "mkt_cap":    parse_val(data.get("Valor de Mercado")),
            "ev":         parse_val(data.get("Enterprise Value (EV)")),
            "ev_ebitda":  parse_val(data.get("EV/EBITDA")),
            "ev_ebit":    parse_val(data.get("EV/EBIT")),
            "psr":        parse_val(data.get("Price Sales Ratio (PSR)")),
            "ebitda":     parse_val(data.get("EBITDA")),
            "ebit":       parse_val(data.get("EBIT")),
            "beta":       parse_val(data.get("Beta")),
            "kd":         parse_val(data.get("Kd (% ao ano)")),
            "lpa":        parse_val(data.get("Lucro por Ação (R$)")),
            "dpa":        parse_val(data.get("Provento por Ação")),
            "payout":     parse_val(data.get("Índice de Payout (%)")),
            "margem_liq": parse_val(data.get("Margem Líquida (LL/RL) em %:")),
            "roe":        parse_val(data.get("(LL/RL)x(RL/AT)x(AT/PL)%:")),
            "div_bruta":  parse_val(data.get("Dívida Bruta")),
            "div_liq":    parse_val(data.get("Dívida Líquida")),
            "fcf_op":     parse_val(data.get("Fluxo Cx das Operações")),
            "cvm_code":   data.get("Código CVM",""),
            "cnpj":       data.get("CNPJ",""),
        }
        
        cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

# ── 3. PROVENTOS ──────────────────────────────────────────────────
async def get_proventos(ticker: str) -> list:
    cache_file = CACHE_DIR / f"prov_{ticker}.json"
    if cache_file.exists():
        import time
        if time.time() - cache_file.stat().st_mtime < 3600:
            return json.loads(cache_file.read_text())
    
    try:
        url = f"https://www.comdinheiro.com.br/Proventos001-{ticker}-comdinheiro"
        page = await _fetch(url)
        
        data = await page.evaluate('''() => {
            const rows = [];
            document.querySelectorAll('table tr').forEach(row => {
                const cells = Array.from(row.querySelectorAll('td,th'))
                    .map(c => c.innerText.trim());
                if (cells.some(c => c)) rows.push(cells);
            });
            return rows;
        }''')
        
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return data
    except Exception as e:
        return []

# ── TEST ──────────────────────────────────────────────────────────
async def test():
    print("=== TESTE COMDINHEIRO SCRAPER ===\n")
    
    print("1. Acionistas PETR4:")
    ac = await get_acionistas("PETR4")
    for a in ac.get("acionistas", []):
        print(f"   {a['rank']}. {a['nome']:35s} {a['pct_total']:>8s}")
    
    print("\n2. Fundamentalista WEGE3:")
    fund = await get_fundamentalista("WEGE3")
    for k in ["mkt_cap","ev","ev_ebitda","beta","lpa","roe","div_liq"]:
        print(f"   {k}: {fund.get(k)}")

if __name__ == "__main__":
    asyncio.run(test())
