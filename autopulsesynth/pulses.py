"""Pulse parameterizations and waveform generators.

Defines the Gaussian-DRAG pulse family with hardware bounds.
Parameters: [A, t0, sigma, phi, beta]
Constraints: |Ω| <= amp_max, sigma >= sigma_min
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict
import numpy as np
from scipy.ndimage import gaussian_filter1d


def _gaussian(t: np.ndarray, t0: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((t - t0) / sigma) ** 2)


def _gaussian_derivative(t: np.ndarray, t0: float, sigma: float) -> np.ndarray:
    # d/dt exp(-(t-t0)^2/(2 sigma^2)) = -(t-t0)/sigma^2 * exp(...)
    g = _gaussian(t, t0, sigma)
    return -((t - t0) / (sigma ** 2)) * g


def clip_and_smooth(wave: np.ndarray, amp_max: float, smooth_sigma_pts: float = 0.0) -> np.ndarray:
    """Apply hard clipping and optional Gaussian smoothing in sample index space."""
    w = np.clip(wave, -amp_max, amp_max)
    if smooth_sigma_pts and smooth_sigma_pts > 0:
        w = gaussian_filter1d(w, sigma=smooth_sigma_pts, mode="nearest")
        w = np.clip(w, -amp_max, amp_max)
    return w


@dataclass
class GaussianDragPulse:
    duration: float
    n_steps: int
    amp_max: float
    sigma_min: float

    def time_grid(self) -> np.ndarray:
        return np.linspace(0.0, self.duration, self.n_steps, endpoint=False)

    def param_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        # A, t0, sigma, phi, beta
        # Restriction: beta should be perturbative [-0.2, 0.2] to avoid geometric phase artifacts
        lo = np.array([0.0, 0.0, self.sigma_min, -np.pi, -0.2], dtype=float)
        hi = np.array([self.amp_max, self.duration, 0.5 * self.duration, np.pi, 0.2], dtype=float)
        return lo, hi

    def sample_controls(self, params: np.ndarray, smooth_sigma_pts: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        A, t0, sigma, phi, beta = [float(x) for x in params]
        sigma = max(sigma, self.sigma_min)
        t = self.time_grid()
        g = _gaussian(t, t0, sigma)
        gp = _gaussian_derivative(t, t0, sigma)

        ox = A * g * np.cos(phi) - A * beta * (gp * sigma) * np.sin(phi)
        oy = A * g * np.sin(phi) + A * beta * (gp * sigma) * np.cos(phi)

        ox = clip_and_smooth(ox, self.amp_max, smooth_sigma_pts=smooth_sigma_pts)
        oy = clip_and_smooth(oy, self.amp_max, smooth_sigma_pts=smooth_sigma_pts)
        return ox, oy

    def to_feature_vector(self, params: np.ndarray) -> np.ndarray:
        """Feature map for surrogate modeling (simple, stable)."""
        # Keep raw params plus a few derived features that help learning.
        A, t0, sigma, phi, beta = params.astype(float)
        return np.array([
            A,
            t0 / self.duration,
            sigma / self.duration,
            np.sin(phi),
            np.cos(phi),
            beta,
            A * beta,
        ], dtype=float)

    def to_dict(self, params: np.ndarray) -> Dict[str, float]:
        A, t0, sigma, phi, beta = [float(x) for x in params]
        return {"A": A, "t0": t0, "sigma": sigma, "phi": phi, "beta": beta,
                "duration": float(self.duration), "n_steps": int(self.n_steps),
                "amp_max": float(self.amp_max), "sigma_min": float(self.sigma_min)}
