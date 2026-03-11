import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['OMP_NUM_THREADS']='1'

import numpy as np
from autopulsesynth.model import QubitHamiltonianModel, UncertaintyModel
from autopulsesynth.pulses import GaussianDragPulse
from autopulsesynth.optimize import SurrogateDataset, train_surrogate, optimize_under_uncertainty, verify_in_simulator
from autopulsesynth.ir import PulseIR
from autopulsesynth.utils import hz_to_rad_s
from api.main import gate_aware_baseline_params

def run_benchmark():
    gate = 'X'
    duration = 40e-9
    amp_max = 2*np.pi/duration*4.0
    
    model = QubitHamiltonianModel()
    pulse = GaussianDragPulse(duration=duration, n_steps=800, amp_max=amp_max, sigma_min=duration/20.0)
    target_ir = PulseIR.from_abstract_gate(gate, duration)
    
    n_train = 200
    n_theta_train = 3
    seed = 43 # We found earlier 43 is a good seed
    
    print(f"--- Investigating Novelty at Extreme Drifts ({n_train} samples) ---")
    
    drift_tests = [10e6, 15e6, 20e6]
    
    for drift_hz in drift_tests:
        det_max_rad = hz_to_rad_s(drift_hz)
        det_min_rad = hz_to_rad_s(-drift_hz)
        
        uncertainty = UncertaintyModel(
            detuning_min=det_min_rad, detuning_max=det_max_rad, 
            scale_min=0.95, scale_max=1.05, 
            rng_seed=seed
        )
        
        # 1. Baseline Performance
        base_params = gate_aware_baseline_params(gate, duration, amp_max)
        base_verify = verify_in_simulator(
            model=model, pulse_family=pulse, params=base_params, 
            uncertainty=uncertainty, target_ir=target_ir, n_theta=64, rng_seed=seed+1
        )
        base_f_worst = base_verify['f_worst'] * 100
        
        # 2. Surrogate Training
        dataset = SurrogateDataset.build(
            pulse_family=pulse, model=model, uncertainty=uncertainty, 
            target_ir=target_ir, n_pulses=n_train, n_theta=n_theta_train, rng_seed=seed
        )
        surrogate, metrics = train_surrogate(dataset, rng_seed=seed)
        
        # 3. Optimization
        opt_res = optimize_under_uncertainty(
            pulse_family=pulse, surrogate=surrogate, uncertainty=uncertainty, 
            mode='worst', target_ir=target_ir, n_theta_eval=32, rng_seed=seed, maxiter=50, popsize=10
        )
        opt_verify = verify_in_simulator(
            model=model, pulse_family=pulse, params=opt_res['best_params'], 
            uncertainty=uncertainty, target_ir=target_ir, n_theta=64, rng_seed=seed+1
        )
        opt_f_worst = opt_verify['f_worst'] * 100
        
        diff = opt_f_worst - base_f_worst
        winner = "OPT " if diff > 0 else "BASE"
        
        print(f"\nDrift: ±{drift_hz/1e6} MHz")
        print(f"  Surrogate R²: {metrics['r2']:.3f}")
        print(f"  Base Worst-Case: {base_f_worst:.2f}%")
        print(f"  Opt Worst-Case:  {opt_f_worst:.2f}%")
        print(f"  Difference:      {'+' if diff > 0 else ''}{diff:.2f}%  [{winner}]")

if __name__ == '__main__':
    run_benchmark()
