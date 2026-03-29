# AutoPulseSynth: Technical Report

## 1. Project Overview

AutoPulseSynth is a robust quantum control framework for superconducting qubits. It solves the calibration drift problem by synthesizing Gaussian-DRAG microwave pulses that maintain high gate fidelity across a specified window of hardware uncertainty, without requiring repeated manual recalibration.

The system is deployed as a full-stack web application: a FastAPI backend (Python, QuTiP, scikit-learn) hosted on Render, and a Next.js frontend hosted on Vercel.

---

## 2. Physics Model

### 2.1 Hamiltonian (`autopulsesynth/model.py`)

We model a single superconducting qubit in the rotating frame under the Rotating Wave Approximation (RWA):

$$H(t) = \frac{\Delta}{2}\sigma_z + \frac{\Omega_x(t)}{2}\sigma_x + \frac{\Omega_y(t)}{2}\sigma_y$$

- $\Delta$: Detuning (qubit frequency minus drive frequency) in rad/s.
- $\Omega_x(t), \Omega_y(t)$: I and Q control fields in rad/s.
- $\sigma_x, \sigma_y, \sigma_z$: Standard Pauli matrices.

Convention: $|0\rangle = [1,0]^T$ is the ground state, $|1\rangle = [0,1]^T$ is the excited state.

### 2.2 Decoherence (`autopulsesynth/model.py`)

For open-system evolution, the Lindblad master equation is used with two collapse operators:

**T1 (energy relaxation):**

$$L_1 = \sqrt{\frac{1}{T_1}} \, \sigma_-, \quad \sigma_- = |0\rangle\langle 1| = \begin{pmatrix}0&1\\0&0\end{pmatrix}$$

Maps $|1\rangle$ (excited) to $|0\rangle$ (ground). Verified: population decays as $e^{-t/T_1}$.

**T2 (dephasing, pure dephasing component):**

$$L_2 = \sqrt{\frac{\gamma_\phi}{2}} \, \sigma_z, \quad \gamma_\phi = \frac{1}{T_2} - \frac{1}{2T_1}$$

Requires $T_2 \leq 2T_1$ (physical). If $T_2 > 2T_1$, only $L_1$ is applied (pure T1 limit).

> The web UI does not expose T1/T2 inputs. Both default to `None` (closed system, fast simulation). T1/T2 are available via the CLI and direct API.

---

## 3. Pulse Parameterization (`autopulsesynth/pulses.py`)

We use the **Gaussian-DRAG** pulse family with 5 parameters $[A, t_0, \sigma, \phi, \beta]$:

$$\Omega_x(t) = A \cdot g(t) \cos\phi \;-\; A\beta\sigma \frac{dg}{dt} \sin\phi$$
$$\Omega_y(t) = A \cdot g(t) \sin\phi \;+\; A\beta\sigma \frac{dg}{dt} \cos\phi$$

where $g(t) = \exp\!\left(-\frac{(t-t_0)^2}{2\sigma^2}\right)$.

For $\phi=0$ (standard X/SX gates) this reduces to: $\Omega_x = A\cdot g$, $\Omega_y = A\beta\sigma \frac{dg}{dt}$ — the standard DRAG form.

The $\sigma$-normalization makes $\beta$ dimensionless and ensures $|\Omega_y| \ll |\Omega_x|$ for $|\beta| \leq 0.2$ (perturbative regime).

**Parameter bounds:**

| Parameter | Min | Max | Physical meaning |
|---|---|---|---|
| $A$ | 0 | $8\pi/T$ | Peak amplitude (rad/s) |
| $t_0$ | 0 | $T$ | Pulse center (s) |
| $\sigma$ | $T/20$ | $T/2$ | Pulse width (s) |
| $\phi$ | $-\pi$ | $\pi$ | Drive axis rotation (rad) |
| $\beta$ | -0.2 | 0.2 | Normalized DRAG coefficient |

---

## 4. Gate Fidelity Metrics (`autopulsesynth/metrics.py`)

### 4.1 Closed System — Average Gate Fidelity

Horodecki formula for $d=2$:

$$F_{\text{avg}}(U, V) = \frac{|\text{Tr}(V^\dagger U)|^2 + 2}{6}$$

Verified: $F(X,X)=1$, $F(\mathrm{SX},\mathrm{SX})=1$, $F(I,X)=1/3$.

### 4.2 Open System — State Fidelity Proxy

For Lindblad density-matrix evolution, a 4-state average:

$$F_{\text{proxy}} = \frac{1}{4}\sum_{k} \text{Tr}\!\left(\rho_k^{\text{target}} \, \rho_k^{\text{out}}\right)$$

over $\{|0\rangle, |1\rangle, |{+}\rangle, |{+i}\rangle\}$, which span the full single-qubit operator space.

---

## 5. Target Gates (`autopulsesynth/simulate.py`)

| Gate | Matrix |
|---|---|
| X | $\bigl(\begin{smallmatrix}0&1\\1&0\end{smallmatrix}\bigr)$ |
| SX | $\tfrac{1}{2}\bigl(\begin{smallmatrix}1+i&1-i\\1-i&1+i\end{smallmatrix}\bigr)$ (IBM convention; $\equiv e^{-i\pi/4 X}$ up to global phase — fidelity unaffected) |

---

## 6. Surrogate-Assisted Optimization (`autopulsesynth/optimize.py`)

### Pipeline

1. **Sample** — $N_{\text{pulses}}$ random parameter sets, each simulated over $N_\theta$ uncertainty instances $\theta = [\Delta, \alpha, \psi, \xi]$.
2. **Train** — Random Forest Regressor (400 trees) on features $[A, t_0/T, \sigma/T, \sin\phi, \cos\phi, \beta, A\beta, \theta_1\ldots\theta_4]$.
3. **Optimize** — Differential Evolution on the surrogate with objective:
   $$\mathcal{L}(p) = 1 - F_{\text{worst}}^{\text{surrogate}} + 2(A\sigma\sqrt{2\pi} - \pi_{\text{target}})^2 + 5\sin^2\phi$$
4. **Verify** — Best parameters re-simulated in full QuTiP over 128 fresh $\theta$ samples. All reported metrics come from this step.

---

## 7. Uncertainty Model

| Parameter | Physical source |
|---|---|
| $\Delta$ (detuning) | Charge noise, TLS defects |
| $\alpha$ (amplitude scale) | AWG gain, mixer chain |
| $\psi$ (phase skew) | IQ imbalance |
| $\xi$ (noise strength) | Additional quasi-static detuning |

All drawn from uniform distributions. The web UI exposes Drift Bounds (±MHz) and uses ±5% amplitude error by default.

---

## 8. Verified Performance

Live re-simulation results (not surrogate), seed=42, X gate, 40 ns, T1=15 μs:

| Metric | Value |
|---|---|
| Mean gate fidelity | **98.5%** (±2 MHz, ±5% amplitude) |
| Worst-case fidelity (±2 MHz drift) | **96.8%** (200 samples) |
| Worst-case fidelity (±10 MHz drift) | **89.9%** (improved from ~80.0% baseline) |
| Surrogate R² | **0.90** (held-out 20% test set) |
| Surrogate MAE | **0.042** (fidelity units) |

---

## 9. API (`api/main.py`)

**Endpoint:** `POST /api/synthesize`

**Input validation:**
- `duration`: 5 ns – 500 ns
- `det_max_hz`: 0 – 50 MHz
- `n_train`: 10 – 1000
- `n_theta_train`: 1 – 20

**CORS:** `allow_origins=["*"]`, no credentials (stateless, no auth tokens).

**Boulder Opal:** If `boulder_opal_key` is provided, the optimized waveform is sent to Q-CTRL's cloud graph API and the resulting fidelity curve is returned alongside local results for cross-validation.

---

## 10. Deployment

| Layer | Service | Config file |
|---|---|---|
| Backend | Render (Python web) | `render.yaml` |
| Frontend | Vercel (Next.js) | `frontend/vercel.json` |
| Backend URL | `NEXT_PUBLIC_API_URL` env var | Set in Vercel dashboard |

---

## 11. Known Limitations

- **Simulation only.** No hardware-in-the-loop. All fidelity numbers are from numerical simulation.
- **Single qubit only.** No two-qubit or multi-qubit gates.
- **Superconducting transmon model.** DRAG pulses and 20–100 ns time scales are specific to this platform.
- **Surrogate extrapolation.** Surrogate accuracy degrades if the deployment drift range differs significantly from the training range. Always train over the full intended uncertainty window.
- **Duration limits.** Below ~20 ns: required amplitudes approach hardware limits and leakage to $|2\rangle$ becomes non-negligible (not modeled in the two-level approximation). Above ~500 ns: decoherence dominates.
