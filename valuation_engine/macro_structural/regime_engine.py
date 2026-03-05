"""
Regime Engine
Responsável por simular regimes macroeconômicos anuais
via cadeia de Markov.

Regimes:
0 = Normal
1 = Stress
"""

import numpy as np
from .parameters import (
    REGIME_TRANSITION_MATRIX,
    REGIME_NORMAL,
    REGIME_STRESS,
    TIME_HORIZON,
)


class RegimeEngine:
    def __init__(self, transition_matrix=None, time_horizon=None):
        self.transition_matrix = (
            transition_matrix if transition_matrix is not None
            else REGIME_TRANSITION_MATRIX
        )
        self.time_horizon = (
            time_horizon if time_horizon is not None
            else TIME_HORIZON
        )

        self._validate_transition_matrix()

    def _validate_transition_matrix(self):
        if self.transition_matrix.shape != (2, 2):
            raise ValueError("A matriz de transição deve ser 2x2.")

        row_sums = self.transition_matrix.sum(axis=1)
        if not np.allclose(row_sums, 1.0):
            raise ValueError("Cada linha da matriz de transição deve somar 1.")

    def simulate_path(self, initial_regime=REGIME_NORMAL):
        """
        Simula uma única trajetória de regimes ao longo do horizonte.
        Retorna array de tamanho TIME_HORIZON.
        """
        regimes = np.zeros(self.time_horizon, dtype=int)
        regimes[0] = initial_regime

        for t in range(1, self.time_horizon):
            current_regime = regimes[t - 1]
            transition_probs = self.transition_matrix[current_regime]
            regimes[t] = np.random.choice(
                [REGIME_NORMAL, REGIME_STRESS],
                p=transition_probs
            )

        return regimes

    def simulate_multiple_paths(self, n_simulations, initial_regime=REGIME_NORMAL):
        """
        Simula múltiplas trajetórias.
        Retorna matriz (n_simulations x TIME_HORIZON)
        """
        paths = np.zeros((n_simulations, self.time_horizon), dtype=int)

        for i in range(n_simulations):
            paths[i] = self.simulate_path(initial_regime)

        return paths

    def expected_stress_duration(self):
        """
        Retorna duração média teórica do regime de stress
        baseada na probabilidade de permanência.
        """
        p_stress_stay = self.transition_matrix[REGIME_STRESS, REGIME_STRESS]
        if p_stress_stay >= 1:
            return np.inf
        return 1 / (1 - p_stress_stay)

    def stationary_distribution(self):
        """
        Calcula distribuição estacionária da cadeia de Markov.
        """
        A = self.transition_matrix.T - np.eye(2)
        A = np.vstack([A, np.ones(2)])
        b = np.array([0, 0, 1])

        solution = np.linalg.lstsq(A, b, rcond=None)[0]
        return solution