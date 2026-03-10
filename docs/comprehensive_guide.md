# AutoPulseSynth: Comprehensive Architecture & Physics Guide

This document is the central reference for the AutoPulseSynth physics pipeline, ML surrogate engine, and full-stack deployment architecture.

---

## 1. The Physics: Transmons, Drift, and Leakage

### What Hardware Is This For?

AutoPulseSynth is built for **superconducting qubits (transmons)** — the qubit technology behind IBM, Google, and Rigetti quantum computers. The Gaussian-DRAG pulse family and 20–100 ns gate time scales are specific to this platform.

The surrogate optimization framework itself is general — it can in principle be applied to any platform where a parameterized pulse family and a physics simulator exist. However, the current implementation is validated only for superconducting transmons.

### The Problem: Detuning and Leakage

A transmon's resonant frequency is not fixed. Charge noise and microscopic Two-Level System (TLS) defects cause it to drift by several MHz over hours. A pulse calibrated at $\Delta=0$ will miss the target state when the qubit frequency shifts — this is **detuning error**.

Additionally, transmons are weakly anharmonic ($|0\rangle \to |1\rangle \to |2\rangle \to \ldots$). Driving too fast with too high an amplitude spills population into the $|2\rangle$ state — this is **leakage**. Below ~20 ns gate time, leakage becomes significant.

### The Solution: Robust DRAG Envelopes

DRAG (Derivative Removal by Adiabatic Gate) suppresses leakage by adding a quadrature component (Q channel) proportional to the derivative of the in-phase (I) envelope. AutoPulseSynth's ML engine further optimizes the shape of both channels to maximize fidelity across the entire specified detuning window, not just at the calibration point.

The output is two numerical arrays ($\Omega_x(t)$, $\Omega_y(t)$) in rad/s, which are loaded directly into an **Arbitrary Waveform Generator (AWG)**, IQ-mixed against a ~5 GHz local oscillator, and transmitted down the dilution refrigerator coaxial lines.

---

## 2. The Hamiltonian

In the rotating frame (RWA):

$$H(t) = \frac{\Delta}{2}\sigma_z + \frac{\Omega_x(t)}{2}\sigma_x + \frac{\Omega_y(t)}{2}\sigma_y$$

- $\Delta$ = detuning (rad/s)
- $\Omega_x, \Omega_y$ = I/Q control amplitudes (rad/s)
- Standard Pauli matrices, $|0\rangle = [1,0]^T$ ground, $|1\rangle = [0,1]^T$ excited

For open systems, the Lindblad master equation adds energy relaxation ($T_1$) and pure dephasing ($T_2$) terms. See `autopulsesynth/model.py` for the exact collapse operators.

---

## 3. The Pulse Family

Five parameters define each pulse: $[A, t_0, \sigma, \phi, \beta]$.

$$\Omega_x(t) = A \cdot g(t)\cos\phi - A\beta\sigma\frac{dg}{dt}\sin\phi$$
$$\Omega_y(t) = A \cdot g(t)\sin\phi + A\beta\sigma\frac{dg}{dt}\cos\phi$$

where $g(t) = e^{-(t-t_0)^2/2\sigma^2}$.

For $\phi=0$ (X, SX gates): $\Omega_x = A\cdot g$, $\Omega_y = A\beta\sigma\,dg/dt$ — the standard DRAG form. The $\sigma$-normalization keeps $\beta$ dimensionless and perturbative.

---

## 4. The ML Surrogate Engine

Directly optimizing fidelity using the QuTiP simulator at every step would take hours. AutoPulseSynth uses a **surrogate-assisted** loop:

1. **Random sampling** — Generate 150 random pulse parameter sets. For each, simulate fidelity under 3–5 sampled uncertainty instances using QuTiP. This creates the training dataset.
2. **Surrogate training** — Fit a Random Forest Regressor (400 trees) to predict worst-case fidelity from pulse + uncertainty features. R² ≥ 0.90 on held-out data confirms the surrogate reliably maps the landscape.
3. **Differential Evolution** — A global optimizer queries the surrogate (milliseconds per evaluation) across thousands of candidate pulses to find the robust optimum, with physics-informed penalties preventing unphysical solutions.
4. **Full simulator verification** — The winning parameters are re-simulated in QuTiP over 128 fresh uncertainty samples. The verified fidelity (not the surrogate prediction) is what's reported.

---

## 5. Fidelity Metrics

**Closed system (no T1/T2):** Horodecki average gate fidelity

$$F_{\text{avg}} = \frac{|\text{Tr}(V^\dagger U)|^2 + 2}{6}$$

**Open system (with T1/T2):** State fidelity proxy averaged over 4 cardinal input states $\{|0\rangle, |1\rangle, |{+}\rangle, |{+i}\rangle\}$.

Both formulas range from 0 to 1. The web dashboard always displays the verified fidelity from the full simulator.

---

## 6. System Architecture

### Backend — FastAPI on Render

File: `api/main.py`

- Single endpoint: `POST /api/synthesize`
- Receives pulse parameters (gate type, duration, drift bounds, optional BO API key)
- Runs the full surrogate pipeline: dataset build → surrogate train → optimize → verify
- Returns waveform arrays, fidelity metrics, robustness sweep data, and optional Q-CTRL validation
- Input validation via Pydantic: `duration` 5–500 ns, `n_train` 10–1000, detuning 0–50 MHz
- CORS: open (`allow_origins=["*"]`), no credentials required

### Frontend — Next.js on Vercel

File: `frontend/src/app/page.tsx`

- Single-page application with three UI regions: control panel, robustness plot, AWG waveform plot
- API URL configured via `NEXT_PUBLIC_API_URL` environment variable (set in Vercel dashboard)
- Canvas-based `SignalConvergence` animation (`frontend/src/components/SignalConvergence.tsx`) responds to optimization state
- Plotly.js renders both plots client-side with live data from the API response

### Q-CTRL Boulder Opal Integration

When a Q-CTRL API key is entered, the backend constructs a piecewise-constant (PWC) Hamiltonian graph in Boulder Opal, evolves it across 41 detuning values, and computes fidelity using the same Horodecki formula. The result is returned alongside the local simulation and plotted as a third curve — providing independent enterprise-grade cross-validation of the local result.

---

## 7. The Laboratory Workflow

1. A physicist identifies that their dilution fridge has drifted ±2 MHz that morning and they are limited to 40 ns gates.
2. They enter those parameters into the AutoPulseSynth dashboard.
3. The ML engine synthesizes an optimized DRAG waveform robust across that entire drift window.
4. They copy the returned JSON waveform arrays into their AWG control software.
5. The qubit executes reliable quantum logic gates for the rest of the day without recalibration.

---

## 8. Deployment Summary

| Component | Platform | Config |
|---|---|---|
| Backend API | Render | `render.yaml` |
| Frontend | Vercel | `frontend/vercel.json` |
| Backend URL (env) | Vercel env vars | `NEXT_PUBLIC_API_URL` |

See `README.md` for the step-by-step deployment sequence.

---

## 9. Scope and Limitations

| Limitation | Detail |
|---|---|
| Platform | Superconducting transmon only |
| Gates | X (π-pulse), SX (π/2 pulse) |
| Qubit count | Single qubit only |
| Validation | Numerical simulation (no hardware) |
| Duration | 20–100 ns validated; 5–500 ns accepted |
| Decoherence UI | T1/T2 not exposed in web UI (CLI only) |
