from app.deterministic_runner import run_deterministic_valuation
from app.stochastic_runner import run_stochastic_single

MODE = "deterministic"  # ou "stochastic"
FILE_PATH = "empresa_teste.xlsx"

if MODE == "deterministic":
    run_deterministic_valuation(FILE_PATH)

elif MODE == "stochastic":
    run_stochastic_single()