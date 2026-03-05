"""
Portfolio Engine
Simula carteira estrutural usando o mesmo ambiente macro
para todas as empresas.
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


class PortfolioEngine:

    def __init__(self, companies, weights, n_simulations=N_SIMULATIONS_DEFAULT):

        if len(companies) != len(weights):
            raise ValueError("Número de empresas deve ser igual ao número de pesos.")

        self.companies = companies
        self.weights = np.array(weights)

        # Normaliza pesos
        self.weights = self.weights / np.sum(self.weights)

        self.n_simulations = n_simulations

        self.regime_engine = RegimeEngine()
        self.factor_engine = FactorEngine()
        self.credit_model = CreditModel()

    # ============================================================
    # Simulação principal da carteira
    # ============================================================

    def run(self):

        n_assets = len(self.companies)
        results_portfolio = np.zeros(self.n_simulations)
        results_assets = np.zeros((self.n_simulations, n_assets))

        # 1️⃣ Simula regimes
        regime_paths = self.regime_engine.simulate_multiple_paths(
            self.n_simulations,
            initial_regime=REGIME_NORMAL
        )

        # 2️⃣ Gera fatores macro
        factor_tensor = self.factor_engine.generate_multiple_paths(
            regime_paths
        )

        # 3️⃣ Gera crédito derivado
        credit_tensor = self.credit_model.compute_multiple_paths(
            factor_tensor,
            regime_paths
        )

        # 4️⃣ Para cada simulação, calcula retorno de cada ativo
        for i in range(self.n_simulations):

            asset_returns = np.zeros(n_assets)

            for j, company in enumerate(self.companies):

                dcf_engine = StochasticDCF(company)

                asset_returns[j] = dcf_engine.run_single_path(
                    factor_tensor[i],
                    credit_tensor[i]
                )

            results_assets[i] = asset_returns

            # 5️⃣ Retorno da carteira
            results_portfolio[i] = np.dot(self.weights, asset_returns)

        return results_portfolio, results_assets

    # ============================================================
    # Estatísticas da carteira
    # ============================================================

    def summary_statistics(self, portfolio_returns):

        mean = np.mean(portfolio_returns)
        std = np.std(portfolio_returns)
        p5 = np.percentile(portfolio_returns, 5)
        p50 = np.percentile(portfolio_returns, 50)
        p95 = np.percentile(portfolio_returns, 95)
        prob_negative = np.mean(portfolio_returns < 0)

        return {
            "mean": mean,
            "std": std,
            "p5": p5,
            "median": p50,
            "p95": p95,
            "prob_negative": prob_negative
        }

    # ============================================================
    # CVaR da carteira
    # ============================================================

    def cvar(self, portfolio_returns, alpha=5):

        threshold = np.percentile(portfolio_returns, alpha)
        tail = portfolio_returns[portfolio_returns <= threshold]

        if len(tail) == 0:
            return threshold

        return np.mean(tail)

    # ============================================================
    # Contribuição marginal ao risco (simples)
    # ============================================================

    def marginal_risk_contribution(self, asset_returns):

        """
        asset_returns: matriz (n_sim x n_assets)
        Retorna contribuição percentual para variância.
        """

        cov_matrix = np.cov(asset_returns.T)
        portfolio_variance = np.dot(
            self.weights,
            np.dot(cov_matrix, self.weights)
        )

        marginal_contrib = np.dot(cov_matrix, self.weights)

        contrib = self.weights * marginal_contrib / portfolio_variance

        return contrib