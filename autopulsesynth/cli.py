import argparse
import sys
import json
import numpy as np
from pathlib import Path
from autopulsesynth.model import QubitHamiltonianModel, UncertaintyModel
from autopulsesynth.pulses import GaussianDragPulse
from autopulsesynth.optimize import SurrogateDataset, train_surrogate, optimize_under_uncertainty, verify_in_simulator
from autopulsesynth.ir import PulseIR

from .utils import hz_to_rad_s

def cmd_synthesize(args):
    print(f"Synthesizing {args.gate} pulse (duration={args.duration}s)...")
    
    # Convert constraints to rad/s
    det_max_rad = hz_to_rad_s(args.det_max_hz)
    det_min_rad = hz_to_rad_s(args.det_min_hz)
    
    # 1. Setup physics
    model = QubitHamiltonianModel(t1=args.t1, t2=args.t2)
    uncertainty = UncertaintyModel(
        detuning_min=det_min_rad, detuning_max=det_max_rad,
        scale_min=1.0 - args.amp_error, scale_max=1.0 + args.amp_error,
        rng_seed=args.seed
    )
    
    # 2. Setup Pulse Family
    # Heuristic: max amplitude ~ pi / duration for a pi-pulse, but give it 2x headroom
    # This remains in rad/s as it's a physical drive strength
    amp_max = 2 * np.pi / args.duration * 4.0 
    pulse = GaussianDragPulse(
        duration=args.duration,
        n_steps=int(args.duration * 20e9), # 20 GSa/s equivalent logic step
        amp_max=amp_max,
        sigma_min=args.duration / 20.0
    )

    # 3. Create Intermediate Representation
    target_ir = PulseIR.from_abstract_gate(args.gate, args.duration)

    print("  - Generating surrogate dataset...")
    dataset = SurrogateDataset.build(
        pulse_family=pulse,
        model=model,
        uncertainty=uncertainty,
        target_ir=target_ir,
        n_pulses=args.n_train,
        n_theta=args.n_theta_train,
        rng_seed=args.seed
    )
    
    print(f"  - Training surrogate on {len(dataset.y)} samples...")
    surrogate, metrics = train_surrogate(dataset, rng_seed=args.seed)
    print(f"    R2: {metrics['r2']:.4f}, MAE: {metrics['mae']:.4f}")
    
    print("  - Optimizing pulse parameters...")
    opt_res = optimize_under_uncertainty(
        pulse_family=pulse,
        surrogate=surrogate,
        uncertainty=uncertainty,
        mode="worst",
        target_ir=target_ir,
        n_theta_eval=64,
        rng_seed=args.seed
    )
    
    print("  - Verifying result...")
    verify_res = verify_in_simulator(
        model=model,
        pulse_family=pulse,
        params=opt_res["best_params"],
        uncertainty=uncertainty,
        target_ir=target_ir,
        n_theta=128,
        rng_seed=args.seed+1
    )
    
    print(f"RESULT: Mean Fidelity = {verify_res['f_mean']:.5f} | Worst Case = {verify_res['f_worst']:.5f}")
    
    # Save output
    args_dict = vars(args).copy()
    if 'func' in args_dict:
        del args_dict['func']

    output = {
        "args": args_dict,
        "metrics": metrics,
        "optimized_params": opt_res["best_params"].tolist(),
        "verification": {
            "f_mean": verify_res["f_mean"],
            "f_worst": verify_res["f_worst"],
            "f_std": verify_res["f_std"],
        }
    }
    
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved results to {args.output}")


def cmd_analyze(args):
    if not Path(args.input).exists():
        print(f"Error: {args.input} not found.")
        sys.exit(1)
        
    with open(args.input, "r") as f:
        data = json.load(f)
        
    print(f"Analysis of {args.input}")
    print("-" * 40)
    print(f"Gate: {data['args']['gate']}")
    print(f"Duration: {data['args']['duration']} s")
    print(f"Optimization R2: {data['metrics']['r2']:.4f}")
    print(f"Verification Sentences:")
    print(f"  Mean Fidelity: {data['verification']['f_mean']:.5f}")
    print(f"  Worst Fidelity: {data['verification']['f_worst']:.5f}")


def main():
    parser = argparse.ArgumentParser(description="AutoPulseSynth CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # SYNTHESIZE
    p_synth = subparsers.add_parser("synthesize", help="Synthesize a robust pulse")
    p_synth.add_argument("--gate", type=str, default="X", choices=["X", "SX"], help="Target gate")
    p_synth.add_argument("--duration", type=float, default=40e-9, help="Pulse duration (s)")
    p_synth.add_argument("--out", dest="output", type=str, default="pulse_result.json", help="Output JSON file")
    p_synth.add_argument("--seed", type=int, default=42, help="Random seed")
    
    # Physics params
    p_synth.add_argument("--t1", type=float, default=None, help="T1 relaxation time (s)")
    p_synth.add_argument("--t2", type=float, default=None, help="T2 dephasing time (s)")
    p_synth.add_argument("--det-max-hz", type=float, default=1e6, help="Max detuning (Hz)")
    p_synth.add_argument("--det-min-hz", type=float, default=-1e6, help="Min detuning (Hz)")
    p_synth.add_argument("--amp-error", type=float, default=0.02, help="Amplitude scale error (+/- fraction)")
    
    # ML params
    p_synth.add_argument("--n-train", type=int, default=500, help="Number of training pulses")
    p_synth.add_argument("--n-theta-train", type=int, default=5, help="Uncertainty samples per pulse in training")
    
    p_synth.set_defaults(func=cmd_synthesize)
    
    # ANALYZE
    p_analyze = subparsers.add_parser("analyze", help="Analyze an optimization result")
    p_analyze.add_argument("--input", type=str, required=True, help="Input JSON file from synthesize")
    p_analyze.set_defaults(func=cmd_analyze)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
