CVM_TO_TICKER = {
    "906": "BBDC4",
    "1023": "BBAS3",
    "1210": "BRSR6",
    "1287": "ITUB4",
    "2577": "CESP6",
    "3980": "GGBR4",
    "4030": "CSNA3",
    "4820": "BRKM5",
    "6211": "FRAS3B",
    "6343": "TUPY3",
    "8133": "LREN3",
    "9067": "SUZB3",
    "9342": "PNVL3",
    "12653": "KLBN11",
    "13714": "VIVT3",
    "14109": "RAPT4",
    "14311": "CPLE6",
    "14320": "USIM5",
    "14443": "SBSP3",
    "14460": "CYRE3",
    "16292": "BRFS3",
    "17329": "EGIE3",
    "17450": "RAIL3",
    "17892": "STBP3",
    "18627": "SAPR11",
    "19445": "CSMG3",
    "19550": "NTCO3",
    "19569": "GOLL4",
    "19623": "DASA3",
    "19763": "ENBR3",
    "19836": "CSAN3",
    "19925": "BRPR3",
    "19992": "TOTVS3",
    "20010": "EQTL3",
    "20087": "EMBR3",
    "20125": "ODPV3",
    "20320": "CMIG4",
    "20338": "MDIA3",
    "20362": "POSI3",
    "20494": "IGTI11",
    "20524": "EVEN3",
    "20532": "SANB11",
    "20575": "JBSS3",
    "20605": "JHSF3",
    "20745": "SLCE3",
    "20770": "EZTC3",
    "20788": "MRFG3",
    "20915": "MRVE3",
    "20958": "ABCB4",
    "20982": "MULT3",
    "21016": "YDUQ3",
    "21091": "DXCO3",
    "21121": "SULA11",
    "21148": "TEND3",
    "21350": "DIRR3",
    "21490": "TIMS3",
    "21903": "ECOR3",
    "22497": "QUAL3",
    "22616": "BPAC11",
    "22675": "HBSA3",
    "22799": "SQIA3",
    "23000": "LIGT3",
    "23159": "BBSE3",
    "23221": "SEER3",
    "23248": "ANIM3",
    "23590": "WIZC3",
    "23795": "CXSE3",
    "24112": "AZUL4",
    "24180": "IRBR3",
    "24392": "HAPV3",
    "24600": "BMGB4",
    "24902": "MTRE3",
    "24961": "AMBP3",
    "25372": "ASAI3",
    "25453": "INTB3",
    "25569": "ROMI3",
    "25984": "CBAV3",
    "26620": "AURE3",
}

"""
b3_runner.py
─────────────────────────────────────────────────────────────────
Motor paralelo de valuation para TODAS as empresas da B3.

Características:
  - ThreadPoolExecutor com N workers configurável
  - Checkpoint a cada CHECKPOINT_INTERVAL empresas (resume automático)
  - Timeout por empresa (evita travar no yfinance)
  - Log detalhado por empresa em logs/b3_runner.log
  - Saída em valuation_results_b3.json (compatível com dashboard.py)

Uso:
  python b3_runner.py                    # roda tudo
  python b3_runner.py --workers 4        # 4 workers paralelos
  python b3_runner.py --resume           # continua de onde parou
  python b3_runner.py --sector EDUCAÇÃO  # só um setor
  python b3_runner.py --test 10          # testa com 10 empresas
"""

import argparse
import json
import logging
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────
OUTPUT_JSON       = Path("valuation_results_b3.json")
CHECKPOINT_PATH   = Path("data/b3_checkpoint.json")
LOG_PATH          = Path("logs/b3_runner.log")
CHECKPOINT_EVERY  = 10   # salva checkpoint a cada N empresas

# ── Logging ──────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("b3_runner")


# ─────────────────────────────────────────────────────────────────
# Serialização (copia de main.py)
# ─────────────────────────────────────────────────────────────────
def serialize(obj):
    if isinstance(obj, (np.integer,)):   return int(obj)
    if isinstance(obj, (np.floating,)):  return float(obj)
    if isinstance(obj, np.ndarray):      return obj.tolist()
    raise TypeError(f"Not serializable: {type(obj)}")


def clean(d):
    if isinstance(d, dict):
        return {k: clean(v) for k, v in d.items()
                if not isinstance(v, (pd.DataFrame, pd.Series))}
    return d


# ─────────────────────────────────────────────────────────────────
# Preço atual via yfinance
# ─────────────────────────────────────────────────────────────────
def get_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        p = t.fast_info.get("lastPrice") or t.fast_info.get("last_price")
        if p:
            return float(p)
        h = t.history(period="1d")
        return float(h["Close"].iloc[-1]) if not h.empty else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# Runner por empresa (baseado em deterministic_runner mas usando cache)
# ─────────────────────────────────────────────────────────────────
def run_single_company(nome: str, cfg: dict) -> dict | None:
    """
    Executa o pipeline completo de valuation para uma empresa.
    Usa o cache Parquet do b3_data_prefetch em vez de baixar novamente.
    Retorna record dict compatível com valuation_results.json, ou None se falhar.
    """
    from b3_data_prefetch import load_company_data
    from financial_model.dre_model import build_dre_projection

    # Mapa de categorias CVM → pipeline (embutido para não depender de app.deterministic_runner)
    CVM_TO_PIPELINE = {
        "REVENUE": "REVENUE", "COGS": "COGS", "GROSS_PROFIT": "GROSS_PROFIT",
        "SELLING_EXPENSES": "SELLING_EXPENSES", "GA_EXPENSES": "GA_EXPENSES",
        "EBIT": "EBIT", "FIN_INCOME": "FIN_INCOME", "FIN_EXPENSE": "FIN_EXPENSE",
        "EBT": "EBT", "TAXES": "TAXES", "NET_INCOME": "NET_INCOME",
        "NET_INCOME_CONT": "NET_INCOME", "DEPRECIATION": "DEPRECIATION",
        "CAPEX_FIXED": "CAPEX", "CAPEX_INTANGIBLE": "CAPEX",
        "OPER_CF": "OPER_CF", "INVEST_CF": "INVEST_CF", "FIN_CF": "FIN_CF",
        "CASH": "CASH", "FIN_INVESTMENTS": "FIN_INVESTMENTS",
        "FIN_INVESTMENTS_LT": "FIN_INVESTMENTS_LT",
        "DEBT_SHORT": "DEBT_SHORT", "DEBT_LONG": "DEBT_LONG",
        "DEBT_SHORT_FIN": "DEBT_SHORT_FIN", "DEBT_LONG_FIN": "DEBT_LONG_FIN",
        "LEASE_SHORT": "LEASE_SHORT", "LEASE_LONG": "LEASE_LONG",
        "EQUITY": "EQUITY", "TOTAL_ASSETS": "TOTAL_ASSETS",
        "TOTAL_LIABILITIES": "TOTAL_LIABILITIES",
    }
    from financial_model.historical_cleaner import clean_historical_data
    from valuation_engine.dcf_engine import build_dcf
    from valuation_engine.fcff_engine import build_fcff
    from valuation_engine.multiples import compute_multiples
    from valuation_engine.wacc_model import build_wacc_structural_brazil

    ticker        = cfg.get("ticker", "")
    cvm_code      = cfg.get("cvm_code", "")
    shares_out    = cfg.get("shares_out") or 0
    term_growth   = cfg.get("terminal_growth", 0.04)
    cost_of_debt  = cfg.get("cost_of_debt", 0.12)
    rev_override  = cfg.get("revenue_growth_override")
    ebit_override = cfg.get("ebit_margin_override")
    ifrs16        = cfg.get("ifrs16_lease_total")
    last_year     = 2024
    tax_rate      = 0.34

    # ── 1) Carrega dados do cache ─────────────────────────────
    df_data = load_company_data(cvm_code)
    if df_data.empty:
        raise ValueError(f"Sem dados no cache para CVM {cvm_code}")

    # Mapeia categorias CVM → categorias internas
    df_data = df_data.copy()
    df_data["category"] = df_data["category"].map(CVM_TO_PIPELINE)
    df_data = df_data[df_data["category"].notna()]
    df_data = df_data[df_data["year"] <= last_year]

    if df_data.empty:
        raise ValueError("Sem categorias mapeadas após CVM_TO_PIPELINE")

    # ── 2) Pivot ───────────────────────────────────────────────
    df_annual = (
        df_data.groupby(["year", "category"])["value"]
        .sum().unstack().sort_index()
    )

    # CAPEX: se não encontrado, tenta derivar de ativo imobilizado
    if "CAPEX" not in df_annual.columns:
        cap_cols = [c for c in df_annual.columns if "CAPEX" in c]
        if cap_cols:
            df_annual["CAPEX"] = df_annual[cap_cols].abs().sum(axis=1)

    # ── 3) Limpeza histórica ───────────────────────────────────
    historical_df = clean_historical_data(
        df_annual, last_historical_year=last_year, min_years=3
    )

    # ── 4) Projeção DRE ───────────────────────────────────────
    dre_projection = build_dre_projection(
        historical_df,
        forecast_years=6,
        tax_rate=tax_rate,
        terminal_growth=term_growth,
        revenue_growth_override=rev_override,
        ebit_margin_override=ebit_override,
    )

    # ── 5) FCFF ───────────────────────────────────────────────
    combined_df = pd.concat([historical_df, dre_projection])
    fcff_series = build_fcff(combined_df, tax_rate=tax_rate)
    combined_df["FCFF"] = fcff_series

    # ── 6) WACC ───────────────────────────────────────────────
    debt_s = float(historical_df["DEBT_SHORT"].iloc[-1]) if "DEBT_SHORT" in historical_df.columns else 0.0
    debt_l = float(historical_df["DEBT_LONG"].iloc[-1])  if "DEBT_LONG"  in historical_df.columns else 0.0
    cash_t = 0.0
    for col in ["CASH", "FIN_INVESTMENTS", "FIN_INVESTMENTS_LT"]:
        if col in historical_df.columns:
            cash_t += float(historical_df[col].iloc[-1]) or 0.0

    wacc_data = build_wacc_structural_brazil(
        ticker_symbol=ticker,
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        debt_short=debt_s,
        debt_long=debt_l,
        cash=cash_t,
    )
    wacc = wacc_data["wacc"]

    # ── 7) DCF ────────────────────────────────────────────────
    projected_fcff = combined_df.loc[combined_df.index > last_year, "FCFF"]
    if projected_fcff.empty:
        raise ValueError("Nenhum FCFF projetado")

    dcf_results      = build_dcf(projected_fcff, wacc=wacc, terminal_growth=term_growth)
    enterprise_value = dcf_results["enterprise_value"]

    # ── 8) Net Debt / Equity Value ────────────────────────────
    has_fin_debt = (
        "DEBT_SHORT_FIN" in historical_df.columns and
        "DEBT_LONG_FIN"  in historical_df.columns
    )
    has_lease = (
        "LEASE_SHORT" in historical_df.columns or
        "LEASE_LONG"  in historical_df.columns
    )

    if ifrs16 is not None:
        gross_debt = debt_s + debt_l
        debt = float(gross_debt) - ifrs16
    elif has_fin_debt:
        debt_fin   = (historical_df["DEBT_SHORT_FIN"].iloc[-1] +
                      historical_df["DEBT_LONG_FIN"].iloc[-1])
        debt_total = debt_s + debt_l
        ratio = float(debt_fin) / float(debt_total) if debt_total > 0 else 1.0
        debt = float(debt_total) if ratio < 0.15 else float(debt_fin)
    elif has_lease:
        lease_s = float(historical_df.get("LEASE_SHORT", pd.Series([0])).iloc[-1]) if "LEASE_SHORT" in historical_df.columns else 0.0
        lease_l = float(historical_df.get("LEASE_LONG",  pd.Series([0])).iloc[-1]) if "LEASE_LONG"  in historical_df.columns else 0.0
        debt = (debt_s + debt_l) - (lease_s + lease_l)
    else:
        debt = debt_s + debt_l

    net_debt    = float(debt) - cash_t
    equity_val  = enterprise_value - net_debt

    # ── 9) Múltiplos ──────────────────────────────────────────
    multiples = compute_multiples(
        enterprise_value, combined_df,
        market_cap=wacc_data.get("market_cap"),
        last_historical_year=last_year,
    )

    # ── 10) Preço + Recomendação ──────────────────────────────
    price_now  = get_price(ticker)
    price_fair = (equity_val / shares_out) if shares_out and equity_val > 0 else 0
    upside     = ((price_fair - price_now) / price_now) if price_now and price_fair else 0

    if   upside >  0.15: rec = "COMPRA FORTE"
    elif upside >  0.05: rec = "COMPRA"
    elif upside > -0.15: rec = "NEUTRO"
    elif upside > -0.30: rec = "VENDA"
    else:                rec = "VENDA FORTE"

    # ── 11) KPIs históricos ───────────────────────────────────
    roic = roe = ebit_margin = net_margin = cagr_revenue = 0.0
    try:
        last = historical_df.iloc[-1]
        rev  = abs(float(last.get("REVENUE", 1))) or 1
        ebit_v  = float(last.get("EBIT", 0))
        ni_v    = float(last.get("NET_INCOME", 0))
        eq_v    = float(last.get("EQUITY", 1)) or 1
        inv_cap = (debt + eq_v) or 1
        ebit_margin = ebit_v / rev
        net_margin  = ni_v  / rev
        roic        = ebit_v * 0.66 / inv_cap
        roe         = ni_v / eq_v
        if len(historical_df) >= 2:
            r0 = abs(float(historical_df.iloc[0].get("REVENUE", 0)))
            rn = abs(float(historical_df.iloc[-1].get("REVENUE", 0)))
            n  = len(historical_df) - 1
            cagr_revenue = float((rn / r0) ** (1 / n) - 1) if r0 > 0 else 0
    except Exception:
        pass

    # FCFF série para dashboard
    fcff_series_dict = {}
    try:
        fcff_series_dict = {
            str(int(k)): float(v)
            for k, v in combined_df["FCFF"].items()
        }
    except Exception:
        pass

    return {
        "empresa":          nome,
        "ticker":           ticker,
        "cvm_code":         cvm_code,
        "setor":            cfg.get("setor", ""),
        "setor_raw":        cfg.get("setor_raw", ""),
        "price_now":        price_now or 0,
        "price_fair":       price_fair,
        "upside":           upside,
        "recomendacao":     rec,
        "enterprise_value": enterprise_value,
        "equity_value":     equity_val,
        "net_debt":         net_debt,
        "wacc":             wacc_data.get("wacc", 0),
        "beta":             wacc_data.get("beta", 0),
        "wacc_data":        wacc_data,
        "roic":             roic,
        "roe":              roe,
        "ebit_margin":      ebit_margin,
        "net_margin":       net_margin,
        "cagr_revenue":     cagr_revenue,
        "ev_ebitda":        multiples.get("EV/EBITDA", 0) or 0,
        "ev_ebit":          multiples.get("EV/EBIT", 0) or 0,
        "pe":               multiples.get("P/E", 0) or 0,
        "ev_revenue":       multiples.get("EV/Revenue", 0) or 0,
        "dcf_pv_fcf":       dcf_results.get("pv_fcf", 0),
        "dcf_pv_terminal":  dcf_results.get("pv_terminal", 0),
        "terminal_growth":  term_growth,
        "cost_of_debt":     cost_of_debt,
        "shares_out":       shares_out,
        "fcff_series":      fcff_series_dict,
    }


# ─────────────────────────────────────────────────────────────────
# Checkpoint helpers
# ─────────────────────────────────────────────────────────────────
def _load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {}


def _save_checkpoint(results: dict):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(clean(results), f, default=serialize, indent=2)


# ─────────────────────────────────────────────────────────────────
# Executor principal
# ─────────────────────────────────────────────────────────────────
def run_b3(
    workers: int = 3,
    resume: bool = True,
    sector_filter: str = None,
    test_limit: int = None,
    timeout_per_company: int = 120,
):
    """
    Executa valuation para todas as empresas B3.

    Args:
        workers            : número de threads paralelas
        resume             : retoma de onde parou (usa checkpoint)
        sector_filter      : filtra por setor (ex: "EDUCAÇÃO")
        test_limit         : limita a N empresas (para teste)
        timeout_per_company: timeout em segundos por empresa
    """
    from b3_catalog import load_catalog

    log.info("=" * 60)
    log.info(f"B3 Runner iniciado — {datetime.now():%Y-%m-%d %H:%M}")
    log.info("=" * 60)

    # ── Carrega catálogo ──────────────────────────────────────
    catalog = load_catalog()
    # Filtra apenas empresas que têm dados no cache local
    catalog = {k: v for k, v in catalog.items() if v.get('has_cache', True)}

    log.info(f"Catálogo: {len(catalog)} empresas")

    # ── Filtra setor ──────────────────────────────────────────
    if sector_filter:
        catalog = {k: v for k, v in catalog.items()
                   if sector_filter.upper() in v.get("setor", "").upper()}
        log.info(f"Filtro setor '{sector_filter}': {len(catalog)} empresas")

    # ── Limita para teste ─────────────────────────────────────
    if test_limit:
        catalog = dict(list(catalog.items())[:test_limit])
        log.info(f"Modo teste: limitado a {test_limit} empresas")

    # ── Resume: pula empresas já processadas ──────────────────
    results: dict = {}
    if resume:
        results = _load_checkpoint()
        skip    = set(results.keys())
        catalog = {k: v for k, v in catalog.items() if k not in skip}
        log.info(f"Resume: {len(skip)} já processadas, {len(catalog)} restantes")

    # ── Counters ──────────────────────────────────────────────
    total    = len(catalog)
    done     = 0
    success  = 0
    failed   = 0
    t_start  = time.time()

    log.info(f"Iniciando {total} valuations com {workers} workers...\n")

    # ── Loop paralelo ─────────────────────────────────────────
    company_list = list(catalog.items())

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_single_company, nome, cfg): nome
            for nome, cfg in company_list
        }

        for future in as_completed(futures, timeout=None):
            nome = futures[future]
            done += 1
            elapsed = time.time() - t_start
            eta_s   = (elapsed / done) * (total - done) if done > 0 else 0

            try:
                record = future.result(timeout=timeout_per_company)
                if record:
                    results[nome] = record
                    success += 1
                    log.info(
                        f"[{done:3d}/{total}] ✅ {nome:40s} "
                        f"R${record['price_fair']:.2f} | "
                        f"{record['upside']*100:+.1f}% | "
                        f"{record['recomendacao']} | "
                        f"ETA {eta_s/60:.0f}min"
                    )
                else:
                    failed += 1
                    log.warning(f"[{done:3d}/{total}] ⚠️  {nome}: retornou None")

            except TimeoutError:
                failed += 1
                log.warning(f"[{done:3d}/{total}] ⏰ {nome}: timeout ({timeout_per_company}s)")

            except Exception as e:
                failed += 1
                log.warning(f"[{done:3d}/{total}] ❌ {nome}: {type(e).__name__}: {e}")
                if "insuficiente" not in str(e).lower() and "sem dados" not in str(e).lower():
                    log.debug(traceback.format_exc())

            # Checkpoint periódico
            if done % CHECKPOINT_EVERY == 0:
                _save_checkpoint(results)
                log.info(f"  💾 Checkpoint: {len(results)} resultados salvos")

    # ── Resultado final ───────────────────────────────────────
    elapsed_total = time.time() - t_start
    log.info("\n" + "=" * 60)
    log.info(f"✅ Concluído em {elapsed_total/60:.1f} minutos")
    log.info(f"   Sucesso   : {success}/{total}")
    log.info(f"   Falhas    : {failed}/{total}")
    log.info(f"   Taxa sucesso: {success/total*100:.0f}%" if total > 0 else "   Taxa sucesso: n/a")
    log.info("=" * 60)

    # Salva resultado final
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(clean(results), f, default=serialize, indent=2)
    log.info(f"📁 Resultado salvo em {OUTPUT_JSON}")

    # Remove checkpoint (run completo)
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    # Estatísticas por setor
    _print_sector_summary(results)

    return results


def _print_sector_summary(results: dict):
    """Imprime resumo de resultados por setor."""
    if not results:
        return

    by_sector: dict[str, list] = {}
    for nome, r in results.items():
        setor = r.get("setor", "DEFAULT")
        by_sector.setdefault(setor, []).append(r)

    log.info("\n─── Resumo por Setor ─────────────────────────────────")
    log.info(f"{'Setor':35s} {'N':>4}  {'Upside médio':>12}  {'Compras':>7}")
    log.info("─" * 65)

    for setor, items in sorted(by_sector.items()):
        upsides  = [i["upside"] for i in items if i.get("upside")]
        compras  = sum(1 for i in items if i.get("recomendacao") in ("COMPRA", "COMPRA FORTE"))
        avg_up   = sum(upsides) / len(upsides) * 100 if upsides else 0
        log.info(f"{setor:35s} {len(items):>4}  {avg_up:>+11.1f}%  {compras:>7}")

    log.info("─" * 65)


# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="B3 Full Valuation Runner")
    parser.add_argument("--workers",  type=int, default=3,
                        help="Número de workers paralelos (default: 3)")
    parser.add_argument("--resume",   action="store_true", default=True,
                        help="Resume de checkpoint (default: True)")
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--sector",   type=str, default=None,
                        help="Filtra por setor (ex: --sector EDUCAÇÃO)")
    parser.add_argument("--test",     type=int, default=None,
                        help="Limita a N empresas para teste rápido")
    args = parser.parse_args()

    run_b3(
        workers=args.workers,
        resume=args.resume,
        sector_filter=args.sector,
        test_limit=args.test,
    )