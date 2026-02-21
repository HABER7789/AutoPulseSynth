"""Surrogate-assisted uncertainty-aware optimization.

Workflow:
1) Generate dataset of (pulse_params, theta) -> fidelity via full simulation.
2) Train a surrogate model to predict fidelity from features.
3) Use the surrogate to optimize pulse parameters for performance under parameter variation across theta,
   then verify in full simulator.

This is not a replacement for GRAPE/Krotov. It is a research-grade baseline
for ML-assisted search, emphasizing reproducibility and physically-fixed models.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Tuple, Dict, Optional
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.optimize import differential_evolution

from .model import QubitHamiltonianModel, UncertaintyModel
from .pulses import GaussianDragPulse
from .simulate import simulate_evolution, fidelity_metric, target_unitary
from .ir import PulseIR


@dataclass
class SurrogateDataset:
    X: np.ndarray  # features
    y: np.ndarray  # fidelity
    meta: Dict[str, np.ndarray]  # raw params, theta

    @staticmethod
    def build(
        pulse_family: GaussianDragPulse,
        model: QubitHamiltonianModel,
        uncertainty: UncertaintyModel,
        target_ir: PulseIR,
        n_pulses: int,
        n_theta: int,
        rng_seed: int = 0,
        smooth_sigma_pts: float = 0.0,
    ) -> "SurrogateDataset":
        rng = np.random.default_rng(rng_seed)
        theta_samples = uncertainty.sample(n_theta)
        lo, hi = pulse_family.param_bounds()

        feats = []
        ys = []
        params_list = []
        theta_list = []
        V = target_ir.unitary_matrix

        for _ in range(n_pulses):
            params = rng.uniform(lo, hi)
            # simulate across multiple theta values (batched)
            ox, oy = pulse_family.sample_controls(params, smooth_sigma_pts=smooth_sigma_pts)
            for th in theta_samples:
                res = simulate_evolution(model, pulse_family.duration, ox, oy, th)
                f = fidelity_metric(res, V)
                # features include pulse + theta
                x = np.concatenate([pulse_family.to_feature_vector(params), th.astype(float)], axis=0)
                feats.append(x)
                ys.append(f)
                params_list.append(params.copy())
                theta_list.append(th.copy())

        X = np.vstack(feats).astype(float)
        y = np.array(ys, dtype=float)
        meta = {"pulse_params": np.vstack(params_list), "theta": np.vstack(theta_list)}
        return SurrogateDataset(X=X, y=y, meta=meta)


def train_surrogate(
    dataset: SurrogateDataset,
    rng_seed: int = 0,
) -> Tuple[RandomForestRegressor, Dict[str, float]]:
    """Train a surrogate model and return metrics on a held-out test set."""
    X_train, X_test, y_train, y_test = train_test_split(
        dataset.X, dataset.y, test_size=0.2, random_state=rng_seed
    )
    model = RandomForestRegressor(
        n_estimators=400,
        random_state=rng_seed,
        min_samples_leaf=2,
        n_jobs=1,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    metrics = {
        "mae": float(mean_absolute_error(y_test, pred)),
        "r2": float(r2_score(y_test, pred)),
        "y_test_mean": float(np.mean(y_test)),
    }
    return model, metrics


def _uncertainty_objective_from_surrogate(
    pulse_family: GaussianDragPulse,
    surrogate: RandomForestRegressor,
    theta_eval: np.ndarray,
    mode: str,
    target_ir: PulseIR,
) -> Callable[[np.ndarray], float]:
    mode = mode.lower()
    if mode not in ("worst", "mean"):
        raise ValueError("mode must be 'worst' or 'mean'")

    def obj(params: np.ndarray) -> float:
        # penalty if out of bounds
        lo, hi = pulse_family.param_bounds()
        if np.any(params < lo) or np.any(params > hi):
            return 10.0  # large loss
        
        # 1. Prediction from surrogate
        feats_p = pulse_family.to_feature_vector(params)
        X = np.hstack([np.repeat(feats_p[None, :], len(theta_eval), axis=0), theta_eval])
        f_pred = surrogate.predict(X)
        f_val = np.min(f_pred) if mode == "worst" else np.mean(f_pred)
        
        # 2. Physics-informed regularization (prevent 7pi pulses or wrong axes)
        # Approximate Gaussian area: A * sigma * sqrt(2pi)
        # This ignores DRAG and truncation, but is a strong guide for the "main" lobe.
        A, t0, sigma, phi, beta = params
        area = A * sigma * np.sqrt(2 * np.pi)
        
        # Target angle for X/Y/etc (assumed Pi for now for X)
        target_area = np.pi
        if target_ir.gate_name.startswith("S"): # SX, SQRTX
            target_area = np.pi / 2.0
            
        area_penalty = 2.0 * (area - target_area)**2
        
        # 3. Soft constraint on Phase (Axis Alignment)
        # For X-type gates (X, SX), we want phi ~ 0 or pi.
        # Ideally phi=0 means drive is along X.
        # phi=pi means drive is along -X. Both are fine for "X gate" up to global phase?
        # phase_penalty = 0.0
        phase_penalty = 0.0
        if target_ir.gate_name in ("X", "SX", "SQRTX", "SQRX"):
             # Penalize y-component of the main Gaussian drive
             phase_penalty = 5.0 * np.sin(phi)**2
        
        return float(1.0 - f_val + area_penalty + phase_penalty)
    return obj


def optimize_under_uncertainty(
    pulse_family: GaussianDragPulse,
    surrogate: RandomForestRegressor,
    uncertainty: UncertaintyModel,
    mode: str = "worst",
    target_ir: PulseIR = None,
    n_theta_eval: int = 64,
    rng_seed: int = 1,
) -> Dict[str, object]:
    """Optimize pulse parameters on surrogate, return best params and predicted fidelity."""
    rng = np.random.default_rng(rng_seed)
    theta_eval = uncertainty.sample(n_theta_eval)

    lo, hi = pulse_family.param_bounds()
    bounds = list(zip(lo.tolist(), hi.tolist()))
    obj = _uncertainty_objective_from_surrogate(pulse_family, surrogate, theta_eval, mode=mode, target_ir=target_ir)

    result = differential_evolution(
    obj,
    bounds=bounds,
    seed=rng_seed,
    maxiter=120,
    popsize=18,
    polish=True,
    tol=1e-4,
    updating="immediate",
    workers=1,  # <- important: avoid multiprocessing pickling
    )
    
    best_params = result.x.astype(float)
    # predicted uncertainty-aware fidelity
    feats_p = pulse_family.to_feature_vector(best_params)
    X = np.hstack([np.repeat(feats_p[None, :], len(theta_eval), axis=0), theta_eval])
    f_pred = surrogate.predict(X)
    summary = {
        "best_params": best_params,
        "pred_f_mean": float(np.mean(f_pred)),
        "pred_f_worst": float(np.min(f_pred)),
        "opt_result": result,
        "theta_eval": theta_eval,
    }
    return summary


def verify_in_simulator(
    model: QubitHamiltonianModel,
    pulse_family: GaussianDragPulse,
    params: np.ndarray,
    uncertainty: UncertaintyModel,
    target_ir: PulseIR,
    n_theta: int = 200,
    rng_seed: int = 2,
    smooth_sigma_pts: float = 0.0,
) -> Dict[str, object]:
    """Full-simulator verification for a pulse across sampled θ."""
    theta = uncertainty.sample(n_theta)
    V = target_ir.unitary_matrix
    ox, oy = pulse_family.sample_controls(params, smooth_sigma_pts=smooth_sigma_pts)
    fs = []
    for th in theta:
        res = simulate_evolution(model, pulse_family.duration, ox, oy, th)
        fs.append(fidelity_metric(res, V))
    fs = np.array(fs, dtype=float)
    return {
        "f_mean": float(np.mean(fs)),
        "f_worst": float(np.min(fs)),
        "f_std": float(np.std(fs)),
        "f_samples": fs,
        "theta": theta,
    }
