import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# Ensure autopulsesynth is in the path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

try:
    import boulderopal as bo
except ImportError:
    raise ImportError("Please install boulderopal with `pip install boulder-opal`.")

def benchmark_simulation(pulse_dict, max_detuning_hz, n_points=101):
    """Simulate pulse with Boulder Opal across a detuning sweep."""
    duration = pulse_dict["args"]["duration"]
    
    # Reconstruct pulse waveform using GaussianDragPulse logic
    from autopulsesynth.pulses import GaussianDragPulse
    
    amp_max = 2 * np.pi / duration * 4.0 
    pulse = GaussianDragPulse(
        duration=duration,
        n_steps=int(duration * 20e9),
        amp_max=amp_max,
        sigma_min=duration / 20.0
    )
    
    params = np.array(pulse_dict["optimized_params"])
    ox_hz, oy_hz = pulse.sample_controls(params)
    
    n_steps = len(ox_hz)
    
    sigma_x_np = np.array([[0, 1], [1, 0]], dtype=complex)
    sigma_y_np = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sigma_z_np = np.array([[1, 0], [0, -1]], dtype=complex)
    
    # target_unitary should match target_unitary('X') from simulate.py EXACTLY
    # AutoPulseSynth X gate: [[0, 1], [1, 0]]
    # (Without a -i phase factor)
    target_unitary_np = np.array([[0, 1], [1, 0]], dtype=complex) 

    detunings = np.linspace(-max_detuning_hz, max_detuning_hz, n_points)
    
    graph = bo.Graph()
    
    # 1D array of detunings
    detunings_tensor = graph.tensor(detunings) # (n_points,)
    # Instead of [n_points, 1] x [1, 2, 2], make det_coefs broadcastable directly
    det_coefs = graph.reshape(detunings_tensor, [n_points, 1, 1])
    
    # Detuning hamiltonian (n_points, 2, 2)
    # sigma_z_np shape is (2,2), we reshape to (1, 2, 2) to broadcast with (n_points, 1, 1)
    sz_t = graph.reshape(graph.tensor(sigma_z_np), [1, 2, 2])
    # Note: simulate.py uses Hk = 0.5 * delta * sz + 0.5 * ox * sx + 0.5 * oy * sy
    # where all terms are in rad/s, and then U = expm(-1j * Hk * dt).
    # Since we use graph.time_evolution_operators_pwc which inherently integrates H(t),
    # we just provide H in rad/s exactly as defined.
    # We must multiply the angular frequency by 2*pi to match standard rad/s!
    # Wait, simulate.py takes detuning explicitly in Hz from uncertainty model?!
    # No, cli.py does: det_max_rad = hz_to_rad_s(args.det_max_hz)
    # So detunings in simulate.py are ALREADY in rad/s.
    # Therefore, we need to convert detunings array to rad/s here too before Hamiltonian construction!
    
    det_coefs_rad = det_coefs * 2.0 * np.pi
    h_detuning = 0.5 * det_coefs_rad * sz_t
    
    # We want shape (n_points, n_steps, 2, 2) to add to time-dependent controls
    h_det_rep = graph.reshape(h_detuning, [n_points, 1, 2, 2])
    h_det_t = graph.repeat(h_det_rep, repeats=n_steps, axis=1) # (n_points, n_steps, 2, 2)
    
    # Control Hamiltonians
    ox_vals = graph.tensor(ox_hz)
    oy_vals = graph.tensor(oy_hz)
    
    ox_sh = graph.reshape(ox_vals, [1, n_steps, 1, 1])
    oy_sh = graph.reshape(oy_vals, [1, n_steps, 1, 1])
    
    h_x_vals = 0.5 * ox_sh * graph.reshape(graph.tensor(sigma_x_np), [1, 1, 2, 2])
    h_y_vals = 0.5 * oy_sh * graph.reshape(graph.tensor(sigma_y_np), [1, 1, 2, 2])
    
    h_total_vals = h_det_t + h_x_vals + h_y_vals
    # Time dimension needs to be specified for PWC objects when they have multiple dimensions.
    # We want time to be dimension 1 (n_steps). Dimensions 2 and 3 are for the operator (2x2).
    # Dimension 0 is the detuning batch.
    h_total_pwc = graph.pwc(
        values=h_total_vals, 
        durations=np.array([duration / n_steps] * n_steps),
        time_dimension=1
    )
    
    # Time evolution
    unitaries = graph.time_evolution_operators_pwc(
        hamiltonian=h_total_pwc,
        sample_times=np.array([duration])
    ) # shape (n_points, 1, 2, 2)
    
    final_unitaries = unitaries[:, 0, :, :] # (n_points, 2, 2)
    
    target_tensor = graph.tensor(target_unitary_np)
    target_tensor_rep = graph.repeat(
        graph.reshape(target_tensor, [1, 2, 2]),
        repeats=n_points, axis=0
    )

    # Manual infidelity calc: 1 - |Tr(U_target^dag U)|^2 / d^2
    products = graph.matmul(graph.adjoint(target_tensor_rep), final_unitaries)
    traces = graph.trace(products)
    fidelities_tr = graph.abs(traces) ** 2
    infidelities = 1.0 - (fidelities_tr / 4.0)

    infidelities.name = "infidelities"
    
    print(f"Executing Boulder Opal simulation ({n_points} samples)...")
    result = bo.execute_graph(graph=graph, output_node_names=["infidelities"])
    
    bo_infidelities = result["output"]["infidelities"]["value"]
    
    d = 2
    bo_avg_gate_fidelities = ( (1 - bo_infidelities) * (d**2) + d ) / (d * (d + 1))
    
    return detunings, bo_avg_gate_fidelities

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark optimized pulse with Boulder Opal")
    parser.add_argument("--input", "-i", type=str, required=True, help="Input optimized pulse JSON")
    parser.add_argument("--det-range", type=float, default=2e6, help="Max detuning (Hz) for sweep")
    args = parser.parse_args()
    
    with open(args.input, "r") as f:
        pulse = json.load(f)
        
    detunings, bo_fidelities = benchmark_simulation(pulse, args.det_range)
    
    plt.figure(figsize=(8, 5))
    plt.plot(detunings / 1e6, bo_fidelities, 'b-', label='Boulder Opal (Graph API)')
    plt.title(f"Robustness Benchmark: {pulse['args']['gate']} Gate")
    plt.xlabel("Detuning Drift (MHz)")
    plt.ylabel("Average Gate Fidelity")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    out_file = "boulder_opal_benchmark.png"
    plt.savefig(out_file)
    print(f"Benchmark complete. Saved plot to {out_file}")
    
    print("\nSample Fidelities (Boulder Opal):")
    print(f"Detuning  0.0 MHz: {bo_fidelities[len(detunings)//2]:.5f}")
    if args.det_range > 0:
        print(f"Detuning -{args.det_range/1e6:.1f} MHz: {bo_fidelities[0]:.5f}")
