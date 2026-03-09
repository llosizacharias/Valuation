from app.deterministic_runner import run_deterministic_valuation
from app.stochastic_runner import run_stochastic_single

# ✅ MELHORIA: Constantes no topo para fácil configuração
MODE = "deterministic"  # Opções: "deterministic" ou "stochastic"
FILE_PATH = "empresa_teste.xlsx"

# ✅ CORREÇÃO BUG #2: Proteção de execução
# Sem isso, qualquer arquivo que importar o main.py rodaria o valuation automaticamente
if __name__ == "__main__":
    if MODE == "deterministic":
        run_deterministic_valuation(FILE_PATH)

    elif MODE == "stochastic":
        run_stochastic_single()

    else:
        print(f"❌ Modo inválido: '{MODE}'. Use 'deterministic' ou 'stochastic'.")
