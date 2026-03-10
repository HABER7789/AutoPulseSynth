# AutoPulseSynth: Quantum Control Optimization

![AutoPulseSynth Banner](docs/images/image%2024.png)

**A full-stack, ML-assisted optimization framework for generating hardware-resilient superconducting qubit pulses.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/frontend-Next.js-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AutoPulseSynth synthesizes Gaussian-DRAG microwave control pulses for superconducting qubits that remain robust under hardware calibration drift (charge noise, TLS defects). A Random Forest surrogate model trained over QuTiP physics simulations drives a Differential Evolution optimizer to find pulse parameters that maximize worst-case fidelity across a specified uncertainty window.

**Verified Performance (re-simulated, seed=42, 40 ns X gate, T₁=15 μs):**
- **98.5% mean gate fidelity** under ±2 MHz frequency drift + ±5% amplitude errors
- **96.8% worst-case fidelity** across 200 uncertainty samples
- **R²=0.90** surrogate predictive accuracy on held-out test set

---

## The Problem

In a superconducting qubit lab, a qubit's resonant frequency drifts continuously due to charge noise and Two-Level System (TLS) defects. A standard Gaussian pulse calibrated to zero drift will lose significant fidelity when the frequency shifts by even a few MHz. Physicists must halt experiments to recalibrate — repeatedly.

AutoPulseSynth instead synthesizes a **robust DRAG envelope**: the ML loop deliberately shapes the pulse amplitude and phase to maintain high fidelity across the entire specified drift window, making recalibration unnecessary for typical daily drift ranges.

The resulting waveform arrays are loaded directly into an **Arbitrary Waveform Generator (AWG)**, IQ-mixed with a local oscillator, and transmitted down the dilution refrigerator coaxial lines.

---

## Quick Start

### 1. Backend (FastAPI + QuTiP simulation engine)

```bash
# From the repository root
pip install -r requirements-api.txt
uvicorn api.main:app --reload
```

The API starts on `http://localhost:8000`.

### 2. Frontend (Next.js dashboard)

```bash
cd frontend
npm install
npm run dev
```

The dashboard starts on `http://localhost:3000`.

> **Deployment:** Set the `NEXT_PUBLIC_API_URL` environment variable in Vercel to point at your deployed Render backend URL. See `.env.example`.

---

## How It Works

1. **Sample** — Generate N random Gaussian-DRAG pulse parameter sets `[A, t₀, σ, φ, β]`.
2. **Simulate** — Run QuTiP time-dependent Schrödinger equations for each pulse across sampled uncertainty instances `θ = [Δ, amp_scale, phase_skew, noise]`.
3. **Surrogate** — Train a Random Forest regressor to predict worst-case fidelity from pulse + uncertainty features.
4. **Optimize** — Differential Evolution searches the surrogate landscape in milliseconds for the globally robust parameters.
5. **Verify** — Re-simulate the best candidate in the full physics simulator (not the surrogate) to confirm performance.

The Hamiltonian throughout is the standard rotating-frame single-qubit model:

```
H(t) = (Δ/2)σz + (Ωx(t)/2)σx + (Ωy(t)/2)σy
```

with decoherence handled via the Lindblad master equation (T₁, T₂) when specified.

---

## Q-CTRL Boulder Opal Validation

If a Q-CTRL API key is provided in the dashboard, the optimized pulse is transmitted to Boulder Opal's cloud infrastructure for independent validation. The resulting fidelity curve is over-plotted on the local simulation result, confirming that the lightweight surrogate-assisted output matches enterprise quantum control software.

---

## Features

- **DRAG Pulse Synthesis** — Gaussian-DRAG parameterization with physically constrained amplitude, width, phase, and DRAG coefficient.
- **Surrogate-Assisted Optimization** — Random Forest + Differential Evolution; evaluates the full physics landscape without running the simulator at every step.
- **Robustness Visualization** — Fidelity vs. detuning sweep plot showing optimized vs. unoptimized baseline.
- **AWG Waveform Output** — IQ envelope arrays (rad/s) ready to be loaded into lab hardware.
- **Hardware Limit Warnings** — UI warns when parameters exceed typical superconducting qubit constraints (< 20 ns duration, > 10 MHz drift).
- **Boulder Opal Integration** — Optional enterprise cross-validation via Q-CTRL's cloud API.

---

## Project Structure

```
AutoPulseSynth/
├── api/                  # FastAPI backend (main.py)
├── autopulsesynth/       # Core Python package
│   ├── model.py          # Hamiltonian + Lindblad model
│   ├── pulses.py         # Gaussian-DRAG pulse family
│   ├── simulate.py       # QuTiP / NumPy simulation backends
│   ├── metrics.py        # Gate fidelity (Horodecki formula)
│   ├── optimize.py       # Surrogate training + Differential Evolution
│   ├── ir.py             # Intermediate Representation (PulseIR)
│   └── export.py         # JSON / Qiskit export
├── frontend/             # Next.js dashboard (React, TailwindCSS, Plotly.js)
├── docs/                 # Technical report, architecture guide
├── tests/                # Physics unit tests (pytest)
├── scripts/              # Standalone analysis scripts
├── render.yaml           # Render deployment config (backend)
└── requirements-api.txt  # Backend dependencies
```

---

## Scope and Limitations

- **Platform:** Superconducting transmon qubits (single-qubit gates only).
- **Validated gates:** X (π-pulse), SX (π/2-pulse).
- **Pulse duration:** 20–100 ns. Outside this range, optimizer convergence degrades.
- **Simulation only:** All results are from numerical simulation. No hardware-in-the-loop validation has been performed.
- **Two-qubit gates:** Not supported (planned).

---

## Citation

```bibtex
@software{autopulsesynth2026,
  author    = {HABER},
  title     = {AutoPulseSynth: Robust Quantum Control via Surrogate Optimization},
  year      = {2026},
  url       = {https://github.com/HABER7789/AutoPulseSynth}
}
```

## License

MIT License — see [LICENSE](LICENSE) for details.
