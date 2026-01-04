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
