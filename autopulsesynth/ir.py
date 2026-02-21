"""Intermediate Representation (IR) module.

This module defines the IR-style data structures used to decouple 
logical quantum gate semantics from physical waveform emission.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

# We import the unitary generator here so the IR can hold the mathematical target.
from autopulsesynth.simulate import target_unitary

@dataclass
class PulseIR:
    """Intermediate Representation decoupling logical intent from physical implementation.
    
    Captures the abstract requirements of the target quantum operation before it is compiled
    into hardware-specific microwave pulses and parameterized driving fields.
    """
    gate_name: str
    unitary_matrix: np.ndarray
    duration_s: float
    platform_target: str = "superconducting_transmon"
    
    @classmethod
    def from_abstract_gate(cls, gate: str, duration: float) -> "PulseIR":
        """Construct the IR directly from an abstract logical gate name."""
        U = target_unitary(gate)
        return cls(
            gate_name=gate.upper(),
            unitary_matrix=U,
            duration_s=duration
        )
