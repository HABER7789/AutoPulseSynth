import argparse
import json
import numpy as np
import plotly.graph_objects as go
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

def main():
    parser = argparse.ArgumentParser(description="Generate Interactive Plotly Widget")
    parser.add_argument("--input", type=str, required=True, default="results_2mhz.json", help="Input JSON result file")
    args = parser.parse_args()
    
    with open(args.input, "r") as f:
        data = json.load(f)
        
    duration = data['args']['duration']
    gate = data['args'].get('gate', 'X')
    params_opt = np.array(data['optimized_params'])
    
    print(f"Generating HTML widget for {gate} pulse (T={duration}s)...")
    
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
        
    # Create the Plotly figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=detunings / 1e6,
        y=fids_opt_qutip,
        mode='lines+markers',
        name='AutoPulseSynth Optimized',
        line=dict(color='#00CC96', width=3),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=detunings / 1e6,
        y=fids_std_qutip,
        mode='lines+markers',
        name='Baseline Gaussian (Unoptimized)',
        line=dict(color='#EF553B', width=2, dash='dash'),
        marker=dict(size=5)
    ))

    fig.update_layout(
        title=f"<b>Interactive Benchmarking Widget: {gate} Gate Robustness</b><br><sup>AutoPulseSynth eliminates the need for constant lab recalibration against drift.</sup>",
        xaxis_title="Frequency Detuning Drift (MHz)",
        yaxis_title="Coherent Gate Fidelity",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(
            yanchor="bottom",
            y=0.05,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    fig.update_yaxes(range=[0.0, 1.05])
    
    out_file = "interactive_benchmark.html"
    fig.write_html(out_file)
    print(f"Saved interactive widget to {out_file}")

if __name__ == "__main__":
    main()
