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
    gate_name: str = "x",
    qubit_index: int = 0,
    qubit_frequency_hz: float = 5.0e9,
    smooth_sigma_pts: float = 0.0,
) -> str:
    """Export optimized pulse parameters to a Rigetti Quil-T program.

    Generates a syntactically valid Quil-T program that can be submitted
    to Rigetti superconducting hardware via Microsoft Azure Quantum or
    directly through pyQuil.

    The output follows the official Quil-T specification:
    https://github.com/quil-lang/quil

    Args:
        pulse_family: Pulse family used for the optimization.
        params: Optimized parameters (A, t0, sigma, phi, beta).
        gate_name: Name of the gate to define (e.g., 'x', 'sx').
        qubit_index: Hardware qubit integer index.
        qubit_frequency_hz: Qubit drive frequency in Hz (default 5 GHz).
        smooth_sigma_pts: Smoothing factor for control samples.

    Returns:
        A string representing a valid Quil-T program.
    """
    ox, oy = pulse_family.sample_controls(params, smooth_sigma_pts=smooth_sigma_pts)

    # Normalize the IQ envelope to [-1, 1] relative to amp_max.
    # On real hardware, the AWG scale factor maps this to physical voltage.
    amp_max = pulse_family.amp_max
    iq_envelope = (ox + 1j * oy) / amp_max

    # Rigetti DACs typically run at 1 GS/s. We must resample our waveform
    # to match the hardware sample rate. Duration in ns = number of samples
    # at 1 GS/s.
    hardware_sample_rate = 1e9  # 1 GS/s
    n_hw_samples = int(round(pulse_family.duration * hardware_sample_rate))

    # Resample from our simulation resolution to the hardware resolution
    if len(iq_envelope) != n_hw_samples:
        from scipy.signal import resample
        iq_resampled = resample(iq_envelope, n_hw_samples)
    else:
        iq_resampled = iq_envelope

    # Format complex samples as comma-separated list per the Quil-T spec:
    #   DEFWAVEFORM name:
    #       z1, z2, z3, ...
    sample_strs = []
    for z in iq_resampled:
        re = float(np.real(z))
        im = float(np.imag(z))
        if im >= 0:
            sample_strs.append(f"{re:.6f}+{im:.6f}i")
        else:
            sample_strs.append(f"{re:.6f}{im:.6f}i")

    waveform_name = f"autopulse_{gate_name}_q{qubit_index}"
    gate_upper = gate_name.upper()
    frame = f'{qubit_index} "xy"'

    lines = [
        f"# AutoPulseSynth -> Azure Quantum (Rigetti Quil-T) Export",
        f"# Gate: {gate_upper} on qubit {qubit_index}",
        f"# Duration: {pulse_family.duration * 1e9:.1f} ns "
        f"({n_hw_samples} samples @ {hardware_sample_rate/1e9:.0f} GS/s)",
        f"",
        f"DECLARE ro BIT[1]",
        f"",
        f"# --- Hardware frame definition ---",
        f'DEFFRAME {frame}:',
        f"    SAMPLE-RATE: {hardware_sample_rate:.1f}",
        f"    INITIAL-FREQUENCY: {qubit_frequency_hz:.1f}",
        f"",
        f"# --- Custom ML-optimized waveform ({n_hw_samples} IQ samples) ---",
        f"DEFWAVEFORM {waveform_name}:",
        f"    {', '.join(sample_strs)}",
        f"",
        f"# --- Gate calibration: override default {gate_upper} with custom pulse ---",
        f"DEFCAL {gate_upper} {qubit_index}:",
        f"    PULSE {frame} {waveform_name}",
        f"",
        f"# --- Execute and measure ---",
        f"{gate_upper} {qubit_index}",
        f"MEASURE {qubit_index} ro[0]",
    ]

    return "\n".join(lines)

