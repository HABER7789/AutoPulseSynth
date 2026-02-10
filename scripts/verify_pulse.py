import sys
import os
import json
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())
try:
    from autopulsesynth.model import QubitHamiltonianModel
    from autopulsesynth.pulses import GaussianDragPulse
    from autopulsesynth.simulate import simulate_evolution, target_unitary
    from autopulsesynth.metrics import average_gate_fidelity_unitary
except ImportError:
    # helper for running from scripts/ dir
    sys.path.append(os.path.join(os.getcwd(), ".."))
    from autopulsesynth.model import QubitHamiltonianModel
    from autopulsesynth.pulses import GaussianDragPulse
    from autopulsesynth.simulate import simulate_evolution, target_unitary
    from autopulsesynth.metrics import average_gate_fidelity_unitary

def analyze_unitary(U):
    tr = np.trace(U)
    val = np.real(tr) / 2.0
    val = np.clip(val, -1.0, 1.0)
    theta = 2 * np.arccos(val)
    return theta

def main():
    if len(sys.argv) < 2:
        print("Usage: verify_pulse.py result.json")
        sys.exit(1)
        
    json_path = sys.argv[1]
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    # Extract optimized params
    params = np.array(data['optimized_params'])
    gate = data['args'].get('gate', 'X')
    duration = data['args']['duration']
    
    print(f"Verifying Optimized Pulse for {gate} (Duration {duration}s)")
    
    # Setup physics
    # If t1/t2 present in args, use them, but for strict geometry check we might prefer closed?
    # Actually, verification should match the physics used in optimization to confirm metrics.
    # BUT, to verify rotation ANGLE, we need unitary (closed).
    # So we force closed system for geometry check.
    model = QubitHamiltonianModel(t1=None, t2=None) 
    
    # Reconstruct Pulse Family
    # Must match CLI definition
    amp_max = 2 * np.pi / duration * 4.0 
    pulse = GaussianDragPulse(
        duration=duration,
        n_steps=int(duration * 20e9),
        amp_max=amp_max,
        sigma_min=duration/20.0
    )
    
    # Generate pulse waveform
    ox, oy = pulse.sample_controls(params)
    
    # 1. Simulate evolution at Delta=0 (Nominal, Closed)
    theta_0 = np.array([0.0, 1.0, 0.0, 0.0])
    U = simulate_evolution(model, duration, ox, oy, theta_0)
    
    # 2. Compute Fidelity
    target = target_unitary(gate)
    fid = average_gate_fidelity_unitary(U, target)
    
    print(f"\n--- Metrics at Delta=0 (Closed System Check) ---")
    print(f"Fidelity: {fid:.5f}")
    
    # 3. Analyze Rotation
    theta_rot = analyze_unitary(U)
    print(f"Rotation Angle: {theta_rot:.4f} rad ({theta_rot/np.pi:.3f} pi)")
    
    # Check Trace Imaginary Part
    tr = np.trace(U)
    print(f"Trace: {tr:.3f}")
    
    # Check Area
    dt = duration / len(ox)
    area_x = np.sum(ox) * dt
    print(f"Integrated Area X: {area_x:.4f}")
    
    if fid > 0.98:
        print("\n[PASS] Pulse meets strict fidelity requirement.")
    else:
        print("\n[FAIL] Fidelity < 0.98.")

if __name__ == "__main__":
    main()
