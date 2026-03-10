# AutoPulseSynth: Portfolio & Interview Guide

This guide condenses the technical answers, architecture, and value proposition of AutoPulseSynth for job interviews in Quantum Computing, Machine Learning, or Scientific Software Engineering.

---

## 1. The One-Line Pitch

> *Designed a full-stack ML pipeline that synthesizes hardware-resilient microwave pulses for superconducting qubits — solving the calibration drift problem by combining QuTiP physics simulation, Random Forest surrogate modeling, and Differential Evolution optimization into a deployed web application (FastAPI + Next.js).*

---

## 2. Verified Resume Claims

**Use these — all backed by live simulation:**

- "Achieved **98.5% mean gate fidelity** and **96.8% worst-case fidelity** under ±2 MHz frequency drift and ±5% amplitude errors (200 uncertainty samples, 40 ns X gate)"
- "Trained a Random Forest surrogate achieving **R²=0.90** on held-out data, enabling differential evolution to optimize over the quantum control landscape without simulator calls"
- "Deployed as a production full-stack application: FastAPI backend on Render, Next.js frontend on Vercel, with optional Q-CTRL Boulder Opal cross-validation"
- "Implemented Lindblad master equation decoherence (T₁, T₂) via QuTiP mesolve with verified collapse operators"

**Do not use:**
- "Works on all qubit platforms" — false, superconducting only
- "Real-time pulse optimization" — false, takes 1–3 minutes
- "Production hardware-validated" — false, simulation only

---

## 3. The Core Architecture (4 Steps)

If asked "how does it work?":

1. **Random Sampling** — 150 random Gaussian-DRAG pulse parameter sets $[A, t_0, \sigma, \phi, \beta]$ are generated. Each is simulated under 3–5 sampled uncertainty instances $\theta = [\Delta, \alpha, \psi, \xi]$ using QuTiP to produce (features, fidelity) training pairs.

2. **Surrogate Training** — A Random Forest Regressor (400 trees) learns to predict worst-case fidelity from the 11-dimensional feature vector. R²=0.90 on held-out data confirms it reliably maps the landscape.

3. **Differential Evolution** — A global optimizer queries the surrogate at millisecond cost across thousands of candidate pulses, guided by a physics-informed loss that penalizes wrong rotation angles and wrong drive axes.

4. **Full Simulator Verification** — The best parameters are re-simulated in QuTiP over 128 fresh uncertainty samples. The verified fidelity (not the surrogate estimate) is what's displayed.

---

## 4. The Physics (What You Modeled)

**Hamiltonian (rotating frame, RWA):**
$$H(t) = \frac{\Delta}{2}\sigma_z + \frac{\Omega_x(t)}{2}\sigma_x + \frac{\Omega_y(t)}{2}\sigma_y$$

**DRAG pulse (phi=0 case):**
$$\Omega_x = A \cdot g(t), \quad \Omega_y = A\beta\sigma\frac{dg}{dt}$$

The Q-channel ($\Omega_y$) suppresses leakage to the $|2\rangle$ state by destructive interference. The ML loop finds the $\beta$ and envelope shape that also maintains robustness to detuning.

**Fidelity metric (Horodecki formula, d=2):**
$$F_{\text{avg}} = \frac{|\text{Tr}(V^\dagger U)|^2 + 2}{6}$$

Analytically verified: $F(U,U)=1$, $F(I,X)=1/3$, consistent with literature.

**Decoherence (Lindblad):**
- T₁: $L_1 = \sqrt{1/T_1}\,\sigma_-$ (energy relaxation $|1\rangle \to |0\rangle$)
- T₂: $L_2 = \sqrt{\gamma_\phi/2}\,\sigma_z$, $\gamma_\phi = 1/T_2 - 1/(2T_1)$ (pure dephasing)

---

## 5. Why Boulder Opal? Why Not CUDA-Q?

**Boulder Opal (Q-CTRL):** Industry leader for microwave pulse-level control on superconducting hardware. Integrating AutoPulseSynth's output with Boulder Opal's PWC graph API proves the local simulation matches enterprise quantum control software. This is a direct validator for the kind of work done at Q-CTRL, IBM, and similar companies.

**CUDA-Q (NVIDIA):** Focuses on circuit-level hybrid quantum-classical algorithms (VQE, QAOA) accelerated on GPUs. It operates at a higher abstraction level than raw continuous microwave pulses. Not the right tool for pulse-level control.

---

## 6. Full-Stack System Design

**Backend (FastAPI on Render):**
- `POST /api/synthesize` — single synchronous endpoint
- Runs the full ML pipeline in one request (~1–3 minutes)
- Pydantic input validation prevents crash-inducing inputs
- Returns: waveform arrays, fidelity metrics, robustness sweep, optional BO validation

**Frontend (Next.js on Vercel):**
- `NEXT_PUBLIC_API_URL` env var → points at Render backend URL
- Plotly.js renders the robustness plot and AWG waveform plot client-side
- HTML5 Canvas (`SignalConvergence`) animates based on optimization state
- No backend-side rendering needed — fully static Next.js build

**CORS:** Open (`allow_origins=["*"]`), no credentials — appropriate for a public, stateless scientific tool.

---

## 7. Honest Scope Statement

AutoPulseSynth is a rigorous, end-to-end scientific software project demonstrating:
- Quantum physics modeling (Hamiltonian simulation, Lindblad equations)
- Machine learning (surrogate modeling, uncertainty quantification)
- Software engineering (FastAPI, Next.js, deployment, testing)
- Scientific validation (verified metrics, cross-validation with enterprise tool)

It is not a commercial product and has not been validated on physical hardware. It is a research-grade simulation tool deployed as a production-style web application.
