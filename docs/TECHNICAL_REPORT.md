# AutoPulseSynth: Technical Report & User Guide

## 1. Project Overview
AutoPulseSynth is a robust control framework for superconducting qubits. It solves the problem of "calibration drift" by synthesizing control pulses that are resilient to frequency detuning ($\Delta$) and amplitude noise.

Unlike standard analytical pulses (e.g., Gaussian) which fail when the qubit frequency drifts, AutoPulseSynth uses **Surrogate-Assisted Machine Learning** to find pulse shapes that maintain $>99\%$ fidelity over a wide range of errors.

---

## 2. System Architecture

### The Physics Model (`autopulsesynth/model.py`)
We model a single superconducting qubit in the rotating frame using the **Rotating Wave Approximation (RWA)**.
The Hamiltonian is:
$$ H(t) = \frac{\Delta}{2} \sigma_z + \frac{\Omega_x(t)}{2} \sigma_x + \frac{\Omega_y(t)}{2} \sigma_y $$
- $\Delta$: Detuning (frequency error) in rad/s.
- $\Omega_x, \Omega_y$: Control fields in rad/s.
- $\sigma_{x,y,z}$: Standard Pauli matrices.

### The Pulse Family (`autopulsesynth/pulses.py`)
We use a **Gaussian-DRAG** (Derivative Removal by Adiabatic Gate) parametrization, which is standard in superconducting qubits to reduce leakage and phase errors.
$$ \Omega_x(t) = A \cdot g(t) $$
$$ \Omega_y(t) = A \cdot \beta \cdot \frac{dg(t)}{dt} \cdot \sigma_{width} $$
- **Structure**: 5 parameters $[A, t_0, \sigma, \phi, \beta]$.
- **Constraint**: Calibrated scaling ensures $\Omega_y$ has correct units ($rad/s$), preventing unphysical energy injection.

### The Optimization Loop (`autopulsesynth/optimize.py`)
Directly optimizing quantum fidelity using a simulator is slow. We use a **Surrogate-Assisted** approach:
1.  **Sample**: Generate $N=500$ random pulses and simulate their worst-case fidelity over the uncertainty range.
2.  **Learn**: Train a Random Forest regressor to predict "Worst-Case Fidelity" from pulse parameters.
3.  **Optimize**: Use a differential evolution optimizer to find the best pulse *on the cheap surrogate model*.
4.  **Verify**: Run the best candidate through the full physics simulator to confirm performance.

---

## 3. Physics & Limitations

### Validated Ranges
- **Detuning ($\Delta$)**: Tested up to $\pm 20$ MHz for a 40ns pulse. This covers typical transmon qubit drift.
- **Pulse Duration**: Tested at 20ns - 100ns. Shorter pulses require higher amplitudes, limited by the `amp_max` constraint.
- **Decoherence ($T_1, T_2$)**: Valid for any $T_1 > 0$. However, fidelity is fundamentally limited by $e^{-t_{gate}/T_1}$.

### Implementation Details
- **Unitary Evolution**: Used for closed systems ($T_1 = \infty$). Fast and exact (to machine precision).
- **Lindblad Master Equation**: Used for open systems ($T_1 < \infty$). Solved via `qutip.mesolve` with strict tolerances (`rtol=1e-6`, `nsteps=50000`) to handle stiff pulse dynamics.
- **Units**: All internal calculations use **rad/s** for energy and **seconds** for time. Inputs are converted from **Hz** immediately upon entry.

---

## 4. The "Fix" - Troubleshooting Optimization
During development, we encountered a critical issue where the optimizer produced pulses with low fidelity (~60%) that performed Z-rotations instead of X-gates.

### Diagnosis
- **Dimensional Mismatch**: The DRAG term in the code was $\Omega_y \propto \beta \cdot \dot{g}$, missing a time-scaling factor. This made the naive derivative term $10^9$ times too large.
- **Optimizer Hallucinations**: Because the training data was sparse, the surrogate model "guessed" that these chaotic high-beta pulses were good.

### The Solution
1.  **Corrected Units**: Multiplied the derivative term by $\sigma$ (pulse width) to ensure $\Omega_y$ is in $rad/s$.
2.  **Physical Constraints**: Tightened the DRAG parameter $\beta$ to $[-0.2, 0.2]$ to keep the pulse physically perturbative.
3.  **Energy Penalty**: Added a penalty term to the cost function: `Loss += (PulseArea - \pi)^2`. This forces the optimizer to find a pulse that actually flips the qubit.
4.  **Phase Penalty**: Added `Loss += sin(phi)^2` to force the drive axis to be along X.

---

## 5. User Guide: How to Synthesize & Test

### Step 1: Synthesize
Generate a pulse robust to $\pm 10$ MHz detuning for a qubit with $15 \mu s$ lifetime.
```bash
autopulsesynth synthesize \
    --gate X \
    --duration 40e-9 \
    --t1 15e-6 \
    --det-max-hz 10e6 \
    --det-min-hz -10e6 \
    --out my_pulse.json
```

### Step 2: Verify Metrics
Check the exact rotation angle and peak fidelity at resonance ($\Delta=0$).
```bash
python scripts/verify_pulse.py my_pulse.json
```
*   **Success Criteria**: Fidelity $> 0.99$, Angle $\approx 3.14$ rad.

### Step 3: Visualize Robustness
See the "V-curve" of fidelity vs. detuning.
```bash
python scripts/plot_robustness.py --input my_pulse.json
```
The resulting plot (`robustness_plot.png`) should show a flat top (high fidelity) across the detuning range.
