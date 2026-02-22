import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Ensure we can import the package
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

def main():
    parser = argparse.ArgumentParser(description="Plot robustness compatibility")
    parser.add_argument("--input", type=str, required=True, help="Input JSON result file")
    args = parser.parse_args()
    
    with open(args.input, "r") as f:
        data = json.load(f)
        
    duration = data['args']['duration']
    gate = data['args'].get('gate', 'X')
    params_opt = np.array(data['optimized_params'])
    
    print(f"Loaded {gate} pulse (T={duration}s) from {args.input}")
    
    # Reconstruct Pulse Family
    # NOTE: Must match CLI definition EXACTLY
    amp_max = 2 * np.pi / duration * 4.0 
    pulse = GaussianDragPulse(
        duration=duration,
        n_steps=int(duration * 20e9),
        amp_max=amp_max,
        sigma_min=duration/20.0
    )
    
    # Generate waveforms
    ox_opt, oy_opt = pulse.sample_controls(params_opt)
    
    # Compare with "Standard" Gaussian (beta=0, calibrated A)
    # The actual area of the truncated Gaussian from t=0 to T is slightly less than sqrt(2pi)*sigma.
    # We numerically scale it so the discrete sum * dt is EXACTLY pi for a fair comparison.
    sigma_std = duration / 4.0
    A_guess = np.pi / (sigma_std * np.sqrt(2 * np.pi))
    params_std = np.array([A_guess, duration/2, sigma_std, 0.0, 0.0])
    ox_std, oy_std = pulse.sample_controls(params_std)
    
    # Calibrate area exactly to Pi (or Pi/2 for SX)
    target_area = np.pi if gate in ("X", "Y") else np.pi/2.0
    dt = duration / len(ox_std)
    actual_area = np.sum(ox_std) * dt
    scale_factor = target_area / actual_area
    params_std[0] *= scale_factor
    
    ox_std, oy_std = pulse.sample_controls(params_std)
    
    # Physics Model
    t1 = data['args'].get('t1', None)
    t2 = data['args'].get('t2', None)
    model = QubitHamiltonianModel(t1=t1, t2=t2)
    
    # Sweep Detuning based on args
    det_max_hz = data['args'].get('det_max_hz', 20e6)
    
    # Expand slightly beyond the trained boundary to show the drop-off
    plot_bound = det_max_hz * 1.5
    
    detunings = np.linspace(-plot_bound, plot_bound, 41) # Hz
    det_rad = detunings * 2 * np.pi
    
    fids_opt = []
    fids_std = []
    
    target = target_unitary(gate)
    
    print(f"Sweeping detuning +/- {plot_bound/1e6:.1f} MHz...")
    
    for d in det_rad:
        # Theta = [det, scale=1, skew=0, noise=0]
        theta = np.array([d, 1.0, 0.0, 0.0])
        
        # Optimized
        res_opt = simulate_evolution(model, duration, ox_opt, oy_opt, theta)
        # Standard
        res_std = simulate_evolution(model, duration, ox_std, oy_std, theta)
        
        # Calculate fidelity (handles unitary or density matrix)
        # We need a metric independent of backend. 
        # But simulate_evolution returns either U or rho_list.
        # We need to adapt fidelity calculation.
        
        # Local helper
        def get_fid(res):
            if isinstance(res, np.ndarray) and res.shape == (2,2):
                return average_gate_fidelity_unitary(res, target)
            elif isinstance(res, list):
                # Open system proxy
                from autopulsesynth.metrics import average_state_fidelity_proxy
                return average_state_fidelity_proxy(res, target)
            return 0.0

        fids_opt.append(get_fid(res_opt))
        fids_std.append(get_fid(res_std))
        
    # Plot
    plt.figure(figsize=(8, 6))
    plt.plot(detunings / 1e6, fids_opt, 'b-', linewidth=2.5, label='Optimized (AutoPulseSynth)')
    plt.plot(detunings / 1e6, fids_std, 'r--', linewidth=1.5, label='Standard Gaussian')
    plt.ylim(0.0, 1.05)
    plt.xlabel("Frequency Detuning (MHz)")
    plt.ylabel("Coherent Gate Fidelity")
    plt.title(f"Robustness: {gate} Gate (T={duration*1e9:.0f}ns)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    out_file = "robustness_plot.png"
    plt.savefig(out_file, dpi=150)
    print(f"Saved plot to {out_file}")

if __name__ == "__main__":
    main()
