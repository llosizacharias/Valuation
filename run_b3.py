"""
run_b3.py
─────────────────────────────────────────────────────────────────
Entrypoint único para o pipeline completo de valuation B3.

Etapas:
  1. CATALOG   — cataloga todas as empresas B3 (CVM + B3 API)
  2. PREFETCH  — baixa ZIPs da CVM e pré-extrai dados (6 anos)
  3. VALUATION — roda FCFF/WACC/DCF em paralelo para cada empresa
  4. SCREENER  — gera rankings, Excel e JSON combinado

Uso rápido:
  python run_b3.py                  # pipeline completo (pode levar 2-4h)
  python run_b3.py --test 20        # teste com 20 empresas (~10min)
  python run_b3.py --step catalog   # só reconstrói o catálogo
  python run_b3.py --step prefetch  # só baixa/extrai ZIPs
  python run_b3.py --step valuation # só roda os valuations
  python run_b3.py --step screener  # só gera o screener

Flags:
  --workers N     Workers paralelos para valuation (default: 3)
  --no-resume     Começa do zero (ignora checkpoint)
  --sector NOME   Valida só um setor específico
  --test N        Limita a N empresas
  --force-catalog Reconstrói catálogo mesmo se cache existir

Tempo estimado (VPS 2-core / 4GB RAM):
  Catálogo  : ~5min  (inclui yfinance shares para ~350 empresas)
  Prefetch  : ~45min (6 ZIPs de ~150MB cada = ~900MB total)
  Valuation : ~3-5h  (350 empresas × ~40s cada / 3 workers)
  Screener  : ~1min
  ─────────────────────────────────────────────────────────
  TOTAL     : ~4-6h primeira execução
  Próximas  : ~3-4h (ZIPs já em cache, catálogo atualizado)
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path


def step_catalog(args):
    print("\n" + "═" * 60)
    print("  STEP 1/4 — CATALOG")
    print("  Catalogando empresas B3...")
    print("═" * 60)
    from b3_catalog import build_catalog
    catalog = build_catalog(
        force_refresh=args.force_catalog,
        
        max_companies=args.test,
    )
    print(f"\n✅ Catálogo: {len(catalog)} empresas")
    return catalog


def step_prefetch(args):
    print("\n" + "═" * 60)
    print("  STEP 2/4 — PREFETCH")
    print("  Baixando ZIPs CVM e pré-extraindo dados...")
    print("═" * 60)
    from b3_data_prefetch import download_zips, extract_all_companies, DEFAULT_YEARS

    years = DEFAULT_YEARS
    zip_paths = download_zips(years)
    if not zip_paths:
        print("❌ Nenhum ZIP disponível — verifique conexão com a internet")
        return False

    extract_all_companies(zip_paths, save_cache=True)
    print(f"\n✅ Prefetch concluído: {len(zip_paths)} anos")
    return True


def step_valuation(args):
    print("\n" + "═" * 60)
    print("  STEP 3/4 — VALUATION")
    print(f"  Rodando DCF para toda a B3 ({args.workers} workers)...")
    print("═" * 60)
    from b3_runner import run_b3

    results = run_b3(
        workers=args.workers,
        resume=args.resume,
        sector_filter=args.sector,
        test_limit=args.test,
    )
    print(f"\n✅ Valuation: {len(results)} empresas processadas")
    return results


def step_screener(args):
    print("\n" + "═" * 60)
    print("  STEP 4/4 — SCREENER")
    print("  Gerando rankings e exportando Excel...")
    print("═" * 60)
    from b3_screener import build_screener, export_excel, export_combined_json, print_summary

    df = build_screener()
    print_summary(df)
    export_excel(df)
    export_combined_json()
    print(f"\n✅ Screener: {len(df)} empresas ranqueadas")
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline B3 Completo — Valuation de todas as empresas listadas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--step", choices=["catalog", "prefetch", "valuation", "screener"],
                        default=None, help="Executa apenas uma etapa específica")
    parser.add_argument("--workers",       type=int,  default=3)
    parser.add_argument("--no-resume",     dest="resume", action="store_false", default=True)
    parser.add_argument("--sector",        type=str,  default=None)
    parser.add_argument("--test",          type=int,  default=None,
                        help="Testa com N empresas (ex: --test 10)")
    parser.add_argument("--force-catalog", action="store_true", default=False,
                        help="Reconstrói catálogo mesmo que cache exista")
    args = parser.parse_args()

    t0 = time.time()
    print(f"\n{'═'*60}")
    print(f"  🚀 B3 PIPELINE — {datetime.now():%Y-%m-%d %H:%M}")
    if args.test:
        print(f"  ⚠️  MODO TESTE: limitado a {args.test} empresas")
    if args.sector:
        print(f"  🔍 Filtro setor: {args.sector}")
    print(f"{'═'*60}\n")

    # ── Executa etapa específica ou pipeline completo ─────────
    if args.step:
        steps_map = {
            "catalog":   step_catalog,
            "prefetch":  step_prefetch,
            "valuation": step_valuation,
            "screener":  step_screener,
        }
        steps_map[args.step](args)
    else:
        # Pipeline completo
        step_catalog(args)
        ok = step_prefetch(args)
        if not ok:
            print("\n❌ Prefetch falhou. Pipeline interrompido.")
            sys.exit(1)
        step_valuation(args)
        step_screener(args)

    elapsed = time.time() - t0
    print(f"\n{'═'*60}")
    print(f"  ✅ Pipeline concluído em {elapsed/60:.1f} minutos")
    print(f"{'═'*60}\n")

    print("Próximos passos:")
    print("  1. Copiar valuation_results_b3.json para o VPS:")
    print("     scp valuation_results_b3.json root@187.77.52.223:/opt/shipyard/")
    print("  2. Reiniciar o dashboard:")
    print("     systemctl restart shipyard-dashboard")
    print("  3. Acessar a aba 'Screener B3' no dashboard")


if __name__ == "__main__":
    main()