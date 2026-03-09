import numpy as np
import pandas as pd
import requests
import yfinance as yf


# =====================================================
# CONFIG
# =====================================================

DAMODARAN_BRAZIL_ERP = 0.0747
DEFAULT_REAL_RF      = 0.074
DEFAULT_INFLATION    = 0.04
DEFAULT_FALLBACK_RF  = 0.115


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
            raise ValueError(f"HTTP {response.status_code}")
        data = response.json()
        ntnb_curves = [
            x for x in data
            if "IPCA" in x.get("nome_titulo", "").upper()
            and x.get("vencimento_anos", 0) >= 5
        ]
        if not ntnb_curves:
            raise ValueError("Sem curvas NTNB disponíveis")
        ntnb_curves.sort(key=lambda x: x["vencimento_anos"], reverse=True)
        return float(ntnb_curves[0]["yield_real"])
    except Exception as e:
        print(f"[WARN] Falha ANBIMA: {e}. Usando fallback NTNB real.")
        return DEFAULT_REAL_RF


def convert_real_to_nominal(real_rate, expected_inflation):
    return (1 + real_rate) * (1 + expected_inflation) - 1


# =====================================================
# BETA REGRESSION  (Blume adjustment + janela 3 anos)
# =====================================================

def fetch_beta_regression(
    ticker_symbol: str,
    market_symbol: str = "^BVSP",
    years: int = 3,
    apply_blume: bool = True,
    beta_cap: float = 1.8,
):
    """
    Calcula beta por regressão de retornos mensais.

    ✅ FIX 1 — Janela 3 anos (antes: 5 anos):
        Janela de 5 anos capturava crise 2020-2022, inflando beta artificialmente
        para empresas em turnaround. 3 anos reflete risco operacional atual.

    ✅ FIX 2 — Blume adjustment: β_adj = 0.67*β_raw + 0.33*1.0
        Ajuste empírico (Blume 1975): betas extremos convergem para 1.0.
        Reduz overshooting em empresas com histórico volátil.

    ✅ FIX 3 — Cap em 1.8:
        Empresas operacionais não-financeiras raramente sustentam beta>1.8.
        Valores acima costumam refletir illiquidez ou ruído estatístico.
    """
    end_date   = pd.Timestamp.today()
    start_date = end_date - pd.DateOffset(years=years)

    stock_df  = yf.download(ticker_symbol, start=start_date, end=end_date,
                             interval="1mo", progress=False, auto_adjust=True)
    market_df = yf.download(market_symbol, start=start_date, end=end_date,
                             interval="1mo", progress=False, auto_adjust=True)

    if stock_df.empty or market_df.empty:
        raise ValueError(
            f"Dados insuficientes para beta de '{ticker_symbol}'. "
            "Verifique o ticker (ex: 'COGN3.SA')."
        )

    if isinstance(stock_df.columns,  pd.MultiIndex):
        stock_df.columns  = stock_df.columns.get_level_values(0)
    if isinstance(market_df.columns, pd.MultiIndex):
        market_df.columns = market_df.columns.get_level_values(0)

    df = pd.concat([stock_df["Close"], market_df["Close"]], axis=1).dropna()
    df.columns = ["stock", "market"]
    returns = df.pct_change().dropna()

    if len(returns) < 12:
        raise ValueError(f"Historico insuficiente para beta: {len(returns)} meses.")

    cov      = np.cov(returns["stock"], returns["market"])[0][1]
    var      = np.var(returns["market"])
    if var == 0:
        raise ValueError("Variancia do mercado e zero.")

    beta_raw = float(cov / var)

    if apply_blume:
        beta_adj = 0.67 * beta_raw + 0.33 * 1.0
        print(f"[BETA] Raw: {beta_raw:.3f}  |  Blume adjusted: {beta_adj:.3f}  "
              f"(window: {years}a, {len(returns)} obs)")
    else:
        beta_adj = beta_raw
        print(f"[BETA] Raw: {beta_raw:.3f}  (sem Blume, window: {years}a)")

    if beta_adj > beta_cap:
        print(f"[BETA] Capped {beta_adj:.3f} -> {beta_cap:.3f}")
        beta_adj = beta_cap

    return beta_adj


# =====================================================
# PESOS REAIS (market-cap + dívida bruta)
# =====================================================

def fetch_capital_structure(
    ticker_symbol: str,
    debt_short: float = None,
    debt_long: float = None,
    cash: float = None,
) -> dict:
    """
    Pesos de equity e dívida usando market cap + DÍVIDA BRUTA.
    Caixa NÃO altera pesos do WACC (reduz EV no final via net_debt).
    """
    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        info       = ticker_obj.info

        market_cap = info.get("marketCap") or info.get("market_cap")
        if not market_cap or market_cap <= 0:
            raise ValueError("market_cap nao disponivel")

        if debt_short is not None and debt_long is not None:
            gross_debt = debt_short + debt_long
        else:
            total_debt = info.get("totalDebt", 0) or 0
            gross_debt = float(total_debt)

        net_debt      = gross_debt - (cash or 0.0)
        total_capital = market_cap + gross_debt
        if total_capital <= 0:
            raise ValueError("Capital total invalido")

        equity_weight = market_cap / total_capital
        debt_weight   = gross_debt / total_capital

        print(f"[WACC] Market Cap      : R$ {market_cap/1e9:.1f} bi")
        print(f"[WACC] Divida Bruta    : R$ {gross_debt/1e9:.1f} bi")
        print(f"[WACC] Caixa           : R$ {(cash or 0)/1e9:.1f} bi")
        print(f"[WACC] Divida Liquida  : R$ {net_debt/1e9:.1f} bi")
        print(f"[WACC] Peso Equity     : {equity_weight:.1%}")
        print(f"[WACC] Peso Divida     : {debt_weight:.1%}")

        return {
            "equity_weight": equity_weight,
            "debt_weight":   debt_weight,
            "market_cap":    market_cap,
            "gross_debt":    gross_debt,
            "net_debt":      net_debt,
        }

    except Exception as e:
        print(f"[WARN] Estrutura de capital via Yahoo: {e}")
        print("[INFO] Usando pesos padrao: equity=75%, divida=25%")
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
    debt_weight: float = None,
    equity_weight: float = None,
    debt_short: float = None,
    debt_long: float = None,
    cash: float = None,
    equity_risk_premium: float = DAMODARAN_BRAZIL_ERP,
    expected_inflation: float  = DEFAULT_INFLATION,
    anbima_token: str = None,
    beta_years: int = 3,
    apply_blume: bool = True,
):
    # Risk Free
    rf_real    = fetch_ntnb_real_long(anbima_token)
    rf_nominal = convert_real_to_nominal(rf_real, expected_inflation)

    # Beta
    try:
        beta = fetch_beta_regression(
            ticker_symbol,
            years=beta_years,
            apply_blume=apply_blume,
        )
    except Exception as e:
        print(f"[WARN] Beta regression falhou: {e}. Usando beta=1.0.")
        beta = 1.0

    # Cost of Equity
    cost_of_equity = rf_nominal + beta * equity_risk_premium

    # Cost of Debt
    after_tax_debt = cost_of_debt * (1 - tax_rate)

    # Estrutura de Capital
    if debt_weight is None or equity_weight is None:
        cap_struct     = fetch_capital_structure(
            ticker_symbol,
            debt_short=debt_short,
            debt_long=debt_long,
            cash=cash,
        )
        eq_w           = cap_struct["equity_weight"]
        debt_w         = cap_struct["debt_weight"]
        market_cap_val = cap_struct["market_cap"]
        net_debt_val   = cap_struct["net_debt"]
    else:
        if not np.isclose(debt_weight + equity_weight, 1.0, atol=1e-6):
            raise ValueError(
                f"debt_weight ({debt_weight}) + equity_weight ({equity_weight}) != 1.0"
            )
        eq_w           = equity_weight
        debt_w         = debt_weight
        market_cap_val = None
        net_debt_val   = (debt_short or 0) + (debt_long or 0) - (cash or 0)

    # WACC
    wacc = eq_w * cost_of_equity + debt_w * after_tax_debt

    # Retorno real (descontado IPCA)
    real_return = (1 + wacc) / (1 + expected_inflation) - 1

    return {
        "risk_free_real":         rf_real,
        "risk_free_nominal":      rf_nominal,
        "beta":                   beta,
        "equity_risk_premium":    equity_risk_premium,
        "cost_of_equity":         cost_of_equity,
        "after_tax_cost_of_debt": after_tax_debt,
        "equity_weight":          eq_w,
        "debt_weight":            debt_w,
        "market_cap":             market_cap_val,
        "net_debt":               net_debt_val,
        "wacc":                   wacc,
        "real_return":            real_return,
    }