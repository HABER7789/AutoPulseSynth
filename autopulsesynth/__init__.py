"""AutoPulseSynth: research-grade baseline for single-qubit pulse synthesis under parameter variation.

This package is intentionally small and readable. The main notebook in notebooks/
demonstrates an end-to-end workflow: model definition, pulse parameterization,
simulation, surrogate training, optimization under parameter variation, and export.

All results are simulated.
"""

from .model import QubitHamiltonianModel, UncertaintyModel
from .pulses import GaussianDragPulse, clip_and_smooth
from .simulate import simulate_evolution, fidelity_metric
from .optimize import SurrogateDataset, train_surrogate, optimize_under_uncertainty
from .utils import hz_to_rad_s, rad_s_to_hz
from .metrics import average_gate_fidelity_unitary, average_state_fidelity_proxy

__all__ = [
    "QubitHamiltonianModel",
    "UncertaintyModel",
    "GaussianDragPulse",
    "clip_and_smooth",
    "simulate_evolution",
    "fidelity_metric",
    "SurrogateDataset",
    "train_surrogate",
    "optimize_under_uncertainty",
    "hz_to_rad_s",
    "average_gate_fidelity_unitary",
]
