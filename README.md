# AutoPulseSynth: Quantum Control Optimization

![AutoPulseSynth Banner](docs/images/image%2024.png)

**A full-stack, ML-assisted optimization framework for generating hardware-resilient superconducting qubit pulses.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/frontend-Next.js-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AutoPulseSynth synthesizes Gaussian-DRAG microwave control pulses for superconducting qubits that remain robust under Hamiltonian uncertainty (e.g. charge noise drift, TLS defects). A Random Forest surrogate model trains over QuTiP physics simulations, driving a Differential Evolution optimizer to find pulse parameters that maximize worst-case fidelity. 

The pipeline includes an automated **gate-aware baseline safeguard** that verifies optimized pulses against analytically calibrated baselines in the simulator, falling back when the surrogate cannot improve. At high drift (±10 MHz), the optimizer pushes worst-case fidelity from **80% to 89%**. All real-time unitary matrix evolutions are optionally cross-validated against Q-CTRL **Boulder Opal**.

**Live Demo:** [auto-pulse-synth.vercel.app](https://auto-pulse-synth.vercel.app)

---

## The Problem

In a superconducting qubit lab, a qubit's resonant frequency drifts continuously due to charge noise and Two-Level System (TLS) defects. A standard Gaussian pulse calibrated to zero drift will lose significant fidelity when the frequency shifts by even a few MHz. Physicists must halt experiments to recalibrate — repeatedly.

AutoPulseSynth instead synthesizes a **robust DRAG envelope**: the ML loop deliberately shapes the pulse amplitude and phase to maintain high fidelity across the entire specified drift window, making recalibration unnecessary for typical daily drift ranges.

The resulting waveform arrays are loaded directly into an **Arbitrary Waveform Generator (AWG)**, IQ-mixed with a local oscillator, and transmitted down the dilution refrigerator coaxial lines.

---

## Quick Start

### One-Command Launch

```bash
git clone https://github.com/HABER7789/AutoPulseSynth.git
cd AutoPulseSynth
./run.sh
```

This automatically creates a Python virtual environment, installs all dependencies, starts both the backend and frontend servers, and opens your browser to `http://localhost:3000`.

### Using Make (alternative)

```bash
make setup    # One-time: creates .venv, installs Python + Node deps
make run      # Starts both backend (port 8000) and frontend (port 3000)
make clean    # Removes .venv, node_modules, and build artifacts
```

### Manual Setup

If you prefer to start each service independently:

**Backend (FastAPI + QuTiP simulation engine):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt
uvicorn api.main:app --reload --port 8000
```

**Frontend (Next.js dashboard):**

```bash
cd frontend
npm install
npm run dev
```

The dashboard starts on `http://localhost:3000` and the API on `http://localhost:8000`.

---

## How It Works

1. **Sample** — Generate N random Gaussian-DRAG pulse parameter sets `[A, t₀, σ, φ, β]`.
2. **Simulate** — Run piecewise-constant Hamiltonian propagation U = Π_k exp(-iH_kΔt) for each pulse across sampled uncertainty instances `θ = [Δ, amp_scale, phase_skew, noise]`.
3. **Surrogate** — Train a Random Forest regressor to predict worst-case fidelity from pulse + uncertainty features.
4. **Optimize** — Differential Evolution searches the surrogate landscape for the globally robust parameters.
5. **Verify** — Re-simulate the best candidate in the full physics simulator (not the surrogate) to confirm performance.

The Hamiltonian throughout is the standard rotating-frame single-qubit model:

```
H(t) = (Δ/2)σz + (Ωx(t)/2)σx + (Ωy(t)/2)σy
```

with decoherence handled via the Lindblad master equation (T₁, T₂) when specified.

---

## Two Run Modes

| Mode | Training Samples | DE Iterations | Eval Points | Typical Time (local) |
|---|---|---|---|---|
| **Full Run** | 150 × 3 = 450 | maxiter=120, pop=18 | 64 + 128 | ~80–120s |
| **Quick Demo** | 30 × 2 = 60 | maxiter=15, pop=8 | 8 + 16 | ~7–15s |

Both modes produce valid physics results. The full run is more rigorous with higher surrogate accuracy; the Quick Demo is ideal for live presentations and career fairs.

---

## Q-CTRL Boulder Opal Validation

If running locally, you can enter your Q-CTRL API key in the dashboard to cross-validate the optimized pulse against Boulder Opal's cloud infrastructure. The resulting fidelity curve is plotted alongside the local simulation result.

> **Note:** Boulder Opal uses OAuth browser authentication and is only available when running locally. When accessing the deployed version, the UI will display a notice directing users to clone the repo for BO validation.

---

## Azure Quantum Export (Rigetti Quil-T)

After synthesis completes, the dashboard provides an **"Export to Azure Quantum"** button that downloads the optimized pulse as a Rigetti Quil-T program file (`.quil`).

The exported file contains:
- 800-point IQ waveform envelope defined via `DEFWAVEFORM`
- Custom gate calibration block (`DEFCAL`) that overrides the default gate with the ML-optimized pulse
- Measurement instruction for readout

This `.quil` file is formatted for Rigetti's superconducting QPUs, which are available as a hardware provider on Microsoft Azure Quantum. An example submission script is provided in `scripts/azure_quantum_submit.py`.

> **Important:** This is a **format export only**. AutoPulseSynth does not connect to Azure Quantum or execute on real hardware. The exported file would require an Azure Quantum workspace with Rigetti access to run on physical qubits.

---

## Features

- **DRAG Pulse Synthesis** — Gaussian-DRAG parameterization with physically constrained amplitude, width, phase, and DRAG coefficient.
- **Surrogate-Assisted Optimization** — Random Forest + Differential Evolution; evaluates the full physics landscape without running the simulator at every step.
- **Robustness Visualization** — Fidelity vs. detuning sweep plot showing optimized vs. unoptimized baseline.
- **AWG Waveform Output** — IQ envelope arrays (rad/s) ready to be loaded into lab hardware.
- **Hardware Limit Warnings** — UI warns when parameters exceed typical superconducting qubit constraints (< 20 ns duration, > 10 MHz drift).
- **Quick Demo Mode** — Lightweight synthesis for fast demos at career fairs or live presentations.
- **Boulder Opal Integration** — Optional enterprise cross-validation via Q-CTRL's cloud API (local mode only).
- **Azure Quantum Export** — One-click download of the optimized pulse as a Rigetti Quil-T program file (`.quil`), formatted for potential execution on superconducting hardware via Microsoft Azure Quantum. This is a format export, not a live hardware submission.

---

## Project Structure

```
AutoPulseSynth/
├── api/                  # FastAPI backend (main.py)
├── autopulsesynth/       # Core Python package
│   ├── model.py          # Hamiltonian + Lindblad model
│   ├── pulses.py         # Gaussian-DRAG pulse family
│   ├── simulate.py       # NumPy / QuTiP simulation backends
│   ├── metrics.py        # Gate fidelity (Horodecki formula)
│   ├── optimize.py       # Surrogate training + Differential Evolution
│   ├── ir.py             # Intermediate Representation (PulseIR)
│   └── export.py         # JSON / Qiskit / Rigetti Quil-T export
├── frontend/             # Next.js dashboard (React, TailwindCSS, Plotly.js)
├── docs/                 # Technical report, architecture guide
├── tests/                # Physics unit tests (pytest)
├── scripts/              # Standalone analysis scripts
├── run.sh                # One-command launcher (backend + frontend)
├── Makefile              # make setup / make run / make clean
├── render.yaml           # Render deployment config (backend)
├── requirements-api.txt  # Backend dependencies
└── requirements.txt      # Full development dependencies
```

---

## Deployment

The application is deployed as a split-service architecture:

- **Backend:** [Render](https://render.com) — Python FastAPI service
- **Frontend:** [Vercel](https://vercel.com) — Next.js static deployment

To deploy your own instance:

1. Push the repo to GitHub
2. Create a Render Web Service pointing at the repo root (see `render.yaml`)
3. Create a Vercel project pointing at the `frontend/` directory
4. Set `NEXT_PUBLIC_API_URL` in Vercel to your Render backend URL (e.g. `https://your-service.onrender.com`)

See `.env.example` and `frontend/.env.local.example` for environment variable templates.

---

## Scope and Limitations

- **Platform:** Superconducting transmon qubits (single-qubit gates only).
- **Validated gates:** X (π-pulse), SX (π/2-pulse).
- **Pulse duration:** 20–100 ns. Outside this range, optimizer convergence degrades.
- **Simulation only:** All fidelity results are from numerical simulation. No hardware-in-the-loop validation has been performed.
- **Azure Quantum export:** The Quil-T export produces a correctly formatted file but has not been tested on physical Rigetti hardware. It requires an Azure Quantum subscription with Rigetti provider access.
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

