import os
import sys

# Ensure backend imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['OMP_NUM_THREADS'] = '1'

import numpy as np
from autopulsesynth.compiler import parse_qasm_to_ir
from autopulsesynth.model import QubitHamiltonianModel, UncertaintyModel
from autopulsesynth.pulses import GaussianDragPulse
from autopulsesynth.optimize import SurrogateDataset, train_surrogate, optimize_under_uncertainty

def compile_and_optimize():
    print("=== AutoPulseSynth OpenQASM Compiler Pipeline ===")
    
    # Example QASM: A logical state preparation circuit
    qasm_str = """OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[1];
    x q[0];
    sx q[0];
    """
    
    print("\n1. Ingesting OpenQASM Circuit:")
    print("-" * 30)
    print(qasm_str.strip())
    print("-" * 30)
    
    # Parse to hardware-agnostic intermediate representation (PulseIR)
    ir_schedule = parse_qasm_to_ir(qasm_str, default_duration=40e-9)
    print(f"\n2. Generated {len(ir_schedule)} PulseIR targets for the execution schedule:")
    for i, ir in enumerate(ir_schedule):
        print(f"  [{i}] GATE: {ir.gate_name} | DURATION: {ir.duration_s * 1e9:.1f} ns")
        
    print("\n3. Hardware Synthesis (Fast Demo Mode)")
    
    # Set up hardware models
    model = QubitHamiltonianModel()
    uncertainty = UncertaintyModel(
        detuning_min=-2e6 * 2 * np.pi, detuning_max=2e6 * 2 * np.pi, 
        scale_min=0.95, scale_max=1.05, 
        rng_seed=42
    )

    full_pulse_schedule = []
    
    # Iterate over the intermediate representation schedule
    for step, target_ir in enumerate(ir_schedule):
        print(f"\n  -> Synthesizing Pulse {step} ({target_ir.gate_name}) ...")
        
        amp_max = 2 * np.pi / target_ir.duration_s * 4.0
        pulse = GaussianDragPulse(
            duration=target_ir.duration_s, 
            n_steps=800, 
            amp_max=amp_max, 
            sigma_min=target_ir.duration_s / 20.0
        )
        
        # Train surrogate pipeline on this specific target
        dataset = SurrogateDataset.build(
            pulse_family=pulse, model=model, uncertainty=uncertainty, 
            target_ir=target_ir, n_pulses=50, n_theta=2, rng_seed=42
        )
        surrogate, metrics = train_surrogate(dataset, rng_seed=42)
        
        # Optimize pulse geometry
        opt_res = optimize_under_uncertainty(
            pulse_family=pulse, surrogate=surrogate, uncertainty=uncertainty, 
            mode='worst', target_ir=target_ir, n_theta_eval=8, rng_seed=42, 
            maxiter=15, popsize=5
        )
        
        params = opt_res['best_params']
        print(f"     => Optimized Params: {params}")
        full_pulse_schedule.append(params)
        
    print("\n4. Final Hardware Pulse Sequence Export Ready!")
    print(f"Total compiled pulses: {len(full_pulse_schedule)}")

if __name__ == '__main__':
    compile_and_optimize()
