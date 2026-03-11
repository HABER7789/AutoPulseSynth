"""Export utilities.

- JSON export is the primary path (portable, tool-agnostic).
- Optional Qiskit Pulse Schedule export is provided if qiskit is installed.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import json
import numpy as np

from .pulses import GaussianDragPulse


def export_pulse_json(
    pulse_family: GaussianDragPulse,
    params: np.ndarray,
    filename: str,
    smooth_sigma_pts: float = 0.0,
) -> Dict[str, Any]:
    """Export a pulse spec and sampled waveforms to a JSON file."""
    ox, oy = pulse_family.sample_controls(params, smooth_sigma_pts=smooth_sigma_pts)
    spec = {
        "pulse_family": "GaussianDragPulse",
        "pulse_params": pulse_family.to_dict(params),
        "samples": {
            "omega_x": ox.tolist(),
            "omega_y": oy.tolist(),
        },
        "notes": {
            "units": {"time": "s", "omega_x": "rad/s", "omega_y": "rad/s"},
            "simulated_only": True,
        },
    }
    with open(filename, "w") as f:
        json.dump(spec, f, indent=2)
    return spec


def export_qiskit_schedule_optional(
    pulse_family: GaussianDragPulse,
    params: np.ndarray,
    dt: float,
    channel: str = "d0",
    smooth_sigma_pts: float = 0.0,
):
    """Optional: export as a Qiskit Pulse Schedule.

    Requires qiskit-terra installed with pulse module.
    We map omega_x, omega_y samples into an IQ complex envelope.

    Args:
        dt: backend time resolution (seconds per sample)
        channel: drive channel name, e.g., 'd0' for DriveChannel(0)
    """
    try:
        from qiskit import pulse
        from qiskit.pulse import Schedule, DriveChannel, Play
        from qiskit.pulse.library import Waveform
    except Exception as e:
        raise ImportError("Qiskit pulse is not available. Install qiskit-terra.") from e

    ox, oy = pulse_family.sample_controls(params, smooth_sigma_pts=smooth_sigma_pts)
    # Convert to a complex envelope; users must scale to backend amplitude units separately.
    env = (ox + 1j * oy).astype(np.complex128)
    wf = Waveform(samples=env, name="autopulsesynth_gaussian_drag")

    if channel.lower().startswith("d"):
        idx = int(channel[1:])
        ch = DriveChannel(idx)
    else:
        raise ValueError("Only DriveChannel naming like 'd0' is supported in this baseline.")

    sched = Schedule(name="AutoPulseSynthSchedule")
    sched += Play(wf, ch)
    return sched


def export_azure_quilt(
    pulse_family: GaussianDragPulse,
    params: np.ndarray,
    gate_name: str = "rx",
    qubit_index: int = 0,
    smooth_sigma_pts: float = 0.0,
) -> str:
    """Export optimized pulse parameters to a Rigetti Quil-T program for Azure Quantum.

    This generates pulse-level instructions compatible with Rigetti superconducting 
    hardware routed through the Microsoft Azure Quantum platform.

    Args:
        pulse_family: Pulse family used for the optimization.
        params: Optimized parameters.
        gate_name: Name of the gate to define (e.g., 'rx', 'sx').
        qubit_index: Hardware qubit integer index.
        smooth_sigma_pts: Smoothing factor for control samples.

    Returns:
        A string representing the Quil-T program.
    """
    ox, oy = pulse_family.sample_controls(params, smooth_sigma_pts=smooth_sigma_pts)
    
    # Quil-T operates with generic complex lists of IQ envelopes normalized to [-1, 1].
    # In a real hardware integration, we divide by the max hardware Rabi rate. 
    # Here we normalize relative to amp_max.
    amp_max = pulse_family.amp_max
    iq_envelope = (ox + 1j * oy) / amp_max
    
    # Construct the base Quil-T syntax
    dt_ns = (pulse_family.duration / pulse_family.n_steps) * 1e9
    
    lines = [
        f'# AutoPulseSynth -> Azure Quantum (Rigetti Quil-T) Export',
        f'# Target Gate: {gate_name.upper()} on Qubit {qubit_index}',
        f'# Total Duration: {pulse_family.duration * 1e9:.2f} ns',
        f'',
        f'DECLARE ro BIT[1]',
        f'',
        f'# Define custom envelope',
        f'DEFWAVEFORM autopulse_{gate_name}_q{qubit_index}:'
    ]
    
    # Append the IQ points
    for z in iq_envelope:
        real_part = float(np.real(z))
        imag_part = float(np.imag(z))
        lines.append(f'    {real_part:.6f} + {imag_part:.6f}*i')
        
    lines.extend([
        f'',
        f'# Define physical gate calibration',
        f'DEFGATE {gate_name.upper()} AS {gate_name.upper()}:',
        f'    {gate_name.upper()} {qubit_index}',
        f'',
        f'DEFCAL {gate_name.upper()} {qubit_index}:',
        f'    PULSE {qubit_index} "{qubit_index}" autopulse_{gate_name}_q{qubit_index}',
        f'',
        f'# Execute custom gate',
        f'{gate_name.upper()} {qubit_index}',
        f'MEASURE {qubit_index} ro[0]'
    ])
    
    return "\n".join(lines)
