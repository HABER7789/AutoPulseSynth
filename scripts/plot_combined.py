import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.getcwd())
try:
    from autopulsesynth.model import QubitHamiltonianModel
    from autopulsesynth.pulses import GaussianDragPulse
    from autopulsesynth.simulate import simulate_evolution, target_unitary
    from autopulsesynth.metrics import average_gate_fidelity_unitary
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), ".."))
    from autopulsesynth.model import QubitHamiltonianModel
    from autopulsesynth.pulses import GaussianDragPulse
    from autopulsesynth.simulate import simulate_evolution, target_unitary
    from autopulsesynth.metrics import average_gate_fidelity_unitary

# Boulder Opal imports
try:
    import boulderopal as bo
except ImportError:
    bo = None
    print("WARNING: boulderopal not installed. Will skip BO benchmark.", file=sys.stderr)

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
    
    amp_max = 2 * np.pi / duration * 4.0 
    pulse = GaussianDragPulse(
        duration=duration,
        n_steps=int(duration * 20e9),
        amp_max=amp_max,
        sigma_min=duration/20.0
    )
    
    ox_opt, oy_opt = pulse.sample_controls(params_opt)
    
    sigma_std = duration / 4.0
    A_guess = np.pi / (sigma_std * np.sqrt(2 * np.pi))
    params_std = np.array([A_guess, duration/2, sigma_std, 0.0, 0.0])
    ox_std, oy_std = pulse.sample_controls(params_std)
    
    target_area = np.pi if gate in ("X", "Y") else np.pi/2.0
    dt = duration / len(ox_std)
    actual_area = np.sum(ox_std) * dt
    scale_factor = target_area / actual_area
    params_std[0] *= scale_factor
    
    ox_std, oy_std = pulse.sample_controls(params_std)
    
    t1 = data['args'].get('t1', None)
    t2 = data['args'].get('t2', None)
    model = QubitHamiltonianModel(t1=t1, t2=t2)
    
    det_max_hz = data['args'].get('det_max_hz', 2000000.0)
    plot_bound = det_max_hz * 1.5
    
    detunings = np.linspace(-plot_bound, plot_bound, 41)
    det_rad = detunings * 2 * np.pi
    
    fids_opt_qutip = []
    fids_std_qutip = []
    
    target = target_unitary(gate)
    
    print(f"Sweeping detuning +/- {plot_bound/1e6:.1f} MHz in QuTiP...")
    for d in det_rad:
        theta = np.array([d, 1.0, 0.0, 0.0])
        res_opt = simulate_evolution(model, duration, ox_opt, oy_opt, theta)
        res_std = simulate_evolution(model, duration, ox_std, oy_std, theta)
        
        def get_fid(res):
            if isinstance(res, np.ndarray) and res.shape == (2,2):
                return average_gate_fidelity_unitary(res, target)
            elif isinstance(res, list):
                from autopulsesynth.metrics import average_state_fidelity_proxy
                return average_state_fidelity_proxy(res, target)
            return 0.0

        fids_opt_qutip.append(get_fid(res_opt))
        fids_std_qutip.append(get_fid(res_std))
        
    # BOULDER OPAL 
    bo_fidelities = None
    if bo is not None:
        try:
            print(f"Sweeping detuning +/- {plot_bound/1e6:.1f} MHz in Boulder Opal...")
            n_points = 41
            n_steps = len(ox_opt)
            
            sigma_x_np = np.array([[0, 1], [1, 0]], dtype=complex)
            sigma_y_np = np.array([[0, -1j], [1j, 0]], dtype=complex)
            sigma_z_np = np.array([[1, 0], [0, -1]], dtype=complex)
            target_unitary_np = np.array([[0, 1], [1, 0]], dtype=complex) 

            graph = bo.Graph()
            
            detunings_tensor = graph.tensor(detunings)
            det_coefs = graph.reshape(detunings_tensor, [n_points, 1, 1])
            sz_t = graph.reshape(graph.tensor(sigma_z_np), [1, 2, 2])
            
            det_coefs_rad = det_coefs * 2.0 * np.pi
            h_detuning = 0.5 * det_coefs_rad * sz_t
            
            h_det_rep = graph.reshape(h_detuning, [n_points, 1, 2, 2])
            h_det_t = graph.repeat(h_det_rep, repeats=n_steps, axis=1)
            
            ox_vals = graph.tensor(ox_opt)
            oy_vals = graph.tensor(oy_opt)
            
            ox_sh = graph.reshape(ox_vals, [1, n_steps, 1, 1])
            oy_sh = graph.reshape(oy_vals, [1, n_steps, 1, 1])
            
            h_x_vals = 0.5 * ox_sh * graph.reshape(graph.tensor(sigma_x_np), [1, 1, 2, 2])
            h_y_vals = 0.5 * oy_sh * graph.reshape(graph.tensor(sigma_y_np), [1, 1, 2, 2])
            
            h_total_vals = h_det_t + h_x_vals + h_y_vals
            h_total_pwc = graph.pwc(
                values=h_total_vals, 
                durations=np.array([duration / n_steps] * n_steps),
                time_dimension=1
            )
            
            unitaries = graph.time_evolution_operators_pwc(
                hamiltonian=h_total_pwc,
                sample_times=np.array([duration])
            )
            
            final_unitaries = unitaries[:, 0, :, :]
            
            target_tensor = graph.tensor(target_unitary_np)
            target_tensor_rep = graph.repeat(
                graph.reshape(target_tensor, [1, 2, 2]),
                repeats=n_points, axis=0
            )

            products = graph.matmul(graph.adjoint(target_tensor_rep), final_unitaries)
            traces = graph.trace(products)
            fidelities_tr = graph.abs(traces) ** 2
            infidelities = 1.0 - (fidelities_tr / 4.0)
            infidelities.name = "infidelities"
            
            result = bo.execute_graph(graph=graph, output_node_names=["infidelities"])
            bo_infidelities = result["output"]["infidelities"]["value"]
            
            d = 2
            bo_fidelities = ( (1 - bo_infidelities) * (d**2) + d ) / (d * (d + 1))
        except Exception as e:
            print(f"Boulder Opal failed: {e}")

    # Plot
    plt.figure(figsize=(10, 6))
    plt.plot(detunings / 1e6, fids_opt_qutip, 'b-', linewidth=2.5, label='AutoPulseSynth (QuTiP)')
    
    if bo_fidelities is not None:
        plt.plot(detunings / 1e6, bo_fidelities, 'g--', linewidth=2.5, label='AutoPulseSynth (Boulder Opal)')
        
    plt.plot(detunings / 1e6, fids_std_qutip, 'r:', linewidth=2.0, label='Baseline Gaussian (QuTiP)')
    
    plt.ylim(0.0, 1.05)
    plt.xlabel("Frequency Detuning (MHz)")
    plt.ylabel("Coherent Gate Fidelity")
    plt.title(f"Robustness Benchmark: {gate} Gate (T={duration*1e9:.0f}ns)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    out_file = "all_benchmarks_plot.png"
    plt.savefig(out_file, dpi=150)
    print(f"Saved combined plot to {out_file}")

if __name__ == "__main__":
    main()
