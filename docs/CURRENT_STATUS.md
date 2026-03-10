# AutoPulseSynth: Current Status

**Last Updated:** 2026-03-09
**Version:** 2.0.0
**Phase:** Production — Full-Stack Deployed

---

## What's Built and Working

### Core Python Package (`autopulsesynth/`)

| Module | Status | Description |
|---|---|---|
| `model.py` | Complete | RWA Hamiltonian, T1/T2 Lindblad collapse operators |
| `pulses.py` | Complete | Gaussian-DRAG, 5-parameter, hardware-constrained |
| `simulate.py` | Complete | QuTiP (sesolve/mesolve) + NumPy/SciPy fallback |
| `metrics.py` | Complete | Horodecki average gate fidelity + 4-state open-system proxy |
| `optimize.py` | Complete | Random Forest surrogate + Differential Evolution |
| `ir.py` | Complete | PulseIR intermediate representation |
| `export.py` | Complete | JSON export, optional Qiskit schedule |
| `utils.py` | Complete | Unit conversions (Hz/rad/s, ns/s) |
| `cli.py` | Complete | `autopulsesynth synthesize` / `analyze` |

### Backend API (`api/main.py`)
- FastAPI with Pydantic input validation (duration 5–500 ns, drift 0–50 MHz, n_train 10–1000)
- CORS open (`allow_origins=["*"]`), no auth
- Optional Q-CTRL Boulder Opal cross-validation path
- Deployment: Render (`render.yaml`)

### Frontend (`frontend/`)
- Next.js 16, React 19, TailwindCSS 4, Plotly.js
- API URL configured via `NEXT_PUBLIC_API_URL` environment variable
- `SignalConvergence` canvas animation tracking optimization state
- Dark/light mode, robustness plot, AWG waveform plot, Boulder Opal overlay
- Deployment: Vercel (`frontend/vercel.json`)

---

## Verified Performance Metrics

**Config:** X gate, 40 ns, ±2 MHz detuning, ±5% amplitude, T1=15 μs, seed=42. Re-verified by live simulation.

| Metric | Value |
|---|---|
| Mean gate fidelity | **98.5%** |
| Worst-case fidelity | **96.8%** (200 samples) |
| Surrogate R² | **0.90** |
| Surrogate MAE | 0.042 |

Stored in `results_2mhz.json`.

---

## Physics Tests (`tests/test_physics.py`) — All Pass

| Test | Result |
|---|---|
| Rabi oscillation at Δ=0: F > 0.99 | PASS |
| Large detuning (100 MHz): F drops to ~1/3 | PASS |
| Half-amplitude does not give full X gate | PASS |

---

## Validated Operating Ranges

| Parameter | Validated | Notes |
|---|---|---|
| Gate duration | 20–100 ns | <20 ns leakage risk; >100 ns decoherence-limited |
| Detuning | ±2 MHz (full); ±10–20 MHz (exploratory) | Graceful degradation |
| Amplitude error | ±5% | |
| T1 | 15 μs tested | Any T1 > 0 accepted |
| T2 | T2 ≤ 2×T1 required | Clamps to T1-limit if violated |

---

## Known Limitations

1. Simulation only — no hardware-in-the-loop.
2. Single qubit only — no two-qubit gates.
3. Superconducting transmon model — DRAG + ns time scales are platform-specific.
4. T1/T2 not exposed in web UI (CLI and direct API only).
5. Full pipeline takes 1–3 minutes per job.
6. Surrogate accuracy degrades outside its training distribution.

---

## Deployment Readiness

| Component | Status |
|---|---|
| Backend (Render) | Ready — `render.yaml` present |
| Frontend (Vercel) | Ready — `frontend/vercel.json` present |
| Env var wiring | `NEXT_PUBLIC_API_URL` must be set in Vercel after Render deploy |
| Boulder Opal | Functional — requires user-supplied Q-CTRL API key at runtime |
