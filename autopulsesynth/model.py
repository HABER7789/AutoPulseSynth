"""Physical model: fixed Hamiltonian structure with parameter uncertainty.

We intentionally *do not* learn arbitrary Hamiltonians. The Hamiltonian structure is:

H(t) = (Δ/2) σ_z + (Ω_x(t)/2) σ_x + (Ω_y(t)/2) σ_y

where:
- Δ is the (possibly uncertain) detuning in rad/s (drift term)
- Ω_x(t), Ω_y(t) are control drives in rad/s (time-dependent)

The parameter vector θ captures imperfect knowledge / calibration:
θ = [detuning, amp_scale, phase_skew, noise_strength]

- detuning: additive detuning Δ (rad/s)
- amp_scale: multiplicative scale error on both quadratures (dimensionless)
- phase_skew: small quadrature mixing (dimensionless, e.g., IQ imbalance)
- noise_strength: optional quasi-static detuning noise std (rad/s)

Notes:
- We keep the structure fixed and only vary parameters.
- We model performance under parameter variation by sampling θ and optimizing average or worst-case fidelity.

Units:
- Time in seconds
- Frequencies in rad/s
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple
import numpy as np

SIGMA_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
SIGMA_Y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=complex)
SIGMA_Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
IDENTITY_2 = np.eye(2, dtype=complex)


@dataclass(frozen=True)
class QubitHamiltonianModel:
    """Fixed single-qubit Hamiltonian structure.

    This object provides the drift and control operators (Pauli matrices).
    Parameters (θ) are applied externally (in simulate.py) so we can handle
    uncertainty consistently.
    """
    # no learned structure; these are fixed
    sigma_x: np.ndarray = field(default_factory=lambda: SIGMA_X.copy())
    sigma_y: np.ndarray = field(default_factory=lambda: SIGMA_Y.copy())
    sigma_z: np.ndarray = field(default_factory=lambda: SIGMA_Z.copy())

    def operators(self) -> Dict[str, np.ndarray]:
        return {"sx": self.sigma_x, "sy": self.sigma_y, "sz": self.sigma_z}


@dataclass(frozen=True)
class UncertaintyModel:
    """Distribution over θ capturing parameter uncertainty.

    We use a simple bounded sampling model, which is easy to reproduce:
    - detuning ~ Uniform[detuning_min, detuning_max]
    - amp_scale ~ Uniform[scale_min, scale_max]
    - phase_skew ~ Uniform[skew_min, skew_max]
    - noise_strength ~ Uniform[noise_min, noise_max] (quasi-static detuning noise)

    The noise_strength here is a *standard deviation* for an additional
    detuning term per simulation (quasi-static during the pulse).
    """

    detuning_min: float
    detuning_max: float
    scale_min: float
    scale_max: float
    skew_min: float = -0.02
    skew_max: float = 0.02
    noise_min: float = 0.0
    noise_max: float = 0.0
    rng_seed: int = 0

    def sample(self, n: int) -> np.ndarray:
        rng = np.random.default_rng(self.rng_seed)
        det = rng.uniform(self.detuning_min, self.detuning_max, size=n)
        scale = rng.uniform(self.scale_min, self.scale_max, size=n)
        skew = rng.uniform(self.skew_min, self.skew_max, size=n)
        noise = rng.uniform(self.noise_min, self.noise_max, size=n)
        return np.stack([det, scale, skew, noise], axis=1)

    def nominal(self) -> np.ndarray:
        return np.array([
            0.5 * (self.detuning_min + self.detuning_max),
            0.5 * (self.scale_min + self.scale_max),
            0.5 * (self.skew_min + self.skew_max),
            0.5 * (self.noise_min + self.noise_max),
        ], dtype=float)

    @staticmethod
    def theta_to_dict(theta: np.ndarray) -> Dict[str, float]:
        return {
            "detuning": float(theta[0]),
            "amp_scale": float(theta[1]),
            "phase_skew": float(theta[2]),
            "noise_strength": float(theta[3]),
        }

    @staticmethod
    def bounds_from_nominal(nominal: np.ndarray, deltas: Tuple[float, float, float, float]) -> Tuple[np.ndarray, np.ndarray]:
        lo = nominal - np.array(deltas, dtype=float)
        hi = nominal + np.array(deltas, dtype=float)
        return lo, hi
