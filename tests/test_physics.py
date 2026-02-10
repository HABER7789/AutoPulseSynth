"""Physics verification tests.

Run with: pytest tests/test_physics.py
"""
import pytest
import numpy as np
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from autopulsesynth.model import QubitHamiltonianModel
from autopulsesynth.pulses import GaussianDragPulse
from autopulsesynth.simulate import simulate_evolution, target_unitary
from autopulsesynth.utils import hz_to_rad_s
from autopulsesynth.metrics import average_gate_fidelity_unitary

def test_rabi_oscillation_at_zero_detuning():
    """Verify that a calibrated pi-pulse drives |0> to |1> (F ~ 1)."""
    model = QubitHamiltonianModel(t1=None, t2=None)
    duration = 40e-9
    
    # Calibrate Pi-pulse for Gaussian(sigma=dur/4): Area = A * sigma * sqrt(2pi) = pi
    # A = pi / (sigma * sqrt(2pi))
    sigma = duration / 4.0
    amp = np.pi / (sigma * np.sqrt(2*np.pi))
    
    # Pulse params: [A, t0, sigma, phi, beta]
    params = np.array([amp, duration/2, sigma, 0.0, 0.0])
    
    # Pulse object
    pulse = GaussianDragPulse(
        duration=duration, n_steps=200, amp_max=amp*2, sigma_min=1e-9
    )
    
    # Simulate at 0 detuning
    theta = np.array([0.0, 1.0, 0.0, 0.0])
    ox, oy = pulse.sample_controls(params)
    
    U_res = simulate_evolution(model, duration, ox, oy, theta)
    U_target = target_unitary("X")
    
    fid = average_gate_fidelity_unitary(U_res, U_target)
    
    # Should be very high fidelity
    assert fid > 0.99, f"Analytical Pi-pulse failed. F={fid}"

def test_detuning_sensitivity():
    """Verify that large detuning reduces fidelity significantly."""
    model = QubitHamiltonianModel(t1=None, t2=None)
    duration = 40e-9
    
    # Use same calibrated pulse
    sigma = duration / 4.0
    amp = np.pi / (sigma * np.sqrt(2*np.pi))
    params = np.array([amp, duration/2, sigma, 0.0, 0.0])
    pulse = GaussianDragPulse(duration=duration, n_steps=200, amp_max=amp*2, sigma_min=1e-9)
    ox, oy = pulse.sample_controls(params)
    
    # Simulate at 0 detuning
    theta_0 = np.array([0.0, 1.0, 0.0, 0.0])
    U_0 = simulate_evolution(model, duration, ox, oy, theta_0)
    
    # Simulate at Large detuning (e.g. 100 MHz)
    det_large = hz_to_rad_s(100e6)
    theta_large = np.array([det_large, 1.0, 0.0, 0.0])
    U_large = simulate_evolution(model, duration, ox, oy, theta_large)
    
    target = target_unitary("X")
    f0 = average_gate_fidelity_unitary(U_0, target)
    f_large = average_gate_fidelity_unitary(U_large, target)
    
    print(f"F(0)={f0}, F(100MHz)={f_large}")
    assert f0 > 0.99
    # If detuning is huge, we effectively do Identity. Fidelity(I, X) = 1/3 = 0.333
    assert f_large < 0.4, "Large detuning should reduce fidelity to near 1/3"

def test_amplitude_scaling():
    """Verify that scaling amplitude changes rotation angle (over/under rotation)."""
    model = QubitHamiltonianModel()
    duration = 40e-9
    pulse = GaussianDragPulse(duration=duration, n_steps=100, amp_max=1e10, sigma_min=1e-9)
    
    # Base params
    sigma = duration/4
    amp = np.pi / (sigma * np.sqrt(2*np.pi))
    params = np.array([amp, duration/2, sigma, 0.0, 0.0])
    
    # 0.5x scale -> Pi/2 pulse (not X gate)
    ox, oy = pulse.sample_controls(params)
    theta_half = np.array([0.0, 0.5, 0.0, 0.0]) # amp_scale=0.5
    
    U_res = simulate_evolution(model, duration, ox, oy, theta_half)
    target_X = target_unitary("X")
    
    f_half = average_gate_fidelity_unitary(U_res, target_X)
    
    # Fidelity of sqrt(X) against X should be 0.5?
    # Tr(X * sqrt(X)) ...
    # Wait, simple check: it shouldn't be > 0.9
    assert f_half < 0.9, "Half amplitude should not implement full X gate"

if __name__ == "__main__":
    # fast run manually
    test_rabi_oscillation_at_zero_detuning()
    test_detuning_sensitivity()
    test_amplitude_scaling()
    print("All physics tests passed!")
