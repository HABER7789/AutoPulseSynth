# AutoPulseSynth: Roadmap

**Current version:** 2.0.0 — Full-stack web application deployed (FastAPI + Next.js).

---

## What's Complete (v2.0.0)

- Single-qubit gate synthesis (X, SX) via Gaussian-DRAG
- Random Forest surrogate + Differential Evolution optimizer
- QuTiP closed/open system simulation backends
- FastAPI backend with Pydantic validation
- Next.js frontend with Plotly.js visualization and Canvas animation
- Q-CTRL Boulder Opal optional cross-validation
- Deployed: Render (backend) + Vercel (frontend)
- Physics unit tests (pytest)
- Full documentation suite

---

## Phase 2: Robustness and UX Improvements

**Goal:** Make the deployed application more reliable and informative for daily use.

- [ ] Async job queue — move heavy computation off the synchronous request path (Celery or background tasks)
- [ ] Progress streaming — stream intermediate progress to the frontend while the job runs
- [ ] Result caching — cache results by parameter hash to avoid re-running identical jobs
- [ ] Expanded test suite — pytest integration tests for the full API pipeline
- [ ] CI/CD — GitHub Actions running tests on push

---

## Phase 3: Two-Qubit Gates

**Goal:** Extend to two-qubit entangling gates on superconducting hardware.

- [ ] Two-qubit Hamiltonian: fixed capacitive coupling ($ZZ$ interaction)
- [ ] Target gates: CZ, iSWAP
- [ ] Surrogate model scaling to 2-qubit parameter space
- [ ] Cross-talk and spectator qubit error modeling

**Prerequisite:** Phase 2 async infrastructure (two-qubit simulations are much slower).

---

## Phase 4: Platform Generalization

**Goal:** Support additional qubit platforms beyond superconducting transmons.

- [ ] Trapped ion pulse families (Raman transitions)
- [ ] NV center pulse families (composite pulses: CORPSE, BB1)
- [ ] Platform configuration via CLI flag (`--platform`)
- [ ] Platform-specific uncertainty models

---

## Phase 5: Hardware Integration (Long-Term)

**Goal:** Closed-loop calibration on real quantum hardware.

- [ ] Qiskit integration — upload pulses to IBM Quantum devices
- [ ] Bayesian optimization loop on real measurement feedback
- [ ] Randomized benchmarking integration for real fidelity measurement
- [ ] Cirq / AWS Braket / Rigetti Forest backends

---

## Non-Goals (Out of Scope)

- Multi-qubit circuit compilation (use Qiskit/Cirq for that)
- Noise characterization (use randomized benchmarking tools)
- Real-time online optimization (optimization takes 1–3 min per job by design)
