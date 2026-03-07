import numpy as np
import pandas as pd
import requests
import yfinance as yf


# =====================================================
# CONFIG
# =====================================================

DAMODARAN_BRAZIL_ERP = 0.0747   # Atualizar 1x por ano
DEFAULT_REAL_RF      = 0.074    # Fallback NTNB real (~7.4%)
DEFAULT_INFLATION    = 0.04     # IPCA estrutural
DEFAULT_FALLBACK_RF  = 0.115    # Nominal fallback


# =====================================================
# NTNB LONGA REAL (ANBIMA)
# =====================================================

def fetch_ntnb_real_long(anbima_token: str = None):
    if not anbima_token:
        print("[INFO] Sem token ANBIMA. Usando fallback NTNB real.")
        return DEFAULT_REAL_RF
    try:
        url = "https://api.anbima.com.br/feed/precos-indices/v1/titulos-publicos/curvas-juros"
        headers = {"Authorization": f"Bearer {anbima_token}"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            raise ValueError(f"Erro ANBIMA {response.status_code}")
        data = response.json()
        ipca_curve = [
            x for x in data.get("data", [])
            if x.get("modalidade") == "NTN-B" and x.get("vencimento_anos", 0) >= 10
        ]
        if not ipca_curve:
            raise ValueError("Curva NTN-B longa não encontrada")
        ipca_curve.sort(key=lambda x: x["vencimento_anos"], reverse=True)
        return float(ipca_curve[0]["yield_real"])
    except Exception as e:
        print(f"[WARN] Falha ANBIMA: {e}. Usando fallback NTNB real.")
        return DEFAULT_REAL_RF


def convert_real_to_nominal(real_rate, expected_inflation):
    return (1 + real_rate) * (1 + expected_inflation) - 1


# =====================================================
# BETA REGRESSION
# =====================================================

def fetch_beta_regression(
    ticker_symbol: str,
    market_symbol: str = "^BVSP",
    years: int = 5
):
    end_date   = pd.Timestamp.today()
    start_date = end_date - pd.DateOffset(years=years)

    stock_df  = yf.download(ticker_symbol,  start=start_date, end=end_date,
                             interval="1mo", progress=False, auto_adjust=True)
    market_df = yf.download(market_symbol, start=start_date, end=end_date,
                             interval="1mo", progress=False, auto_adjust=True)

    if stock_df.empty or market_df.empty:
        raise ValueError(
            f"Dados insuficientes para beta de '{ticker_symbol}'. "
            "Verifique o ticker (ex: 'WEGE3.SA')."
        )

    if isinstance(stock_df.columns,  pd.MultiIndex):
        stock_df.columns  = stock_df.columns.get_level_values(0)
    if isinstance(market_df.columns, pd.MultiIndex):
        market_df.columns = market_df.columns.get_level_values(0)

    df = pd.concat([stock_df["Close"], market_df["Close"]], axis=1).dropna()
    df.columns = ["stock", "market"]
    returns = df.pct_change().dropna()

    if len(returns) < 12:
        raise ValueError(f"Histórico insuficiente para beta: {len(returns)} meses.")

    cov = np.cov(returns["stock"], returns["market"])[0][1]
    var = np.var(returns["market"])
    if var == 0:
        raise ValueError("Variância do mercado é zero.")

    return float(cov / var)


# =====================================================
# PESOS REAIS (market-cap + dívida líquida)
# =====================================================

def fetch_capital_structure(
    ticker_symbol: str,
    debt_short: float = None,
    debt_long: float = None,
    cash: float = None,
) -> dict:
    """
    Calcula pesos de equity e dívida usando market cap + DÍVIDA BRUTA.

    ✅ FIX: pesos baseados em dívida BRUTA (não líquida).
    No WACC, os pesos refletem de onde vem o financiamento da empresa:
      - Equity: acionistas → peso = market cap / (market cap + dívida bruta)
      - Dívida: credores  → peso = dívida bruta / (market cap + dívida bruta)
    O caixa reduz o custo efetivo da dívida (via net debt no EV final),
    mas NÃO muda a estrutura de capital para fins de WACC.
    """
    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        info = ticker_obj.info

        market_cap = info.get("marketCap") or info.get("market_cap")
        if not market_cap or market_cap <= 0:
            raise ValueError("market_cap não disponível")

        # Dívida bruta do balanço fornecido
        if debt_short is not None and debt_long is not None:
            gross_debt = max(debt_short + debt_long, 0)
        else:
            gross_debt = max(info.get("totalDebt", 0) or 0, 0)

        # Cash para cálculo do net debt (usado no EV, não no WACC)
        if cash is not None:
            cash_val = cash
        else:
            cash_val = info.get("totalCash", 0) or 0

        net_debt = gross_debt - cash_val

        # EV para WACC = market cap + dívida BRUTA
        ev_wacc = market_cap + gross_debt

        eq_weight   = market_cap / ev_wacc if ev_wacc > 0 else 1.0
        debt_weight = gross_debt / ev_wacc if ev_wacc > 0 else 0.0

        print(f"[WACC] Market Cap      : R$ {market_cap/1e9:.1f} bi")
        print(f"[WACC] Dívida Bruta    : R$ {gross_debt/1e9:.1f} bi")
        print(f"[WACC] Caixa           : R$ {cash_val/1e9:.1f} bi")
        print(f"[WACC] Dívida Líquida  : R$ {net_debt/1e9:.1f} bi")
        print(f"[WACC] Peso Equity     : {eq_weight:.1%}")
        print(f"[WACC] Peso Dívida     : {debt_weight:.1%}")

        return {
            "equity_weight": eq_weight,
            "debt_weight":   debt_weight,
            "market_cap":    market_cap,
            "gross_debt":    gross_debt,
            "net_debt":      net_debt,
        }

    except Exception as e:
        print(f"[WARN] Estrutura de capital via Yahoo: {e}")
        print("[INFO] Usando pesos padrão: equity=75%, dívida=25%")
        return {
            "equity_weight": 0.75,
            "debt_weight":   0.25,
            "market_cap":    None,
            "gross_debt":    None,
            "net_debt":      None,
        }


# =====================================================
# WACC ESTRUTURAL BRASIL
# =====================================================

def build_wacc_structural_brazil(
    ticker_symbol: str,
    cost_of_debt: float,
    tax_rate: float = 0.34,
    # Pesos: None = calcula do market cap (recomendado)
    # Forneça valores explícitos para sobrescrever
    debt_weight: float = None,
    equity_weight: float = None,
    # Balanço mais recente (para calcular dívida líquida real)
    debt_short: float = None,
    debt_long: float = None,
    cash: float = None,
    equity_risk_premium: float = DAMODARAN_BRAZIL_ERP,
    expected_inflation: float  = DEFAULT_INFLATION,
    anbima_token: str = None,
):
    """
    Calcula WACC estrutural com inputs de mercado.

    ✅ FIX 1: pesos calculados do market cap real, não hardcoded.
    ✅ FIX 2: aceita balanço para calcular dívida líquida correta.
    ✅ FIX 3: imprime estrutura de capital para auditoria.
    """

    # ── Risk Free ──────────────────────────────────
    rf_real    = fetch_ntnb_real_long(anbima_token)
    rf_nominal = convert_real_to_nominal(rf_real, expected_inflation)

    # ── Beta ───────────────────────────────────────
    beta = fetch_beta_regression(ticker_symbol)

    # ── Cost of Equity ─────────────────────────────
    cost_of_equity = rf_nominal + beta * equity_risk_premium

    # ── Cost of Debt ───────────────────────────────
    after_tax_debt = cost_of_debt * (1 - tax_rate)

    # ── Estrutura de Capital ───────────────────────
    if debt_weight is None or equity_weight is None:
        cap_struct = fetch_capital_structure(
            ticker_symbol,
            debt_short=debt_short,
            debt_long=debt_long,
            cash=cash,
        )
        eq_w   = cap_struct["equity_weight"]
        debt_w = cap_struct["debt_weight"]
    else:
        # Validação se fornecidos manualmente
        if not np.isclose(debt_weight + equity_weight, 1.0, atol=1e-6):
            raise ValueError(
                f"debt_weight ({debt_weight}) + equity_weight ({equity_weight}) ≠ 1.0"
            )
        eq_w   = equity_weight
        debt_w = debt_weight
        cap_struct = {"market_cap": None, "net_debt": None}

    # ── WACC ───────────────────────────────────────
    wacc = eq_w * cost_of_equity + debt_w * after_tax_debt

    return {
        "risk_free_real":        rf_real,
        "risk_free_nominal":     rf_nominal,
        "beta":                  beta,
        "equity_risk_premium":   equity_risk_premium,
        "cost_of_equity":        cost_of_equity,
        "after_tax_cost_of_debt":after_tax_debt,
        "equity_weight":         eq_w,
        "debt_weight":           debt_w,
        "market_cap":            cap_struct.get("market_cap"),
        "net_debt":              cap_struct.get("net_debt"),
        "wacc":                  wacc,
    }