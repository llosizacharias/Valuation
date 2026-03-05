"""
Factor Engine
Gera trajetórias de fatores macroeconômicos correlacionados
usando decomposição de Cholesky, regime a regime.

Fatores: [PIB, JUROS, COMMODITIES, CAMBIO]
"""

import numpy as np

from .parameters import (
    TIME_HORIZON,
    FACTOR_MEANS_NORMAL,
    FACTOR_STDS_NORMAL,
    FACTOR_MEANS_STRESS,
    FACTOR_STDS_STRESS,
    CORRELATION_MATRIX_NORMAL,
    CORRELATION_MATRIX_STRESS,
    REGIME_NORMAL,
)


class FactorEngine:

    def __init__(self):
        # Pré-calcula Cholesky para cada regime — evita recalcular a cada simulação
        self._chol_normal = np.linalg.cholesky(CORRELATION_MATRIX_NORMAL)
        self._chol_stress = np.linalg.cholesky(CORRELATION_MATRIX_STRESS)

    # ============================================================
    # Gera fatores para um único período dado o regime
    # ============================================================

    def _sample_factors(self, regime: int) -> np.ndarray:
        """
        Retorna array de 4 fatores correlacionados para um período.
        """
        z = np.random.standard_normal(4)

        if regime == REGIME_NORMAL:
            chol = self._chol_normal
            means = FACTOR_MEANS_NORMAL
            stds = FACTOR_STDS_NORMAL
        else:
            chol = self._chol_stress
            means = FACTOR_MEANS_STRESS
            stds = FACTOR_STDS_STRESS

        # Aplica correlação via Cholesky e escala
        correlated = chol @ z
        return means + stds * correlated

    # ============================================================
    # Gera uma trajetória de fatores (TIME_HORIZON períodos)
    # ============================================================

    def generate_path(self, regime_path: np.ndarray) -> np.ndarray:
        """
        regime_path: array de tamanho TIME_HORIZON com regime por período.
        Retorna matriz (TIME_HORIZON x 4).
        """
        factors = np.zeros((TIME_HORIZON, 4))

        for t in range(TIME_HORIZON):
            factors[t] = self._sample_factors(regime_path[t])

        return factors

    # ============================================================
    # Gera múltiplas trajetórias
    # ============================================================

    def generate_multiple_paths(self, regime_paths: np.ndarray) -> np.ndarray:
        """
        regime_paths: matriz (n_simulations x TIME_HORIZON).
        Retorna tensor (n_simulations x TIME_HORIZON x 4).
        """
        n_simulations = regime_paths.shape[0]
        factor_tensor = np.zeros((n_simulations, TIME_HORIZON, 4))

        for i in range(n_simulations):
            factor_tensor[i] = self.generate_path(regime_paths[i])

        return factor_tensor
