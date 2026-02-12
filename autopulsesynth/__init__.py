"""AutoPulseSynth: research-grade baseline for single-qubit pulse synthesis under parameter variation.

This package is intentionally small and readable. The main notebook in notebooks/
demonstrates an end-to-end workflow: model definition, pulse parameterization,
simulation, surrogate training, optimization under parameter variation, and export.

All results are simulated.
"""

from .model import QubitHamiltonianModel, UncertaintyModel
from .pulses import GaussianDragPulse, clip_and_smooth
from .simulate import simulate_evolution, fidelity_metric, simulate_unitary, target_unitary
from .optimize import SurrogateDataset, train_surrogate, optimize_under_uncertainty, verify_in_simulator
from .utils import hz_to_rad_s, rad_s_to_hz
from .metrics import average_gate_fidelity_unitary, average_state_fidelity_proxy
from .export import export_pulse_json

# Backwards compatibility aliases for notebook
average_gate_fidelity = average_gate_fidelity_unitary

__all__ = [
    "QubitHamiltonianModel",
    "UncertaintyModel",
    "GaussianDragPulse",
    "clip_and_smooth",
    "simulate_evolution",
    "simulate_unitary",
    "fidelity_metric",
    "target_unitary",
    "SurrogateDataset",
    "train_surrogate",
    "optimize_under_uncertainty",
    "verify_in_simulator",
    "hz_to_rad_s",
    "average_gate_fidelity_unitary",
    "average_gate_fidelity",
    "export_pulse_json",
]
