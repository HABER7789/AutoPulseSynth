"""AutoPulseSynth: research-grade baseline for single-qubit pulse synthesis under parameter variation.

This package is intentionally small and readable. The main notebook in notebooks/
demonstrates an end-to-end workflow: model definition, pulse parameterization,
simulation, surrogate training, optimization under parameter variation, and export.

All results are simulated.
"""

from .model import QubitHamiltonianModel, UncertaintyModel
from .pulses import GaussianDragPulse, clip_and_smooth
from .simulate import simulate_unitary, average_gate_fidelity
from .optimize import SurrogateDataset, train_surrogate, optimize_under_uncertainty
from .export import export_pulse_json, export_qiskit_schedule_optional

__all__ = [
    "QubitHamiltonianModel",
    "UncertaintyModel",
    "GaussianDragPulse",
    "clip_and_smooth",
    "simulate_unitary",
    "average_gate_fidelity",
    "SurrogateDataset",
    "train_surrogate",
    "optimize_under_uncertainty",
    "export_pulse_json",
    "export_qiskit_schedule_optional",
]
