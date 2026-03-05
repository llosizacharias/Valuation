"""
Monte Carlo Engine
Orquestra todo o motor macro-estrutural:
Regimes -> Fatores -> Crédito -> DCF Estocástico
"""

import numpy as np

from .parameters import (
    N_SIMULATIONS_DEFAULT,
    REGIME_NORMAL,
)
from .regime_engine import RegimeEngine
from .factor_engine import FactorEngine
from .credit_model import CreditModel
from .stochastic_dcf import StochasticDCF


class MonteCarloEngine:

    def __init__(self, company, n_simulations=N_SIMULATIONS_DEFAULT):
        self.company = company
        self.n_simulations = n_simulations

        self.regime_engine = RegimeEngine()
        self.factor_engine = FactorEngine()
        self.credit_model = CreditModel()
        self.dcf_engine = StochasticDCF(company)

    # ============================================================
    # Executa simulação completa
    # ============================================================

    def run(self):

        results = np.zeros(self.n_simulations)

        # 1️⃣ Simular regimes
        regime_paths = self.regime_engine.simulate_multiple_paths(
            self.n_simulations,
            initial_regime=REGIME_NORMAL
        )

        # 2️⃣ Gerar fatores correlacionados
        factor_tensor = self.factor_engine.generate_multiple_paths(
            regime_paths
        )

        # 3️⃣ Gerar crédito derivado
        credit_tensor = self.credit_model.compute_multiple_paths(
            factor_tensor,
            regime_paths
        )

        # 4️⃣ Rodar DCF estocástico para cada simulação
        for i in range(self.n_simulations):
            results[i] = self.dcf_engine.run_single_path(
                factor_tensor[i],
                credit_tensor[i]
            )

        return results

    # ============================================================
    # Estatísticas básicas
    # ============================================================

    def summary_statistics(self, results):

        mean = np.mean(results)
        std = np.std(results)
        p5 = np.percentile(results, 5)
        p50 = np.percentile(results, 50)
        p95 = np.percentile(results, 95)

        prob_negative = np.mean(results < 0)

        return {
            "mean": mean,
            "std": std,
            "p5": p5,
            "median": p50,
            "p95": p95,
            "prob_negative": prob_negative
        }

    # ============================================================
    # CVaR estrutural (cauda esquerda)
    # ============================================================

    def cvar(self, results, alpha=5):
        threshold = np.percentile(results, alpha)
        tail_losses = results[results <= threshold]
        if len(tail_losses) == 0:
            return threshold
        return np.mean(tail_losses)