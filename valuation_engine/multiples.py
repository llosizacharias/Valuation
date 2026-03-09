"""
multiples.py — cálculo de múltiplos de valuation.

Usa o último ano histórico disponível em combined_df (onde existem
EBIT, DEPRECIATION e NET_INCOME reais). Projeções não são usadas
para múltiplos de entrada (LTM — Last Twelve Months).
"""

import pandas as pd


def compute_multiples(
    enterprise_value: float,
    combined_df: pd.DataFrame,
    market_cap: float = None,
    last_historical_year: int = 2024,
) -> dict:
    """
    Calcula múltiplos EV/EBITDA, EV/EBIT, P/E e EV/Receita.

    Usa obrigatoriamente o último ano histórico (não projeção),
    pois múltiplos de entrada são sempre calculados sobre LTM.

    Parâmetros:
      enterprise_value    : EV do DCF (R$)
      combined_df         : df com histórico + projeção, index = year
      market_cap          : market cap atual (para P/E). Se None, usa EV como proxy.
      last_historical_year: último ano com dados reais (default 2024)
    """
    result = {}

    # Isola apenas anos históricos
    hist = combined_df[combined_df.index <= last_historical_year].copy()

    if hist.empty:
        return result

    last = hist.iloc[-1]

    def _get(col):
        if col in hist.columns:
            v = last[col]
            return float(v) if pd.notna(v) else None
        return None

    ebit         = _get("EBIT")
    depreciation = _get("DEPRECIATION")
    revenue      = _get("REVENUE")
    net_income   = _get("NET_INCOME")

    # ── EBITDA ───────────────────────────────────────────────
    if ebit is not None and depreciation is not None:
        ebitda = ebit + abs(depreciation)
    elif ebit is not None:
        ebitda = None  # não computa sem D&A
        print("[MULT] WARN: DEPRECIATION ausente — EV/EBITDA não calculado")
    else:
        ebitda = None

    # ── EV/EBITDA ────────────────────────────────────────────
    if ebitda and ebitda > 0 and enterprise_value:
        result["EV/EBITDA"] = enterprise_value / ebitda
    else:
        result["EV/EBITDA"] = None

    # ── EV/EBIT ──────────────────────────────────────────────
    if ebit and ebit > 0 and enterprise_value:
        result["EV/EBIT"] = enterprise_value / ebit
    else:
        result["EV/EBIT"] = None

    # ── EV/Receita ───────────────────────────────────────────
    if revenue and revenue > 0 and enterprise_value:
        result["EV/Revenue"] = enterprise_value / revenue
    else:
        result["EV/Revenue"] = None

    # ── P/E ──────────────────────────────────────────────────
    cap = market_cap or enterprise_value  # fallback: usa EV se sem market cap
    if net_income and net_income > 0 and cap:
        result["P/E"] = cap / net_income
    else:
        result["P/E"] = None

    # Log para auditoria
    print(f"[MULT] EBIT       : R$ {ebit/1e9:.3f} bi"        if ebit         else "[MULT] EBIT: n/d")
    print(f"[MULT] D&A        : R$ {abs(depreciation)/1e9:.3f} bi" if depreciation else "[MULT] D&A: n/d")
    print(f"[MULT] EBITDA     : R$ {ebitda/1e9:.3f} bi"      if ebitda       else "[MULT] EBITDA: n/d")
    print(f"[MULT] NET_INCOME : R$ {net_income/1e9:.3f} bi"  if net_income   else "[MULT] NET_INCOME: n/d")
    print(f"[MULT] EV/EBITDA  : {result['EV/EBITDA']:.1f}x"  if result.get("EV/EBITDA") else "[MULT] EV/EBITDA: n/d")
    print(f"[MULT] EV/EBIT    : {result['EV/EBIT']:.1f}x"    if result.get("EV/EBIT")   else "[MULT] EV/EBIT: n/d")
    print(f"[MULT] P/E        : {result['P/E']:.1f}x"        if result.get("P/E")        else "[MULT] P/E: n/d")

    return result