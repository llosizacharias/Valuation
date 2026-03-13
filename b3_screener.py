"""
b3_screener.py
─────────────────────────────────────────────────────────────────
Screener pós-valuation: lê valuation_results_b3.json e gera:
  1. Ranking geral por upside
  2. Rankings por setor
  3. Filtros: só compras, só grandes, etc.
  4. Export Excel com múltiplas abas

Uso:
  python b3_screener.py                       # gera screener completo
  python b3_screener.py --top 50              # só top 50 upsides
  python b3_screener.py --rec "COMPRA FORTE"  # filtro por recomendação
  python b3_screener.py --min-mcap 1          # mínimo R$ 1bi de market cap
"""

import argparse
import json
from pathlib import Path

import pandas as pd

INPUT_B3   = Path("valuation_results_b3.json")
INPUT_MAIN = Path("valuation_results.json")         # cobertura manual (WEG, COGNA)
OUTPUT_XLS = Path("b3_screener.xlsx")
OUTPUT_JSON = Path("valuation_results_combined.json")  # combina ambos para o dashboard


# ─────────────────────────────────────────────────────────────────
def load_results(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def results_to_df(results: dict) -> pd.DataFrame:
    """Converte results dict para DataFrame enriquecido."""
    rows = []
    for nome, r in results.items():
        rows.append({
            "Empresa":         nome,
            "Ticker":          r.get("ticker", "").replace(".SA", ""),
            "Setor":           r.get("setor_raw", r.get("setor", "")),
            "Preço Atual":     r.get("price_now", 0) or 0,
            "Preço Justo":     r.get("price_fair", 0) or 0,
            "Upside %":        (r.get("upside", 0) or 0) * 100,
            "Recomendação":    r.get("recomendacao", ""),
            "EV (R$ bi)":      (r.get("enterprise_value", 0) or 0) / 1e9,
            "Market Cap (bi)": (r.get("wacc_data", {}) or {}).get("market_cap") or 0,
            "Net Debt (bi)":   (r.get("net_debt", 0) or 0) / 1e9,
            "WACC %":          (r.get("wacc", 0) or 0) * 100,
            "Beta":            r.get("beta", 0) or 0,
            "ROIC %":          (r.get("roic", 0) or 0) * 100,
            "ROE %":           (r.get("roe", 0) or 0) * 100,
            "Mg EBIT %":       (r.get("ebit_margin", 0) or 0) * 100,
            "Mg Líquida %":    (r.get("net_margin", 0) or 0) * 100,
            "CAGR Receita %":  (r.get("cagr_revenue", 0) or 0) * 100,
            "EV/EBITDA":       r.get("ev_ebitda", 0) or 0,
            "EV/EBIT":         r.get("ev_ebit", 0) or 0,
            "P/L":             r.get("pe", 0) or 0,
            "EV/Receita":      r.get("ev_revenue", 0) or 0,
        })

    df = pd.DataFrame(rows)

    # Market Cap em bi
    if "Market Cap (bi)" in df.columns:
        df["Market Cap (bi)"] = df["Market Cap (bi)"] / 1e9

    # Limpa outliers de múltiplos (>200x = provavelmente ruído)
    for col in ["EV/EBITDA", "EV/EBIT", "P/L"]:
        if col in df.columns:
            df[col] = df[col].where((df[col] > 0) & (df[col] < 200), other=None)

    return df


def add_score_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score composto (0-100) para ranking qualitativo.
    Combina: upside + ROIC + margem EBIT + CAGR receita
    """
    def zscore(s):
        s = pd.to_numeric(s, errors="coerce")
        std = s.std()
        if std == 0 or pd.isna(std):
            return s * 0
        return (s - s.mean()) / std

    score = (
        zscore(df["Upside %"])       * 0.40 +  # 40% peso no upside
        zscore(df["ROIC %"])         * 0.25 +  # 25% qualidade do capital
        zscore(df["Mg EBIT %"])      * 0.20 +  # 20% eficiência operacional
        zscore(df["CAGR Receita %"]) * 0.15    # 15% crescimento
    )
    # Normaliza para 0-100
    score_min = score.min()
    score_max = score.max()
    if score_max > score_min:
        df["Score"] = ((score - score_min) / (score_max - score_min) * 100).round(1)
    else:
        df["Score"] = 50.0

    return df


# ─────────────────────────────────────────────────────────────────
def build_screener(
    top_n: int = None,
    rec_filter: str = None,
    min_mcap_bi: float = None,
    min_upside: float = None,
) -> pd.DataFrame:
    """Constrói DataFrame do screener com filtros opcionais."""

    results_b3   = load_results(INPUT_B3)
    results_main = load_results(INPUT_MAIN)

    # Combina: resultados manuais têm prioridade (overwrite)
    combined = {**results_b3, **results_main}

    if not combined:
        print("[SCR] Nenhum resultado encontrado. Execute run_b3.py primeiro.")
        return pd.DataFrame()

    print(f"[SCR] {len(combined)} empresas ({len(results_b3)} B3 + {len(results_main)} manual)")

    df = results_to_df(combined)
    df = add_score_column(df)

    # ── Filtros ───────────────────────────────────────────────
    # Remove preço justo zerado (valuation falhou)
    df = df[df["Preço Justo"] > 0].copy()

    # Remove upside absurdo (> 500% = erro de modelo)
    df = df[df["Upside %"].abs() < 500].copy()

    if rec_filter:
        df = df[df["Recomendação"].str.upper() == rec_filter.upper()]

    if min_mcap_bi:
        df = df[df["Market Cap (bi)"] >= min_mcap_bi]

    if min_upside:
        df = df[df["Upside %"] >= min_upside]

    # ── Ordena por Score ──────────────────────────────────────
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)
    df.index += 1  # ranking começa em 1

    if top_n:
        df = df.head(top_n)

    print(f"[SCR] {len(df)} empresas após filtros")

    return df


# ─────────────────────────────────────────────────────────────────
OUTPUT_CSV_DIR = Path("data/screener")

def export_excel(df: pd.DataFrame, path: Path = OUTPUT_XLS):
    """
    Exporta screener em CSVs (sem dependência de openpyxl).
    Tenta Excel se openpyxl estiver disponível, senão usa CSV.
    """
    if df.empty:
        print("[SCR] DataFrame vazio, nada a exportar.")
        return

    # ── Tenta Excel se openpyxl disponível ───────────────────
    try:
        import openpyxl
        path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Screener Completo", index=True)
            df_buy = df[df["Recomendação"].isin(["COMPRA", "COMPRA FORTE"])]
            df_buy.head(20).to_excel(writer, sheet_name="Top 20 Compras", index=True)
            df_sell = df[df["Recomendação"].isin(["VENDA", "VENDA FORTE"])]
            df_sell.head(20).to_excel(writer, sheet_name="Top 20 Vendas", index=True)
            sector_summary = (
                df.groupby("Setor")
                .agg(N=("Ticker","count"), Upside_Medio=("Upside %","mean"),
                     ROIC_Medio=("ROIC %","mean"), Score_Medio=("Score","mean"),
                     Compras=("Recomendação", lambda x: x.isin(["COMPRA","COMPRA FORTE"]).sum()))
                .sort_values("Score_Medio", ascending=False).round(2)
            )
            sector_summary.to_excel(writer, sheet_name="Resumo por Setor", index=True)
        print(f"[SCR] ✅ Excel exportado: {path}")
        return
    except ImportError:
        print("[SCR] openpyxl não instalado — exportando CSVs")

    # ── Fallback: CSV por categoria ───────────────────────────
    OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_CSV_DIR / "screener_completo.csv", index=True)
    print(f"[SCR] ✅ {OUTPUT_CSV_DIR}/screener_completo.csv")

    df_buy = df[df["Recomendação"].isin(["COMPRA", "COMPRA FORTE"])]
    df_buy.head(20).to_csv(OUTPUT_CSV_DIR / "top20_compras.csv", index=True)
    print(f"[SCR] ✅ {OUTPUT_CSV_DIR}/top20_compras.csv")

    df_sell = df[df["Recomendação"].isin(["VENDA", "VENDA FORTE"])]
    df_sell.head(20).to_csv(OUTPUT_CSV_DIR / "top20_vendas.csv", index=True)
    print(f"[SCR] ✅ {OUTPUT_CSV_DIR}/top20_vendas.csv")

    sector_summary = (
        df.groupby("Setor")
        .agg(N=("Ticker","count"), Upside_Medio=("Upside %","mean"),
             ROIC_Medio=("ROIC %","mean"), Score_Medio=("Score","mean"),
             Compras=("Recomendação", lambda x: x.isin(["COMPRA","COMPRA FORTE"]).sum()))
        .sort_values("Score_Medio", ascending=False).round(2)
    )
    sector_summary.to_csv(OUTPUT_CSV_DIR / "resumo_setores.csv", index=True)
    print(f"[SCR] ✅ {OUTPUT_CSV_DIR}/resumo_setores.csv")

    df_large = df[df["Market Cap (bi)"] >= 5]
    if not df_large.empty:
        df_large.to_csv(OUTPUT_CSV_DIR / "large_caps.csv", index=True)
        print(f"[SCR] ✅ {OUTPUT_CSV_DIR}/large_caps.csv")


# ─────────────────────────────────────────────────────────────────
def export_combined_json():
    """
    Gera valuation_results_combined.json para o dashboard.
    Combina cobertura manual (WEG, COGNA) + B3 completa.
    """
    results_b3   = load_results(INPUT_B3)
    results_main = load_results(INPUT_MAIN)
    combined     = {**results_b3, **results_main}

    with open(OUTPUT_JSON, "w") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"[SCR] Combined JSON: {len(combined)} empresas → {OUTPUT_JSON}")


def print_summary(df: pd.DataFrame):
    """Imprime sumário no terminal."""
    if df.empty:
        return

    total     = len(df)
    by_rec    = df["Recomendação"].value_counts()
    avg_up    = df["Upside %"].mean()
    median_up = df["Upside %"].median()

    print("\n" + "═" * 65)
    print(f"  B3 SCREENER — {total} empresas valuadas")
    print("═" * 65)
    print(f"\n  Upside médio  : {avg_up:+.1f}%")
    print(f"  Upside mediana: {median_up:+.1f}%")
    print(f"\n  Distribuição de recomendações:")
    for rec, count in by_rec.items():
        pct = count / total * 100
        bar = "█" * int(pct / 3)
        print(f"    {rec:15s}: {count:4d} ({pct:.0f}%) {bar}")

    print(f"\n  Top 10 por Score:")
    top10_cols = ["Empresa", "Ticker", "Upside %", "Recomendação", "ROIC %", "Score"]
    top10_cols_present = [c for c in top10_cols if c in df.columns]
    print(df[top10_cols_present].head(10).to_string(index=True))
    print("═" * 65 + "\n")


# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="B3 Screener")
    parser.add_argument("--top",     type=int,   default=None)
    parser.add_argument("--rec",     type=str,   default=None,
                        help="Ex: 'COMPRA FORTE'")
    parser.add_argument("--min-mcap",type=float, default=None,
                        help="Mínimo market cap em bilhões")
    parser.add_argument("--min-up",  type=float, default=None,
                        help="Mínimo upside em % (ex: 20)")
    parser.add_argument("--no-excel", action="store_true")
    args = parser.parse_args()

    df = build_screener(
        top_n=args.top,
        rec_filter=args.rec,
        min_mcap_bi=args.min_mcap,
        min_upside=args.min_up,
    )

    print_summary(df)

    if not args.no_excel:
        export_excel(df)

    export_combined_json()