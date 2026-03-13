"""
brapi_client.py — Shipyard | Vela Capital
Wrapper para brapi.dev — cotações B3 em tempo real, histórico, dividendos, fundamentals
Docs: https://brapi.dev/docs
"""
import os, requests, pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache

BRAPI_KEY  = os.getenv("BRAPI_TOKEN", "82Pz8JKQS8zatUkoo1PBgr")
BASE_URL   = "https://brapi.dev/api"
TIMEOUT    = 15

# Tickers com nome diferente no brapi vs B3
TICKER_MAP = {
    "BRFS3":  "BRF",
    "TOTVS3": "TOTS3",
    "FRAS3B": "FRAS3",
    "CPLE6":  "CPLE3",
    "ENBR3":  "ENBR3",   # sem dados em nenhuma fonte
    "STBP3":  "STBP3",   # sem dados em nenhuma fonte
    "AZUL4":  "AZUL4",
    "AURE3":  "AURE3",
    "BRPR3":  "BRPR3",
}
TICKER_MAP_INV = {v: k for k, v in TICKER_MAP.items()}

def _get(endpoint, params=None):
    params = params or {}
    params["token"] = BRAPI_KEY
    r = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# ── 1. COTAÇÃO EM TEMPO REAL ───────────────────────────────────────
def get_quote(tickers: list[str]) -> dict:
    """Retorna dict {ticker: dados} com cotação atual."""
    if not tickers: return {}
    chunk_size = 20  # brapi aceita até ~20 por request
    result = {}
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        # Aplica mapeamento
        mapped = [TICKER_MAP.get(t, t) for t in chunk]
        try:
            data = _get(f"/quote/{','.join(mapped)}")
            if not data.get("results"):
                raise ValueError("sem resultados no batch")
            for item in data.get("results", []):
                sym = TICKER_MAP_INV.get(item["symbol"], item["symbol"])
                result[sym] = {
                    "price":       item.get("regularMarketPrice"),
                    "change_pct":  item.get("regularMarketChangePercent"),
                    "change":      item.get("regularMarketChange"),
                    "high":        item.get("regularMarketDayHigh"),
                    "low":         item.get("regularMarketDayLow"),
                    "volume":      item.get("regularMarketVolume"),
                    "mkt_cap":     item.get("marketCap"),
                    "pe":          item.get("priceEarnings"),
                    "eps":         item.get("earningsPerShare"),
                    "52w_high":    item.get("fiftyTwoWeekHigh"),
                    "52w_low":     item.get("fiftyTwoWeekLow"),
                    "name":        item.get("longName") or item.get("shortName"),
                    "logo":        item.get("logourl"),
                    "updated_at":  item.get("regularMarketTime"),
                }
        except Exception as _batch_err:
            # Fallback: tenta individualmente
            for tk, tk_mapped in zip(chunk, mapped):
                try:
                    d2 = _get(f"/quote/{tk_mapped}")
                    items2 = d2.get("results", [])
                    if items2 and items2[0].get("regularMarketPrice"):
                        it = items2[0]
                        result[tk] = {
                            "price":      it.get("regularMarketPrice"),
                            "change_pct": it.get("regularMarketChangePercent"),
                            "change":     it.get("regularMarketChange"),
                            "high":       it.get("regularMarketDayHigh"),
                            "low":        it.get("regularMarketDayLow"),
                            "volume":     it.get("regularMarketVolume"),
                            "mkt_cap":    it.get("marketCap"),
                            "pe":         it.get("priceEarnings"),
                            "eps":        it.get("earningsPerShare"),
                            "52w_high":   it.get("fiftyTwoWeekHigh"),
                            "52w_low":    it.get("fiftyTwoWeekLow"),
                            "name":       it.get("longName") or it.get("shortName"),
                            "logo":       it.get("logourl"),
                            "updated_at": it.get("regularMarketTime"),
                        }
                except Exception:
                    pass  # ticker não existe no brapi — yfinance fará fallback
    return result

# ── 2. COTAÇÃO COM FUNDAMENTALS ────────────────────────────────────
def get_fundamentals(ticker: str) -> dict:
    """Retorna fundamentals completos de um ativo."""
    try:
        data = _get(f"/quote/{ticker}", {
            "modules": "summaryProfile,defaultKeyStatistics,financialData,incomeStatementHistory"
        })
        res = data.get("results", [{}])[0]
        profile  = res.get("summaryProfile", {}) or {}
        keystats = res.get("defaultKeyStatistics", {}) or {}
        findata  = res.get("financialData", {}) or {}
        return {
            "ticker":       ticker,
            "name":         res.get("longName") or res.get("shortName"),
            "sector":       profile.get("sector"),
            "industry":     profile.get("industry"),
            "website":      profile.get("website"),
            "description":  profile.get("longBusinessSummary"),
            "price":        res.get("regularMarketPrice"),
            "mkt_cap":      res.get("marketCap"),
            "pe":           res.get("priceEarnings"),
            "eps":          res.get("earningsPerShare"),
            "52w_high":     res.get("fiftyTwoWeekHigh"),
            "52w_low":      res.get("fiftyTwoWeekLow"),
            # KeyStats
            "beta":         keystats.get("beta"),
            "shares":       keystats.get("sharesOutstanding"),
            "book_value":   keystats.get("bookValue"),
            "pb":           keystats.get("priceToBook"),
            "roe":          keystats.get("returnOnEquity"),
            "profit_margin":keystats.get("profitMargins"),
            "ev":           keystats.get("enterpriseValue"),
            "ev_ebitda":    keystats.get("enterpriseToEbitda"),
            "ev_revenue":   keystats.get("enterpriseToRevenue"),
            # FinData
            "revenue":      findata.get("totalRevenue", {}).get("raw"),
            "ebitda":       findata.get("ebitda", {}).get("raw"),
            "debt":         findata.get("totalDebt", {}).get("raw"),
            "cash":         findata.get("totalCash", {}).get("raw"),
            "net_debt":     (findata.get("totalDebt",{}).get("raw") or 0) - (findata.get("totalCash",{}).get("raw") or 0),
            "roe_raw":      findata.get("returnOnEquity", {}).get("raw"),
            "roa":          findata.get("returnOnAssets", {}).get("raw"),
            "gross_margin": findata.get("grossMargins", {}).get("raw"),
            "op_margin":    findata.get("operatingMargins", {}).get("raw"),
            "current_ratio":findata.get("currentRatio", {}).get("raw"),
            "rec_growth":   findata.get("revenueGrowth", {}).get("raw"),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

# ── 3. HISTÓRICO DE PREÇOS ─────────────────────────────────────────
def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Retorna DataFrame com histórico de preços.
    period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
    interval: 1d,1wk,1mo
    """
    try:
        data = _get(f"/quote/{ticker}", {"range": period, "interval": interval})
        hist = data.get("results", [{}])[0].get("historicalDataPrice", [])
        if not hist:
            return pd.DataFrame()
        df = pd.DataFrame(hist)
        df["date"] = pd.to_datetime(df["date"], unit="s")
        df = df.set_index("date").sort_index()
        df = df.rename(columns={"open":"Open","high":"High","low":"Low",
                                  "close":"Close","volume":"Volume"})
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception as e:
        return pd.DataFrame()

# ── 4. DIVIDENDOS ──────────────────────────────────────────────────
def get_dividends(ticker: str) -> pd.DataFrame:
    """Retorna histórico de dividendos/JCP."""
    try:
        data = _get(f"/quote/{ticker}", {"dividends": "true"})
        divs = data.get("results", [{}])[0].get("dividendsData", {})
        cash_divs = divs.get("cashDividends", []) if divs else []
        if not cash_divs:
            return pd.DataFrame()
        df = pd.DataFrame(cash_divs)
        for col in ["declaredDate","recordDate","paymentDate"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    except Exception as e:
        return pd.DataFrame()

# ── 5. LISTA DE ATIVOS ─────────────────────────────────────────────
def get_available() -> list[str]:
    """Retorna lista de todos os tickers disponíveis."""
    try:
        data = _get("/available")
        return data.get("stocks", [])
    except:
        return []

# ── 6. COTAÇÕES EM LOTE PARA CARTEIRA ─────────────────────────────
def get_portfolio_prices(tickers: list[str]) -> dict:
    """Cotação em tempo real para lista de tickers da carteira."""
    clean = [t.replace(".SA","") for t in tickers if t != "CAIXA"]
    if not clean: return {}
    raw = get_quote(clean)
    # Remapeia para ticker.SA
    result = {}
    for tk in tickers:
        clean_tk = tk.replace(".SA","")
        if clean_tk in raw:
            result[tk] = raw[clean_tk]
        elif tk in raw:
            result[tk] = raw[tk]
    return result

# ── 7. TESTE DE CONEXÃO ────────────────────────────────────────────
def test_connection() -> dict:
    try:
        q = get_quote(["PETR4"])
        if "PETR4" in q and "price" in q["PETR4"]:
            return {"ok": True, "msg": f"brapi OK — PETR4: R${q['PETR4']['price']}"}
        return {"ok": False, "msg": "Resposta inesperada"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

if __name__ == "__main__":
    print(test_connection())
    print("\nHistórico WEGE3 1y:")
    df = get_history("WEGE3", "1y", "1d")
    print(df.tail(3) if not df.empty else "Vazio")
    print("\nDividendos TAEE11:")
    print(get_dividends("TAEE11").head(5))
