import numpy as np
import pandas as pd
import requests
import yfinance as yf


# =====================================================
# CONFIG
# =====================================================

DAMODARAN_BRAZIL_ERP = 0.0747   # Atualizar 1x por ano
DEFAULT_REAL_RF = 0.074        # Fallback NTNB real (~7.4%)
DEFAULT_INFLATION = 0.04       # IPCA estrutural
DEFAULT_FALLBACK_RF = 0.115    # Nominal fallback caso tudo falhe


# =====================================================
# NTNB LONGA REAL (ANBIMA)
# =====================================================

def fetch_ntnb_real_long(anbima_token: str = None):
    """
    Busca taxa real longa via API ANBIMA.
    Requer token. Caso falhe, usa fallback real.
    """

    if not anbima_token:
        print("[INFO] Sem token ANBIMA. Usando fallback NTNB real.")
        return DEFAULT_REAL_RF

    try:
        url = "https://api.anbima.com.br/feed/precos-indices/v1/titulos-publicos/curvas-juros"

        headers = {
            "Authorization": f"Bearer {anbima_token}"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            raise Exception(f"Erro ANBIMA {response.status_code}")

        data = response.json()

        # Filtrar NTN-B longas
        ipca_curve = [
            x for x in data.get("data", [])
            if x.get("modalidade") == "NTN-B"
            and x.get("vencimento_anos", 0) >= 10
        ]

        if not ipca_curve:
            raise Exception("Curva NTN-B longa não encontrada")

        ipca_curve.sort(key=lambda x: x["vencimento_anos"], reverse=True)

        return float(ipca_curve[0]["yield_real"])

    except Exception as e:
        print(f"[WARN] Falha ANBIMA: {e}")
        print("[INFO] Usando fallback NTNB real.")
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

    end_date = pd.Timestamp.today()
    start_date = end_date - pd.DateOffset(years=years)

    stock_df = yf.download(
        ticker_symbol,
        start=start_date,
        end=end_date,
        interval="1mo",
        progress=False,
        auto_adjust=True
    )

    market_df = yf.download(
        market_symbol,
        start=start_date,
        end=end_date,
        interval="1mo",
        progress=False,
        auto_adjust=True
    )

    if stock_df.empty or market_df.empty:
        raise ValueError("Dados insuficientes para cálculo de beta")

    stock = stock_df["Close"]
    market = market_df["Close"]

    df = pd.concat([stock, market], axis=1).dropna()
    df.columns = ["stock", "market"]

    returns = df.pct_change().dropna()

    cov = np.cov(returns["stock"], returns["market"])[0][1]
    var = np.var(returns["market"])

    beta = cov / var

    return float(beta)


# =====================================================
# WACC ESTRUTURAL BRASIL
# =====================================================

def build_wacc_structural_brazil(
    ticker_symbol: str,
    cost_of_debt: float,
    tax_rate: float = 0.34,
    debt_weight: float = 0.4,
    equity_weight: float = 0.6,
    equity_risk_premium: float = DAMODARAN_BRAZIL_ERP,
    expected_inflation: float = DEFAULT_INFLATION,
    anbima_token: str = None
):

    if round(debt_weight + equity_weight, 5) != 1:
        raise ValueError("Debt + Equity weights devem somar 1")

    # -------------------------
    # Risk Free Estrutural
    # -------------------------

    rf_real = fetch_ntnb_real_long(anbima_token)

    rf_nominal = convert_real_to_nominal(
        rf_real,
        expected_inflation
    )

    # -------------------------
    # Beta
    # -------------------------

    beta = fetch_beta_regression(ticker_symbol)

    # -------------------------
    # Cost of Equity
    # -------------------------

    cost_of_equity = rf_nominal + beta * equity_risk_premium

    # -------------------------
    # Cost of Debt
    # -------------------------

    after_tax_debt = cost_of_debt * (1 - tax_rate)

    # -------------------------
    # WACC
    # -------------------------

    wacc = (
        equity_weight * cost_of_equity
        + debt_weight * after_tax_debt
    )

    return {
        "risk_free_real": rf_real,
        "risk_free_nominal": rf_nominal,
        "beta": beta,
        "equity_risk_premium": equity_risk_premium,
        "cost_of_equity": cost_of_equity,
        "after_tax_cost_of_debt": after_tax_debt,
        "wacc": wacc
    }