"""Simulation and fidelity utilities.

Primary backend: **QuTiP** (if installed).
Fallback backend: **NumPy/SciPy** piecewise-constant propagator.

We use QuTiP because it is widely used for time-dependent Hamiltonians and makes it
easy to extend this baseline to open-system dynamics later. The fallback exists
so the notebook can still run in minimal environments.

Hamiltonian (fixed structure):
H(t) = (Δ_total/2) σ_z + (s * Ωx(t)/2) σ_x + (s * Ωy_eff(t)/2) σ_y

Uncertainty θ = [detuning, amp_scale, phase_skew, noise_strength]
- Δ_total = detuning + quasi-static noise draw
- s = amp_scale
- Ωy_eff = Ωy + phase_skew * Ωx  (simple IQ imbalance model)

Average gate fidelity for d=2:
F_avg(U, V) = (|Tr(V^† U)|^2 + d) / (d(d+1))
"""

from __future__ import annotations
import numpy as np
from scipy.linalg import expm

try:
    import qutip as qt
except Exception:  # pragma: no cover
    qt = None

from .model import QubitHamiltonianModel


def _apply_uncertainty(ox: np.ndarray, oy: np.ndarray, theta: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    detuning, amp_scale, phase_skew, noise_strength = [float(x) for x in theta]
    # Quasi-static detuning noise draw (fixed seed for reproducibility inside a run)
    rng = np.random.default_rng(12345)
    det_noise = rng.normal(0.0, noise_strength) if noise_strength > 0 else 0.0
    delta = detuning + det_noise

    ox_eff = amp_scale * ox
    oy_eff = amp_scale * (oy + phase_skew * ox)
    return delta, ox_eff, oy_eff


def _piecewise_unitary_numpy(
    model: QubitHamiltonianModel,
    duration: float,
    ox: np.ndarray,
    oy: np.ndarray,
    theta: np.ndarray,
) -> np.ndarray:
    """NumPy/SciPy fallback propagator for piecewise-constant Hamiltonian."""
    n_steps = len(ox)
    dt = duration / n_steps
    delta, ox_eff, oy_eff = _apply_uncertainty(ox, oy, theta)

    sx = model.sigma_x
    sy = model.sigma_y
    sz = model.sigma_z

    U = np.eye(2, dtype=complex)
    for k in range(n_steps):
        Hk = 0.5 * delta * sz + 0.5 * ox_eff[k] * sx + 0.5 * oy_eff[k] * sy
        U = expm(-1j * Hk * dt) @ U
    return U


def _piecewise_unitary_qutip(
    model: QubitHamiltonianModel,
    duration: float,
    ox: np.ndarray,
    oy: np.ndarray,
    theta: np.ndarray,
) -> np.ndarray:
    """QuTiP-based unitary simulation using sesolve on basis states."""
    n_steps = len(ox)
    dt = duration / n_steps
    delta, ox_eff, oy_eff = _apply_uncertainty(ox, oy, theta)

    sx = qt.Qobj(model.sigma_x)
    sy = qt.Qobj(model.sigma_y)
    sz = qt.Qobj(model.sigma_z)

    def _idx(t: float) -> int:
        i = int(np.floor(t / dt))
        return min(max(i, 0), n_steps - 1)

    def fx(t, args):
        return 0.5 * float(ox_eff[_idx(t)])

    def fy(t, args):
        return 0.5 * float(oy_eff[_idx(t)])

    H0 = 0.5 * delta * sz
    H = [H0, [sx, fx], [sy, fy]]

    basis = [qt.basis(2, 0), qt.basis(2, 1)]
    cols = []
    opts = qt.Options(nsteps=10000)
    for b in basis:
        out = qt.sesolve(H, b, tlist=[0.0, duration], options=opts).states[-1]
        cols.append(out.full())
    U = np.concatenate(cols, axis=1)
    return U


def simulate_unitary(
    model: QubitHamiltonianModel,
    duration: float,
    ox: np.ndarray,
    oy: np.ndarray,
    theta: np.ndarray,
) -> np.ndarray:
    """Simulate unitary evolution for given controls and uncertainty θ.

    Returns:
        U: 2x2 complex unitary (numpy array)
    """
    if qt is None:
        return _piecewise_unitary_numpy(model, duration, ox, oy, theta)
    return _piecewise_unitary_qutip(model, duration, ox, oy, theta)


def average_gate_fidelity(U: np.ndarray, V: np.ndarray) -> float:
    """Average gate fidelity between implemented U and target V for d=2."""
    d = 2
    tr = np.trace(np.conjugate(V.T) @ U)
    return float((abs(tr) ** 2 + d) / (d * (d + 1)))


def target_unitary(name: str) -> np.ndarray:
    """Return target single-qubit unitary for X or SX (sqrt(X))."""
    name = name.upper()
    if name == "X":
        return np.array([[0, 1], [1, 0]], dtype=complex)
    if name in ("SX", "SQRTX", "SQRX"):
        # sqrt(X) = exp(-i pi/4 X)
        return 0.5 * np.array([[1+1j, 1-1j], [1-1j, 1+1j]], dtype=complex)
    raise ValueError(f"Unknown gate {name}")
