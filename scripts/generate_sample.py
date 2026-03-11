import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
from autopulsesynth.pulses import GaussianDragPulse
from autopulsesynth.export import export_azure_quilt

def main():
    pulse = GaussianDragPulse(duration=40e-9, n_steps=800, amp_max=314159265.35, sigma_min=40e-9/20.0)
    # A, t0, sigma, phi, beta  (5 params for GaussianDragPulse)
    params = np.array([3.14e8, 20e-9, 10e-9, 0.0, 1.5])
    
    quilt_str = export_azure_quilt(pulse, params, gate_name="x", qubit_index=0)
    
    with open("/Users/haber/CSProjects/AutoPulseSynth/scripts/sample.quil", "w") as f:
        f.write(quilt_str)
        
    print("Done")

if __name__ == "__main__":
    main()
