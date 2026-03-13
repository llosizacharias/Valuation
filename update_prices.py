#!/usr/bin/env python3
"""Atualiza price_now no JSON via brapi + yfinance. Roda via cron."""
import json, sys, requests, logging
sys.path.insert(0, "/opt/shipyard")
import brapi_client as brapi

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger()

results = json.load(open("/opt/shipyard/valuation_results_combined.json"))
all_tks = list(set(v.get("ticker","") for v in results.values() if v.get("ticker","")))

prices = {}
# brapi individual
for tk in all_tks:
    clean = tk.replace(".SA","")
    mapped = brapi.TICKER_MAP.get(clean, clean)
    try:
        r = requests.get(f"https://brapi.dev/api/quote/{mapped}",
            params={"token":"82Pz8JKQS8zatUkoo1PBgr"}, timeout=8)
        res = r.json().get("results",[{}])
        if res and res[0].get("regularMarketPrice"):
            prices[tk] = float(res[0]["regularMarketPrice"])
    except: pass

# yfinance fallback
missing = [t for t in all_tks if t not in prices]
if missing:
    try:
        import yfinance as yf
        raw = yf.download(missing, period="2d", auto_adjust=True, progress=False)
        cl = raw["Close"] if "Close" in raw else raw
        if hasattr(cl,"columns"):
            for tk in missing:
                if tk in cl.columns:
                    v = cl[tk].dropna()
                    if len(v): prices[tk] = float(v.iloc[-1])
    except: pass

updated = 0
for emp, r in results.items():
    tk = r.get("ticker","")
    p = prices.get(tk)
    if p and p > 0.01:
        results[emp]["price_now"] = p
        pj = float(r.get("price_fair") or 0)
        if pj: results[emp]["upside"] = (pj/p - 1)*100
        updated += 1

json.dump(results, open("/opt/shipyard/valuation_results_combined.json","w"),
          ensure_ascii=False, indent=2)
log.info(f"Precos atualizados: {updated}/{len(all_tks)} empresas")
